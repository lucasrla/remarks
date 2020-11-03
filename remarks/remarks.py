import pathlib

import fitz  # PyMuPDF

from .conversion.parsing import parse_rm_file, RM_WIDTH, RM_HEIGHT
from .conversion.drawing import draw_svg, draw_pdf
from .conversion.text import md_from_blocks, is_text_extractable
from .conversion.ocrmypdf import is_tool, run_ocr

from .utils import get_pdf_name, get_pdf_page_dims, list_pages_uuids, list_ann_rm_files


def prepare_subdir(base_dir, fmt):
    fmt_dir = pathlib.Path(f"{base_dir}/{fmt}/")
    fmt_dir.mkdir(parents=True, exist_ok=True)
    return fmt_dir


def run_remarks(input_dir, output_dir, targets=None, pdf_name=None, ann_type=None):
    for path in pathlib.Path(f"{input_dir}/").glob("*.pdf"):
        w, h = get_pdf_page_dims(path)

        pages = list_pages_uuids(path)
        name = get_pdf_name(path)
        rm_files = list_ann_rm_files(path)

        if pdf_name and (pdf_name not in name):
            continue

        if not pages or not name or not rm_files or not len(rm_files):
            continue

        _dir = pathlib.Path(f"{output_dir}/{name}/")
        _dir.mkdir(parents=True, exist_ok=True)

        pdf_src = fitz.open(path)

        print(f"Working on PDF file: {path}")
        print(f'PDF visibleName: "{name}"')

        for rm_file in rm_files:
            page_idx = pages.index(f"{rm_file.stem}")
            # print(f"- page #{page_idx}")

            highlights, scribbles = parse_rm_file(rm_file)

            if ann_type == "highlights":
                parsed_data = highlights
            elif ann_type == "scribbles":
                parsed_data = scribbles
            else:  # get both types
                parsed_data = {'layers': highlights['layers'] + scribbles['layers']}

            if not parsed_data.get('layers'):
                continue

            if "svg" in targets:
                svg_str = draw_svg(parsed_data)

                subdir = prepare_subdir(_dir, "svg")
                with open(f"{subdir}/{page_idx}.svg", "w") as f:
                    f.write(svg_str)

            # Inspired by https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/examples/posterize.py
            ann_doc = fitz.open()
            ann_page = ann_doc.newPage(width=RM_WIDTH, height=RM_HEIGHT)

            # ann_page = doc.newPage(width=w, height=h)
            # print(ann_page.rect)

            if (w / h) >= (RM_WIDTH / RM_HEIGHT):
                adj_rect = fitz.Rect(0, 0, RM_WIDTH, h * (RM_WIDTH / w))
            else:
                adj_rect = fitz.Rect(0, 0, w * (RM_HEIGHT / h), RM_HEIGHT)

            ann_page.showPDFpage(adj_rect, pdf_src, pno=page_idx)

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
                ann_doc.save(f"{subdir}/{page_idx}.pdf")

            if "png" in targets:
                # (2, 2) is a short-hand for 2x zoom on x and y
                # ref: https://pymupdf.readthedocs.io/en/latest/page.html#Page.getPixmap
                pixmap = ann_page.getPixmap(matrix=fitz.Matrix(2, 2))

                subdir = prepare_subdir(_dir, "png")
                pixmap.writePNG(f"{subdir}/{page_idx}.png")

            if "md" in targets:
                if should_extract_text and (extractable or ocred):
                    md_str = md_from_blocks(ann_page)
                    # TODO: add proper table extraction?
                    # https://pymupdf.readthedocs.io/en/latest/faq.html#how-to-extract-tables-from-documents

                    # TODO: maybe also add highlighted image (pixmap) extraction?

                    subdir = prepare_subdir(_dir, "md")
                    with open(f"{subdir}/{page_idx}.md", "w") as f:
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

            # Inserting annotated page into source PDF
            # but beware, we are losing original page size (see the TODO below)
            #
            # pdf_src.insertPDF(ann_doc, start_at=page_idx)
            # pdf_src.deletePage(page_idx + 1)

            # TODO: come up with a way to adjust size of ann_page before inserting it into the original PDF
            # the code below does not work because showPDFpage does not carry annotations over
            #
            # rect_src = fitz.Rect(0, 0, w, h)
            # page_src = pdf_src.newPage()
            # page_src.showPDFpage(rect_src, ann_doc, pno=(page_idx + 1))

            ann_doc.close()

        # TODO: bookmarks and table of contents of original PDF are missing in the -REMARKS.pdf file
        # how hard is to reconstruct them?
        # ref: note #2 at https://pymupdf.readthedocs.io/en/latest/document.html#Document.insertPDF
        # ref: https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/examples/PDFjoiner.py#L462
        #
        # pdf_src.save(f"{output_dir}/{name}-REMARKS.pdf")

        pdf_src.close()

