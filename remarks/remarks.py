import logging
import pathlib
import re
import sys
from pprint import pprint
from typing import List

import yaml

import fitz  # PyMuPDF
from rmscene.scene_items import GlyphRange

from .Document import Document
from .conversion.drawing import (
    draw_annotations_on_pdf,
    add_smart_highlight_annotations,
)
from .conversion.ocrmypdf import (
    is_executable_available,
    run_ocr,
)
from .conversion.parsing import (
    parse_rm_file,
    rescale_parsed_data,
    get_ann_max_bound,
    determine_document_dimensions,
)
from .conversion.text import (
    check_if_text_extractable,
    extract_groups_from_pdf_ann_hl,
    extract_groups_from_smart_hl,
    prepare_md_from_hl_groups,
)
from .dimensions import REMARKABLE_DOCUMENT
from .utils import (
    is_document,
    get_document_filetype,
    get_visible_name,
    get_ui_path,
    load_json_file,
    prepare_subdir,
    RM_WIDTH,
    RM_HEIGHT,
)


# TODO: add support to `.textconversion/*.json` files, that's an easy way to
# start offering some support to handwriting conversion...
#
# See also:
# - https://github.com/lucasrla/remarks/issues/13
# - https://github.com/lucasrla/remarks/issues/11


def run_remarks(
    input_dir, output_dir, file_name=None, file_uuid=None, file_path=None, **kwargs
):
    num_docs = sum(1 for _ in pathlib.Path(f"{input_dir}/").glob("*.metadata"))

    if num_docs == 0:
        logging.warning(
            f'No .metadata files found in "{input_dir}". Are you sure you\'re running remarks on a valid xochitl-like directory? See: https://github.com/lucasrla/remarks#1-copy-remarkables-raw-document-files-to-your-computer'
        )
        sys.exit(1)

    logging.info(
        f'\nFound {num_docs} documents in "{input_dir}", will process them now',
    )

    for metadata_path in pathlib.Path(f"{input_dir}/").glob("*.metadata"):
        if file_uuid is not None and metadata_path.stem != file_uuid:
            continue

        if not is_document(metadata_path):
            continue

        doc_type = get_document_filetype(metadata_path)
        # Both "Quick Sheets" and "Notebooks" have doc_type="notebook"
        supported_types = ["pdf", "epub", "notebook"]

        doc_name = get_visible_name(metadata_path)

        if (file_name and (file_name not in doc_name)) or not doc_name:
            continue

        if doc_type in supported_types:
            logging.info(f'\nFile: "{doc_name}.{doc_type}" ({metadata_path.stem})')

            in_device_dir = get_ui_path(metadata_path)
            out_path = pathlib.Path(f"{output_dir}/{in_device_dir}/{doc_name}/")
            # print("out_path:", out_path)

            if file_path is not None and file_path not in str(in_device_dir):
                continue

            process_document(metadata_path, out_path, **kwargs)
        else:
            logging.info(
                f'\nFile skipped: "{doc_name}" ({metadata_path.stem}) due to unsupported filetype: {doc_type}. remarks only supports: {", ".join(supported_types)}'
            )

    logging.info(
        f'\nDone processing "{input_dir}"',
    )


"""
ReMarkable has a resolution, it's 1404x1872. We'll consider anything in this unit rmpts for "ReMarkable points"
PyMuPDF has its own internal points-based resolution. We'll consider this the "mupts"
A4 has a size of 210x297mm.
"""


class ObsidianMarkdownFile:
    def __init__(self):
        self.content = ""
        self.page_content = {}

    def add_document_header(self, document: Document):
        frontmatter = {}
        if document.rm_tags:
            frontmatter["remarkable_tags"] = list(
                map(lambda tag: f"#{tag}", document.rm_tags)
            )

        frontmatter_md = ""
        if len(frontmatter) > 0:
            frontmatter_md = f"""---
{yaml.dump(frontmatter, indent=2)}
---"""

        # the yaml library outputs tags as quoted, we need unquoted for obsidian to be able to parse them.
        # ie, "#obsidian" -> #obsidian
        frontmatter_md = re.sub("- [\"'](#[a-zA-Z0-9]+)[\"']", "- \\1", frontmatter_md)

        self.content += f"""{frontmatter_md}

# {document.name}

## Pages

"""

    def save(self, location: str):
        # sort pages

        for page_idx in sorted(self.page_content.keys()):
            self.content += self.page_content[page_idx]

        with open(f"{location}.md", "w") as f:
            f.write(self.content)

    def add_highlights(
        self, page_idx: int, highlights: List[GlyphRange], doc: Document
    ):
        highlight_content = ""
        joined_highlights = []
        highlights = sorted(highlights, key=lambda h: h.start)
        if len(highlights) > 0:
            if len(highlights) == 1:
                highlight_content += f"""### [[{doc.name}.pdf#page={page_idx}|{doc.name}, page {page_idx}]]

> {highlights[0].text}

"""
            else:
                # first, highlights may be disjointed. We want to join highlights that belong together
                paired_highlights = [
                    (highlights[i], highlights[i + 1])
                    for i, _ in enumerate(highlights[:-1])
                ]
                assert len(paired_highlights) > 0
                joined_highlight = []
                for current, next in paired_highlights:
                    distance = next.start - (current.start + current.length)
                    joined_highlight.append(current.text)
                    print(next)
                    if distance > 2:
                        joined_highlights.append(joined_highlight)
                        joined_highlight = []

                highlight_content += f"""### [[{doc.name}.pdf#page={page_idx}|{doc.name}, page {page_idx}]]
    """

                for joined_highlight in joined_highlights:
                    highlight_text = " ".join(joined_highlight)
                    highlight_content += f"\n> {highlight_text}\n"

                highlight_content += "\n"

        print(f"page: {page_idx}")
        print(highlights)
        if highlight_content:
            self.page_content[page_idx] = highlight_content


# TODO: review args
def process_document(
    metadata_path,
    out_path,
    per_page_targets=None,
    ann_type=None,
    combined_pdf=False,
    modified_pdf=False,
    combined_md=False,
    assume_malformed_pdfs=False,
    avoid_ocr=False,
    md_hl_format="whole_block",
    md_page_offset=0,
    md_header_format="atx",
):
    document = Document(metadata_path)
    pdf_src = document.open_source_pdf()

    pages_magnitude = document.pages_magnitude()

    if combined_md:
        combined_md_strs = []

    if modified_pdf:
        mod_pdf = fitz.open()
        pages_order = []

    obsidian_markdown = ObsidianMarkdownFile()
    obsidian_markdown.add_document_header(document)

    for (
        page_uuid,
        page_idx,
        rm_annotation_file,
        has_annotations,
        rm_highlights_file,
        has_smart_highlights,
    ) in document.pages():
        print(f"processing page {page_idx}")

        has_ann_hl = False

        # Create a new PDF document to hold the page that will be annotated
        work_doc = fitz.open()

        # Get document page dimensions and calculate what scale should be
        # applied to fit it into the device (given the device's own dimensions)
        if rm_annotation_file:
            try:
                dims = determine_document_dimensions(rm_annotation_file)
            except ValueError:
                dims = REMARKABLE_DOCUMENT
        else:
            dims = REMARKABLE_DOCUMENT
        ann_page = work_doc.new_page(
            width=dims.width,
            height=dims.height,
        )

        pdf_src_page_rect = fitz.Rect(
            0, 0, REMARKABLE_DOCUMENT.width, REMARKABLE_DOCUMENT.height
        )

        # This check is necessary because PyMuPDF doesn't let us
        # "show_pdf_page" from an empty (blank) page
        # - https://github.com/pymupdf/PyMuPDF/blob/9d2af43230f6d9944734320813acc79abe95d514/fitz/utils.py#L185-L186
        if len(pdf_src[page_idx].get_contents()) != 0:
            # Resize content of original page and copy it to the page that will
            # be annotated
            ann_page.show_pdf_page(pdf_src_page_rect, pdf_src, pno=page_idx)

            # `show_pdf_page()` works as a way to copy and resize content from
            # one doc/page/rect into another, but unlike `insert_pdf()` it will
            # not carry over in-PDF links, annotations, etc:
            # - https://pymupdf.readthedocs.io/en/latest/page.html#Page.show_pdf_page
            # - https://pymupdf.readthedocs.io/en/latest/document.html#Document.insert_pdf

        is_text_extractable = check_if_text_extractable(
            pdf_src[page_idx],
            malformed=assume_malformed_pdfs,
        )

        is_ann_out_page = False

        scale = 1
        if "scribbles" in ann_type and has_annotations:
            (ann_data, has_ann_hl), version = parse_rm_file(rm_annotation_file)
            x_max, y_max, x_min, y_min = get_ann_max_bound(ann_data)
            offset_x = 0
            offset_y = 0
            is_ann_out_page = True
            obsidian_markdown.add_highlights(page_idx, ann_data["highlights"], document)
            if version == "V6":
                offset_x = RM_WIDTH / 2
            if dims.height >= (RM_HEIGHT + 88 * 3):
                offset_y = 3 * 88  # why 3 * text_offset? No clue, ask ReMarkable.
            if abs(x_min) + abs(x_max) > 1872:
                scale = RM_WIDTH / (max(x_max, 1872) - min(x_min, 0))
                ann_data = rescale_parsed_data(ann_data, scale, offset_x, offset_y)
            else:
                scale = RM_HEIGHT / (max(y_max, 2048) - min(y_min, 0))
                ann_data = rescale_parsed_data(ann_data, scale, offset_x, offset_y)
        if "highlights" not in ann_type and has_ann_hl:
            logging.info(
                "- Found highlighted text on page #{page_idx} but `--ann_type` flag is set to `scribbles` only, so we won't bother with it"
            )

        is_ocred = False

        # This is for highlights that reMarkable's own "smart" detection misses
        # Most likely, they're highlights on scanned / image-based PDF, so in
        # order to extract any text from it, we need to run the PDF through OCR
        #
        # TODO: isn't it faster to run ocr through the whole PDF document at
        # once? (as opposed to doing it per page)
        if (
            document.doc_type == "pdf"
            and "highlights" in ann_type
            and has_ann_hl
            and not is_text_extractable
            and is_executable_available("ocrmypdf")
            and not avoid_ocr
        ):
            logging.warning("- Will run OCRmyPDF on this document. Hold on!")
            work_doc, ann_page = process_ocr(work_doc)
            is_ocred = True

        if has_annotations:
            ann_page = draw_annotations_on_pdf(ann_data, ann_page)

        # TODO: add ability to extract highlighted images / tables (via pixmaps)?

        ann_hl_groups = []
        if (
            "highlights" in ann_type
            and has_ann_hl
            and (is_text_extractable or is_ocred)
        ):
            ann_hl_groups = extract_groups_from_pdf_ann_hl(
                ann_page,
                malformed=assume_malformed_pdfs,
            )
        elif "highlights" in ann_type and has_ann_hl and document.doc_type == "pdf":
            logging.info(
                f"- Found highlights on page #{page_idx} but couldn't extract them to Markdown. Maybe run it through OCRmyPDF next time?"
            )

        smart_hl_groups = []
        if "highlights" in ann_type and has_smart_highlights:
            smart_hl_data = load_json_file(rm_highlights_file)
            ann_page = add_smart_highlight_annotations(smart_hl_data, ann_page, scale)
            smart_hl_groups = extract_groups_from_smart_hl(smart_hl_data)

        hl_text = ""
        if len(ann_hl_groups + smart_hl_groups) > 0:
            hl_text = prepare_md_from_hl_groups(
                ann_page,
                ann_hl_groups,
                smart_hl_groups,
                presentation=md_hl_format,
            )

        if per_page_targets and (has_annotations or has_smart_highlights):
            out_path.mkdir(parents=True, exist_ok=True)

            if "pdf" in per_page_targets:
                subdir = prepare_subdir(out_path, "pdf")
                work_doc.save(f"{subdir}/{page_idx:0{pages_magnitude}}.pdf")

            if "png" in per_page_targets:
                # (2, 2) is a short-hand for 2x zoom on (x, y)
                # https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_pixmap
                ann_pixmap = ann_page.get_pixmap(matrix=fitz.Matrix(2, 2))

                subdir = prepare_subdir(out_path, "png")
                ann_pixmap.save(f"{subdir}/{page_idx:0{pages_magnitude}}.png")

            if "svg" in per_page_targets:
                # (2, 2) is a short-hand for 2x zoom on (x, y)
                # https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_svg_image
                ann_svg_str = ann_page.get_svg_image(
                    matrix=fitz.Matrix(2, 2), text_as_path=False
                )

                subdir = prepare_subdir(out_path, "svg")
                with open(f"{subdir}/{page_idx:0}.svg", "w") as f:
                    f.write(ann_svg_str)

            if "md" in per_page_targets:
                subdir = prepare_subdir(out_path, "md")
                with open(f"{subdir}/{page_idx:0{pages_magnitude}}.md", "w") as f:
                    f.write(hl_text)

        if modified_pdf and (has_annotations or has_smart_highlights):
            mod_pdf.insert_pdf(work_doc, start_at=-1)
            pages_order.append(page_idx)

        if combined_md and (has_ann_hl or has_smart_highlights):
            combined_md_strs += [(page_idx + md_page_offset, hl_text + "\n")]

        # If there are annotations outside the original page limits
        # or if the PDF has been OCRed by us, insert the annotated page
        # that we've just (re)created from scratch
        if combined_pdf and (is_ann_out_page or is_ocred):
            pdf_src.insert_pdf(work_doc, start_at=page_idx)
            pdf_src.delete_page(page_idx + 1)

        # Else, draw annotations on the original PDF page (in-place) to do
        # our best to preserve in-PDF links and the original page size
        elif combined_pdf:
            if has_annotations:
                draw_annotations_on_pdf(
                    ann_data,
                    pdf_src[page_idx],
                    inplace=True,
                )

            if has_smart_highlights:
                add_smart_highlight_annotations(
                    smart_hl_data,
                    pdf_src[page_idx],
                    scale,
                    inplace=True,
                )

        work_doc.close()

    out_doc_path_str = f"{out_path.parent}/{out_path.name}"
    # print("out_doc_path_str:", out_doc_path_str)

    if combined_pdf:
        pdf_src.save(f"{out_doc_path_str} _remarks.pdf")

    if modified_pdf and (document.doc_type == "notebook" and combined_pdf):
        logging.info(
            "- You asked for the modified PDF, but we won't bother generated it for this notebook. It would be the same as the combined PDF, which you're already getting anyway"
        )
    elif modified_pdf:
        pages_order = sorted(
            range(len(pages_order)),
            key=pages_order.__getitem__,
        )
        # print("pages_order:", pages_order)
        mod_pdf.select(pages_order)
        mod_pdf.save(f"{out_doc_path_str} _remarks-only.pdf")
        mod_pdf.close()

    if combined_md and len(combined_md_strs) > 0:
        combined_md_strs = sorted(combined_md_strs, key=lambda t: t[0])

        if md_header_format == "atx":
            combined_md_str = "".join(
                [f"\n## Page {s[0]}\n\n" + s[1] for s in combined_md_strs]
            )
            combined_md_str = f"# {out_path.name}\n" + combined_md_str

        elif md_header_format == "setex":
            combined_md_str = "".join(
                [f"\nPage {s[0]}\n--------\n" + s[1] for s in combined_md_strs]
            )
            combined_md_str = f"{out_path.name}\n========\n" + combined_md_str

        with open(f"{out_doc_path_str} _highlights.md", "w") as f:
            f.write(combined_md_str)

    obsidian_markdown.save(out_doc_path_str)

    pdf_src.close()


def process_ocr(work_doc):
    tmp_fname = "_tmp.pdf"
    work_doc.save(tmp_fname)

    # Note that OCRmyPDF does not recognize handwriting (as of Oct 2022)
    # https://github.com/ocrmypdf/OCRmyPDF/blob/7bd0e43243a05e56a92d6b00fcaa3c826fb3cccd/docs/introduction.rst#L152
    # "- It is not capable of recognizing handwriting."
    tmp_fname = run_ocr(tmp_fname)

    tmp_doc = fitz.open(tmp_fname)

    # Insert the brand new OCRed page as the first one (index=0)
    work_doc.insert_pdf(tmp_doc, start_at=0)
    # Delete the non-OCRed page, now in the second position (index=1)
    work_doc.delete_page(1)
    # Update ann_page reference to the OCRed page
    ann_page = work_doc[0]

    tmp_doc.close()
    pathlib.Path(tmp_fname).unlink()

    return work_doc, ann_page
