import math
import pathlib

import fitz  # PyMuPDF

from .conversion.parsing import (
    parse_rm_file,
    get_pdf_to_device_ratio,
    get_adjusted_pdf_dims,
    get_rescaled_device_dims,
    rescale_parsed_data,
)
from .conversion.drawing import draw_svg, draw_pdf
from .conversion.text import md_from_blocks, is_text_extractable
from .conversion.ocrmypdf import is_tool, run_ocr

from .utils import (
    get_visible_name,
    get_ui_path,
    get_pdf_page_dims,
    list_pages_uuids,
    list_ann_rm_files,
)


def prepare_subdir(base_dir, fmt):
    fmt_dir = pathlib.Path(f"{base_dir}/{fmt}/")
    fmt_dir.mkdir(parents=True, exist_ok=True)
    return fmt_dir


def run_remarks(
    input_dir,
    output_dir,
    targets=None,
    pdf_name=None,
    ann_type=None,
    combined_pdf=False,
):
    for path in pathlib.Path(f"{input_dir}/").glob("*.pdf"):
        pages = list_pages_uuids(path)
        name = get_visible_name(path)
        rm_files = list_ann_rm_files(path)

        if pdf_name and (pdf_name not in name):
            continue

        if not pages or not name or not rm_files or not len(rm_files):
            continue

        page_magnitude = math.floor(math.log10(len(pages))) + 1
        in_device_path = get_ui_path(path)

        _dir = pathlib.Path(f"{output_dir}/{in_device_path}/{name}/")
        _dir.mkdir(parents=True, exist_ok=True)

        pdf_src = fitz.open(path)

        print(f"Working on PDF file: {path}")
        print(f'PDF visibleName: "{name}"')
        print(f"PDF in-device directory: {in_device_path}")

        for rm_file in rm_files:
            page_idx = pages.index(f"{rm_file.stem}")

            pdf_w, pdf_h = get_pdf_page_dims(path, page_idx=page_idx)
            scale = get_pdf_to_device_ratio(pdf_w, pdf_h)

            highlights, scribbles = parse_rm_file(rm_file)

            if ann_type == "highlights":
                parsed_data = highlights
            elif ann_type == "scribbles":
                parsed_data = scribbles
            else:  # merge both annotated types
                parsed_data = {"layers": highlights["layers"] + scribbles["layers"]}

            if not parsed_data.get("layers"):
                continue

            parsed_data = rescale_parsed_data(parsed_data, scale)

            if "svg" in targets:
                svg_str = draw_svg(parsed_data)

                subdir = prepare_subdir(_dir, "svg")
                with open(f"{subdir}/{page_idx:0{page_magnitude}}.svg", "w") as f:
                    f.write(svg_str)

            ann_doc = fitz.open()

            rm_w_rescaled, rm_h_scaled = get_rescaled_device_dims(scale)
            ann_page = ann_doc.newPage(width=rm_w_rescaled, height=rm_h_scaled)

            pdf_w_adj, pdf_h_adj = get_adjusted_pdf_dims(pdf_w, pdf_h, scale)
            pdf_rect = fitz.Rect(0, 0, pdf_w_adj, pdf_h_adj)

            ann_page.showPDFpage(pdf_rect, pdf_src, pno=page_idx)

            should_extract_text = ann_type != "scribbles" and highlights
            extractable = is_text_extractable(pdf_src[page_idx])
            ocred = False

            if should_extract_text and not extractable and is_tool("ocrmypdf"):
                print(
                    f"Couldn't extract text from page #{page_idx}. Will OCR it. Hold on\n"
                )

                tmp_file = "_tmp.pdf"
                ann_doc.save(tmp_file)
                ann_doc.close()

                # Note: as of July 2020, ocrmypdf does not recognize handwriting
                tmp_file = run_ocr(tmp_file)

                ann_doc = fitz.open(tmp_file)
                pathlib.Path(tmp_file).unlink()

                ann_page = ann_doc[0]
                ocred = True

            ann_page = draw_pdf(parsed_data, ann_page)

            if "pdf" in targets:
                subdir = prepare_subdir(_dir, "pdf")
                ann_doc.save(f"{subdir}/{page_idx:0{page_magnitude}}.pdf")

            if "png" in targets:
                # (2, 2) is a short-hand for 2x zoom on x and y
                # ref: https://pymupdf.readthedocs.io/en/latest/page.html#Page.getPixmap
                pixmap = ann_page.getPixmap(matrix=fitz.Matrix(2, 2))

                subdir = prepare_subdir(_dir, "png")
                pixmap.writePNG(f"{subdir}/{page_idx:0{page_magnitude}}.png")

            if "md" in targets:
                if should_extract_text and (extractable or ocred):
                    md_str = md_from_blocks(ann_page)
                    # TODO: add proper table extraction?
                    # https://pymupdf.readthedocs.io/en/latest/faq.html#how-to-extract-tables-from-documents

                    # TODO: maybe also add highlighted image (pixmap) extraction?

                    subdir = prepare_subdir(_dir, "md")
                    with open(f"{subdir}/{page_idx:0{page_magnitude}}.md", "w") as f:
                        f.write(md_str)

                elif not highlights:
                    print(f"Couldn't find any highlighted text on page #{page_idx}")
                elif ann_type == "scribbles":
                    print(
                        "Found some highlighted text but `--ann_type` flag was set to `scribbles` only"
                    )
                else:
                    print(
                        f"Found highlighted text but couldn't create markdown from page #{page_idx}"
                    )

            if combined_pdf:
                pdf_src.insertPDF(ann_doc, start_at=page_idx)
                pdf_src.deletePage(page_idx + 1)

            ann_doc.close()

        if combined_pdf:
            pdf_src.save(f"{output_dir}/{name} _remarks.pdf")

        pdf_src.close()

