import logging
import math
import pathlib
import sys

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
    check_if_text_extractable,
    extract_text_from_pdf_annotations,
    extract_text_from_smart_highlights,
)
from .conversion.ocrmypdf import (
    is_tool,
    run_ocr,
)
from .conversion.drawing import (
    draw_annotations_on_pdf,
    add_smart_highlight_annotations,
)
from .utils import (
    is_document,
    get_document_filetype,
    get_visible_name,
    get_ui_path,
    list_pages_uuids,
    list_ann_rm_files,
    list_hl_json_files,
    load_json_file,
    prepare_subdir,
)


def run_remarks(input_dir, output_dir, file_name=None, **kwargs):
    num_docs = sum(1 for _ in pathlib.Path(f"{input_dir}/").glob("*.metadata"))

    if num_docs == 0:
        logging.warning(
            f"No .metadata files found in {input_dir}. Are you sure you're running remarks on a valid xochitl-like directory? See: https://github.com/lucasrla/remarks#1-copy-remarkables-raw-document-files-to-your-computer"
        )
        sys.exit(1)

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

    logging.info(
        f"\nDone processing {num_docs} documents from {input_dir} to {output_dir}"
    )


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
    avoid_ocr=False,
):
    pages_list = list_pages_uuids(metadata_path)
    # print("- Number of pages:", len(pages))
    # print(pages)

    if len(pages_list) == 0:
        return

    pages_magnitude = math.floor(math.log10(len(pages_list))) + 1

    ann_rm_files = list_ann_rm_files(metadata_path)  # scribbles
    # print("ann_rm_files", ann_rm_files)
    hl_json_files = list_hl_json_files(metadata_path)  # highlights
    # print("hl_json_files", hl_json_files)

    if ann_type == "scribbles" and len(ann_rm_files) == 0:
        logging.info(
            "- You asked for scribbles, but we couldn't find any of those on this document. Will skip this one"
        )
        return

    if ann_type == "highlights" and len(hl_json_files) == 0 and len(ann_rm_files) == 0:
        logging.info(
            "- You asked for highlights, but we couldn't find anything highlighted on this document. Will skip this one"
        )
        return

    if len(hl_json_files) == 0 and len(ann_rm_files) == 0:
        logging.info(
            "- Found nothing annotated on this document (no scribbles, no highlights). Will skip this one"
        )
        return

    if combined_md:
        combined_md_strs = []

    if modified_pdf:
        mod_pdf = fitz.open()
        pages_order = []

    # Original PDF source document
    f = metadata_path.with_name(f"{metadata_path.stem}.pdf")
    pdf_src = fitz.open(f)

    pages_to_process = set(
        [f.stem for f in ann_rm_files] + [f.stem for f in hl_json_files]
    )

    for page_uuid in pages_to_process:
        page_idx = pages_list.index(f"{page_uuid}")
        # print("page_uuid:", page_uuid)
        # print("page_idx", page_idx)

        ann_rm_file = None
        hl_json_file = None

        has_ann = False
        has_smart_hl = False
        has_ann_hl = False

        for f in ann_rm_files:
            if page_uuid == f.stem:
                ann_rm_file = f
                has_ann = True

        for f in hl_json_files:
            if page_uuid == f.stem:
                hl_json_file = f
                has_smart_hl = True

        is_text_extractable = check_if_text_extractable(
            pdf_src[page_idx], malformed=assume_malformed_pdfs
        )

        # PDF document with page that will be annotated
        ann_doc = fitz.open()

        # Create a page (with the appropriate dimensions) to be annotated
        pdf_src_dims = (
            pdf_src.load_page(page_idx).rect.width,
            pdf_src.load_page(page_idx).rect.height,
        )
        scale = get_page_to_device_ratio(pdf_src_dims[0], pdf_src_dims[1])
        rescaled_device_dims = get_rescaled_device_dims(scale)
        ann_page = ann_doc.new_page(
            width=rescaled_device_dims[0], height=rescaled_device_dims[1]
        )
        page_dims_fitted_to_device = get_adjusted_page_dims(
            pdf_src_dims[0], pdf_src_dims[1], scale
        )
        page_rect = fitz.Rect(
            0, 0, page_dims_fitted_to_device[0], page_dims_fitted_to_device[1]
        )
        ann_page.show_pdf_page(page_rect, pdf_src, pno=page_idx)

        is_ann_out_page = False
        if "scribbles" in ann_type and has_ann:
            parsed_data, has_ann_hl = parse_rm_file(ann_rm_file)
            # print(parsed_data)

            ann_data = rescale_parsed_data(parsed_data, scale)
            # print(ann_data)

            # Check if there are annotations outside the original page limits
            try:
                x_max, y_max = get_ann_max_bound(ann_data)
                is_ann_out_page = (x_max > page_dims_fitted_to_device[0]) or (
                    y_max > page_dims_fitted_to_device[1]
                )
            except:
                is_ann_out_page = False

        if "highlights" not in ann_type and has_ann_hl:
            logging.info(
                "- Found highlighted text on page #{page_idx} but `--ann_type` flag is set to `scribbles` only, so we won't bother with it"
            )

        is_ocred = False
        # This is for highlights that reMarkable's own "smart" detection misses
        # Most likely, they're highlights on scanned / image-based PDF, so in
        # order to extract any text from it, we need to run the PDF through OCR

        # TODO: isn't it faster to run ocr through the whole PDF document at
        # once? (as opposed to doing it per page)
        if (
            doc_type == "pdf"
            and "highlights" in ann_type
            and has_ann_hl
            and not is_text_extractable
            and is_tool("ocrmypdf")
            and not avoid_ocr
        ):
            logging.warning("- Will run OCRmyPDF on this document. Hold on!")
            ann_doc, ann_page = process_ocr(ann_doc, ann_page)
            is_ocred = True

        ann_page = draw_annotations_on_pdf(ann_data, ann_page)

        # TODO: add ability to extract highlighted images / tables (via pixmaps)?

        ann_hl_text = ""
        if (
            "highlights" in ann_type
            and has_ann_hl
            and (is_text_extractable or is_ocred)
        ):
            ann_hl_text = extract_text_from_pdf_annotations(
                ann_page, malformed=assume_malformed_pdfs, md_format=hl_md_format
            )
        elif "highlights" in ann_type and has_ann_hl and doc_type == "pdf":
            logging.info(
                f"- Found highlights on page #{page_idx} but couldn't extract them to Markdown. Maybe run it through OCRmyPDF next time?"
            )

        smart_hl_text = ""
        if "highlights" in ann_type and has_smart_hl:
            smart_hl_data = load_json_file(hl_json_file)
            ann_page = add_smart_highlight_annotations(smart_hl_data, ann_page)
            smart_hl_text = extract_text_from_smart_highlights(
                smart_hl_data, md_format=hl_md_format
            )

        hl_text = smart_hl_text + "\n\n" + ann_hl_text

        if per_page_targets:
            if "pdf" in per_page_targets:
                subdir = prepare_subdir(out_path, "pdf")
                ann_doc.save(f"{subdir}/{page_idx:0{pages_magnitude}}.pdf")

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
                with open(f"{subdir}/{page_idx:0{pages_magnitude}}.svg", "w") as f:
                    f.write(ann_svg_str)

            if "md" in per_page_targets:
                subdir = prepare_subdir(out_path, "md")
                with open(f"{subdir}/{page_idx:0{pages_magnitude}}.md", "w") as f:
                    f.write(hl_text)

        if modified_pdf:
            mod_pdf.insert_pdf(ann_doc, start_at=-1)
            pages_order.append(page_idx)

        if combined_md and (has_ann_hl or has_smart_hl):
            combined_md_strs += [(page_idx, hl_text + "\n")]

        # If there are annotations outside the original page limits
        # or if the PDF has been OCRed by us, insert the annotated page
        # that we've just (re)created from scratch
        if combined_pdf and (is_ann_out_page or is_ocred):
            pdf_src.insert_pdf(ann_doc, start_at=page_idx)
            pdf_src.delete_page(page_idx + 1)

        # Else, draw annotations on the original PDF page (in-place) to do
        # our best to preserve in-PDF links and the original page size
        elif combined_pdf:
            if has_ann:
                draw_annotations_on_pdf(ann_data, pdf_src[page_idx], inplace=True)

            if has_smart_hl:
                add_smart_highlight_annotations(
                    smart_hl_data, pdf_src[page_idx], inplace=True
                )

        ann_doc.close()

    out_doc_path_str = f"{out_path.parent}/{out_path.stem}"
    # print("out_doc_path_str:", out_doc_path_str)

    if combined_pdf:
        pdf_src.save(f"{out_doc_path_str} _remarks.pdf")

    if modified_pdf:
        pages_order = sorted(range(len(pages_order)), key=pages_order.__getitem__)
        mod_pdf.select(pages_order)
        mod_pdf.save(f"{out_doc_path_str} _remarks-only.pdf")
        mod_pdf.close()

    if combined_md and len(combined_md_strs) > 0:
        combined_md_strs = sorted(combined_md_strs, key=lambda t: t[0])
        combined_md_str = "".join(
            [f"\nPage {s[0]}\n--------\n" + s[1] for s in combined_md_strs]
        )
        combined_md_str = f"{out_path.stem}\n========\n" + combined_md_str

        with open(f"{out_doc_path_str} _highlights.md", "w") as f:
            f.write(combined_md_str)

    pdf_src.close()


def process_ocr(ann_doc, ann_page):
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

    return ann_doc, ann_page
