import logging
import math
import pathlib

import fitz  # PyMuPDF

from .conversion.parsing import (
    parse_rm_file,
    get_page_to_device_ratio,
    get_adjusted_page_dims,
    get_rescaled_device_dims,
    rescale_parsed_data,
    get_ann_max_bound,
)
from .conversion.text import (
    create_md_from_word_blocks,
    is_text_extractable,
    extract_text_from_smart_highlights,
)
from .conversion.ocrmypdf import (
    is_tool,
    run_ocr,
)
from .conversion.drawing import (
    draw_annotations,
    add_smart_highlight_annotations,
)
from .utils import (
    is_document,
    get_document_filetype,
    get_visible_name,
    get_ui_path,
    get_page_dims,
    list_pages_uuids,
    list_ann_rm_files,
    list_hl_json_files,
    load_json_file,
    prepare_subdir,
)


def run_remarks(input_dir, output_dir, file_name=None, **kwargs):
    if sum(1 for _ in pathlib.Path(f"{input_dir}/").glob("*.metadata")) == 0:
        logging.warning(
            f"No .metadata files found in '{input_dir}/'. Are you sure you're running remarks on a valid xochitl-like directory? See: https://github.com/lucasrla/remarks#1-copy-remarkables-raw-document-files-to-your-computer"
        )

    for metadata_path in pathlib.Path(f"{input_dir}/").glob("*.metadata"):
        if not is_document(metadata_path):
            continue

        doc_type = get_document_filetype(metadata_path)
        supported_types = ["pdf", "epub"]

        doc_name = get_visible_name(metadata_path)

        if (file_name and (file_name not in doc_name)) or not doc_name:
            continue

        if doc_type in supported_types:
            logging.info(f'\nFile: "{doc_name}.{doc_type}" ({metadata_path.stem})')

            in_device_dir = get_ui_path(metadata_path)
            out_path = pathlib.Path(f"{output_dir}/{in_device_dir}/{doc_name}/")
            out_path.mkdir(parents=True, exist_ok=True)
            # print("out_path:", out_path)

            process_document(metadata_path, out_path, doc_type, **kwargs)
        else:
            logging.info(
                f'\nFile skipped: "{doc_name}" ({metadata_path.stem}) due to unsupported filetype: {doc_type}. remarks only supports: {", ".join(supported_types)}'
            )

        # TODO: add support to notebooks

        # TODO: also, check what happens when sheets are created inside other
        # documents, like PDFs


# TODO: review args
def process_document(
    metadata_path,
    out_path,
    doc_type,
    per_page_targets=None,
    ann_type=None,
    combined_pdf=False,
    modified_pdf=False,
    combined_md=False,
    assume_malformed_pdfs=False,
    hl_md_format="whole_block",
):
    pages = list_pages_uuids(metadata_path)
    # print("- Number of pages:", len(pages))
    # print(pages)

    if not pages:
        return

    pages_magnitude = math.floor(math.log10(len(pages))) + 1

    ann_rm_files = list_ann_rm_files(metadata_path)  # scribbles
    # print("ann_rm_files", ann_rm_files)
    hl_json_files = list_hl_json_files(metadata_path)  # highlights
    # print("hl_json_files", hl_json_files)

    if ann_type == "scribbles" and not len(ann_rm_files):
        logging.warning(
            "- You asked for scribbles, but we couldn't find any of those on this document"
        )
        return

    if ann_type == "highlights" and not len(hl_json_files):
        logging.warning(
            "- You asked for highlights, but we couldn't find anything highlighted on this document"
        )
        return

    if ann_type is None and not len(hl_json_files) and not len(ann_rm_files):
        logging.warning(
            "- Found nothing annotated on this document (no scribbles, no highlights)"
        )
        return

    if doc_type == "epub":
        logging.info(
            "- This is an EPUB file! Please beware that, right now, all we can do with it is _basic_ extraction of highlighted text to Markdown. There is no support for redrawing scribbles and highlights. If you need annotations redrawn with remarks, convert EPUBs to PDFs _before_ annotating them with your reMarkable device"
        )

    if combined_md:
        combined_md_strs = []

    if modified_pdf:
        mod_pdf = fitz.open()
        pages_order = []

    pages_to_process = set(
        [f.stem for f in ann_rm_files] + [f.stem for f in hl_json_files]
    )

    for page_uuid in pages_to_process:
        page_idx = pages.index(f"{page_uuid}")
        # print("page_uuid:", page_uuid)
        # print("page_idx", page_idx)

        ann_file = None
        hl_file = None

        for f in ann_rm_files:
            if page_uuid == f.stem:
                ann_file = f

        for f in hl_json_files:
            if page_uuid == f.stem:
                hl_file = f

        page_w, page_h = get_page_dims(metadata_path, doc_type, page_idx=page_idx)
        scale = get_page_to_device_ratio(page_w, page_h)
        # print("page_w, page_h, scale", page_w, page_h, scale)

        pdf_src = None
        if doc_type == "pdf":
            f = metadata_path.with_name(f"{metadata_path.stem}.pdf")
            pdf_src = fitz.open(f)

        ann_doc = fitz.open()

        (
            ann_page,
            ann_data,
            is_ann_out_page,
            has_highlighter,
            is_extractable,
            is_ocred,
        ) = prepare_annotations(
            ann_doc,
            ann_file,
            ann_type,
            page_idx,
            page_w,
            page_h,
            scale,
            pdf_src,
            assume_malformed_pdfs,
        )

        ann_page = draw_annotations(ann_data, ann_page)

        if hl_file is not None:
            hl_data = load_json_file(hl_file)
            ann_page = add_smart_highlight_annotations(hl_data, ann_page)

        hl_text = extract_highlighted_text(
            ann_page,
            ann_type,
            page_idx,
            has_highlighter,
            is_extractable,
            is_ocred,
            assume_malformed_pdfs,
            hl_md_format,
        )

        # A workaround for extracting highlight text without relying on our
        # PDF-based code methods
        # Note that this won't output a Markdown file with <mark> tags that
        # contextualizes our highlights
        if hl_file is not None and doc_type == "epub":
            hl_text = extract_text_from_smart_highlights(hl_data, hl_md_format)

        if per_page_targets:
            if "pdf" in per_page_targets and doc_type == "pdf":
                subdir = prepare_subdir(out_path, "pdf")
                ann_doc.save(f"{subdir}/{page_idx:0{pages_magnitude}}.pdf")

            if "png" in per_page_targets and doc_type == "pdf":
                # (2, 2) is a short-hand for 2x zoom on (x, y)
                # https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_pixmap
                ann_pixmap = ann_page.get_pixmap(matrix=fitz.Matrix(2, 2))

                subdir = prepare_subdir(out_path, "png")
                ann_pixmap.save(f"{subdir}/{page_idx:0{pages_magnitude}}.png")

            if "svg" in per_page_targets and doc_type == "pdf":
                # (2, 2) is a short-hand for 2x zoom on (x, y)
                # https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_svg_image
                ann_svg_str = ann_page.get_svg_image(
                    matrix=fitz.Matrix(2, 2), text_as_path=False
                )

                subdir = prepare_subdir(out_path, "svg")
                with open(f"{subdir}/{page_idx:0{pages_magnitude}}.svg", "w") as f:
                    f.write(ann_svg_str)

            if "md" in per_page_targets:
                subdir = prepare_subdir(out_path, "md")
                with open(f"{subdir}/{page_idx:0{pages_magnitude}}.md", "w") as f:
                    f.write(hl_text)

        if modified_pdf and doc_type == "pdf":
            mod_pdf.insert_pdf(ann_doc, start_at=-1)
            pages_order.append(page_idx)

        if combined_md:
            combined_md_strs += [(page_idx, hl_text + "\n")]

        if combined_pdf and doc_type == "pdf":
            # If there are annotations outside the original page limits
            # or if the PDF has been OCRed by us, insert the annotated page
            # that we have reconstructed from scratch
            if is_ann_out_page or is_ocred:
                pdf_src.insert_pdf(ann_doc, start_at=page_idx)
                pdf_src.delete_page(page_idx + 1)

            # Else, draw annotations in the original PDF page (in-place)
            # to do our best to preserve links (and also the original page size)
            else:
                draw_annotations(ann_data, pdf_src[page_idx], inplace=True)

        ann_doc.close()

    out_doc_path_str = f"{out_path.parent}/{out_path.stem}"
    # print("out_doc_path_str:", out_doc_path_str)

    if combined_pdf and doc_type == "pdf":
        pdf_src.save(f"{out_doc_path_str} _remarks.pdf")

    if modified_pdf and doc_type == "pdf":
        pages_order = sorted(range(len(pages_order)), key=pages_order.__getitem__)
        mod_pdf.select(pages_order)
        mod_pdf.save(f"{out_doc_path_str} _remarks-only.pdf")
        mod_pdf.close()

    if combined_md:
        combined_md_strs = sorted(combined_md_strs, key=lambda t: t[0])
        combined_md_str = "".join(
            [f"\nPage {s[0]}\n--------\n" + s[1] for s in combined_md_strs]
        )
        combined_md_str = f"{out_path.stem}\n========\n" + combined_md_str

        with open(f"{out_doc_path_str} _highlights.md", "w") as f:
            f.write(combined_md_str)

    if pdf_src is not None:
        pdf_src.close()


def prepare_annotations(
    ann_doc,
    ann_file,
    ann_type,
    idx,
    page_w,
    page_h,
    scale,
    pdf_src,
    assume_malformed_pdfs,
):
    ann_data = None

    rm_w_rescaled, rm_h_rescaled = get_rescaled_device_dims(scale)
    ann_page = ann_doc.new_page(width=rm_w_rescaled, height=rm_h_rescaled)

    page_w_adj, page_h_adj = get_adjusted_page_dims(page_w, page_h, scale)
    page_rect = fitz.Rect(0, 0, page_w_adj, page_h_adj)

    if pdf_src is not None:
        ann_page.show_pdf_page(page_rect, pdf_src, pno=idx)

    # TODO: someday we might dabble at reconstructing annotations on EPUB
    # and notebook files... That probably would involve converting them to PDF
    # https://pymupdf.readthedocs.io/en/latest/document.html#Document.convert_to_pdf
    else:
        pass

    has_highlighter = False
    is_extractable = False
    is_ocred = False

    if (ann_type == "scribbles" or ann_type is None) and ann_file is not None:
        parsed_data, has_highlighter = parse_rm_file(ann_file)
        # print(parsed_data)

        ann_data = rescale_parsed_data(parsed_data, scale)
        # print(ann_data)

        # Check if there are annotations outside the original page limits
        try:
            x_max, y_max = get_ann_max_bound(ann_data)
            is_ann_out_page = (x_max > page_w_adj) or (y_max > page_h_adj)
        except:
            is_ann_out_page = False

    # This is for highlights that reMarkable's own "smart" detection misses
    # Most likely, they're highlights on scanned / image-based PDF,
    # so in order to extract any text from it, we need to run it through an OCR
    if (ann_type == "highlights" or ann_type is None) and has_highlighter:
        if pdf_src is not None:
            is_extractable = is_text_extractable(
                pdf_src[idx], malformed=assume_malformed_pdfs
            )

        if not is_extractable and pdf_src is not None and is_tool("ocrmypdf"):
            logging.warning("- Will run OCRmyPDF on it. Hold on!\n")

            tmp_fname = "_tmp.pdf"
            ann_doc.save(tmp_fname)

            # Note that OCRmyPDF does not recognize handwriting (as of Oct 2022)
            # https://github.com/ocrmypdf/OCRmyPDF/blob/7bd0e43243a05e56a92d6b00fcaa3c826fb3cccd/docs/introduction.rst#L152
            # "- It is not capable of recognizing handwriting."
            tmp_fname = run_ocr(tmp_fname)

            tmp_doc = fitz.open(tmp_fname)

            # Insert the brand new OCRed page as the first one (index=0)
            ann_doc.insert_pdf(tmp_doc, start_at=0)
            # Delete the non-OCRed page, now in the second position (index=1)
            ann_doc.delete_page(1)
            # Update ann_page reference to the OCRed page
            ann_page = ann_doc[0]

            tmp_doc.close()
            pathlib.Path(tmp_fname).unlink()

            is_ocred = True

    if ann_type == "scribbles" and has_highlighter:
        logging.info(
            "- Found highlighted text on page #{idx} but `--ann_type` flag was set to `scribbles` only, so we won't bother with it"
        )

    return (
        ann_page,
        ann_data,
        is_ann_out_page,
        has_highlighter,
        is_extractable,
        is_ocred,
    )


def extract_highlighted_text(
    ann_page,
    ann_type,
    page_idx,
    has_highlighter,
    is_extractable,
    is_ocred,
    assume_malformed_pdfs,
    hl_md_format,
):
    hl_text = ""

    # TODO: add ability to extract highlighted images / tables (via pixmaps)?

    if (ann_type == "highlights" or ann_type is None) and has_highlighter:
        if is_extractable or is_ocred:
            hl_text = create_md_from_word_blocks(
                ann_page, malformed=assume_malformed_pdfs, md_format=hl_md_format
            )
        else:
            logging.warning(
                f"- Found highlights on page #{page_idx} but couldn't extract them to Markdown"
            )

    if ann_type == "highlights" and not has_highlighter:
        logging.warning(f"- Couldn't find any highlighted text on page #{page_idx}")

    # print("hl_text:", hl_text)
    return hl_text
