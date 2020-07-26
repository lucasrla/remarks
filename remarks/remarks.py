import pathlib

import fitz  # PyMuPDF

from .conversion.parsing import parse_rm_file, RM_WIDTH, RM_HEIGHT
from .conversion.drawing import draw_svg, draw_pdf
from .conversion.text import extract_highlighted_text, create_paragraph_md

from .utils import get_pdf_name, get_pdf_page_dims, list_pages_uuids, list_ann_rm_files


def run_remarks(input_dir, output_dir, targets=["pdf", "md", "png", "svg"]):
    for path in pathlib.Path(f"{input_dir}/").glob("*.pdf"):
        w, h = get_pdf_page_dims(path)

        pages = list_pages_uuids(path)
        name = get_pdf_name(path)
        rm_files = list_ann_rm_files(path)

        if not pages or not name or not rm_files or not len(rm_files):
            continue

        _dir = pathlib.Path(f"{output_dir}/{name}/")
        _dir.mkdir(parents=True, exist_ok=True)

        pdf_src = fitz.open(path)

        for rm_file in rm_files:
            page_idx = pages.index(f"{rm_file.stem}")

            # parsed_data = parse_rm_file(rm_file, dims={"x": w, "y": h})
            parsed_data = parse_rm_file(rm_file)
            # print(parsed_data)

            if "svg" in targets:
                # svg_str = draw_svg(parsed_data, dims={"x": w, "y": h})
                svg_str = draw_svg(parsed_data)
                # print(svg_str)

                _ = pathlib.Path(f"{_dir}/svg/")
                _.mkdir(parents=True, exist_ok=True)
                out_file = f"{_}/{page_idx}.svg"
                with open(out_file, "w") as f:
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

            ann_page = draw_pdf(parsed_data, ann_page)

            if "png" in targets:
                # (2, 2) is a short-hand for 2x zoom on x and y
                # ref: https://pymupdf.readthedocs.io/en/latest/page.html#Page.getPixmap
                pixmap = ann_page.getPixmap(matrix=fitz.Matrix(2, 2))

                _ = pathlib.Path(f"{_dir}/png/")
                _.mkdir(parents=True, exist_ok=True)
                pixmap.writePNG(f"{_}/{page_idx}.png")

            if "md" in targets:
                highlighted_groups = extract_highlighted_text(ann_page)
                md_str = create_paragraph_md(ann_page, highlighted_groups)

                # TODO: add proper table extraction?
                # https://pymupdf.readthedocs.io/en/latest/faq.html#how-to-extract-tables-from-documents

                # TODO: maybe also add highlighted image (pixmap) extraction?

                _ = pathlib.Path(f"{_dir}/md/")
                _.mkdir(parents=True, exist_ok=True)
                out_file = f"{_}/{page_idx}.md"
                with open(out_file, "w") as f:
                    f.write(md_str)

            if "pdf" in targets:
                _ = pathlib.Path(f"{_dir}/pdf/")
                _.mkdir(parents=True, exist_ok=True)
                ann_doc.save(f"{_}/{page_idx}.pdf")

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

