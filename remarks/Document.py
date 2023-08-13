import math
from typing import List

import fitz

from remarks.conversion import check_rm_file_version
from remarks.conversion.parsing import determine_document_dimensions
from remarks.dimensions import REMARKABLE_DOCUMENT, ReMarkableDimensions
from remarks.utils import (
    get_document_filetype,
    get_document_tags,
    list_hl_json_files,
    is_inserted_page,
    get_pages_data,
    list_ann_rm_files,
    get_visible_name,
)


class Document:
    def __init__(self, metadata_path):
        self.metadata_path = metadata_path
        self.pages_list, self.pages_map = get_pages_data(metadata_path)
        self.doc_type = get_document_filetype(metadata_path)
        self.name = get_visible_name(metadata_path)

        # annotations
        self.rm_tags = get_document_tags(metadata_path)
        self.rm_annotation_files = list_ann_rm_files(metadata_path)
        self.rm_highlight_files = list_hl_json_files(metadata_path)

    def open_source_pdf(self) -> fitz.Document:
        if self.doc_type in ["pdf", "epub"]:
            f = self.metadata_path.with_name(f"{self.metadata_path.stem}.pdf")
            pdf_src = fitz.open(f)

            for i, page_idx in enumerate(self.pages_map):
                if is_inserted_page(page_idx):
                    pdf_src.new_page(
                        width=REMARKABLE_DOCUMENT.to_mm().to_mu().width,
                        height=REMARKABLE_DOCUMENT.to_mm().to_mu().height,
                        pno=i,
                    )

        # Thanks to @apoorvkh
        # - https://github.com/lucasrla/remarks/issues/11#issuecomment-1287175782
        # - https://github.com/apoorvkh/remarks/blob/64dd3b586b96195b00e727fc1f1e537b90d841dc/remarks/remarks.py#L16-L38
        elif self.doc_type == "notebook":
            # PyMuPDF's A4 default is width=595, height=842
            # - https://pymupdf.readthedocs.io/en/latest/document.html#Document.new_page
            # The 0.42 below is just me eye-balling PyMuPDF's defaults:
            # 1404*0.42 ~= 590 and 1872*0.4 ~= 786
            #
            # reMarkable's desktop app exports notebooks to PDF with 445 x 594, in
            # terms of scale it is 445/1404 = ~0.316
            # Open an empty PDF to be treated as if it were the original document
            pdf_src = fitz.open()
            page_sizes: List[ReMarkableDimensions] = []
            for page in self.pages_list:
                paths = filter(
                    lambda _ann_page: _ann_page.stem == page, self.rm_annotation_files
                )
                path = next(paths, None)
                if path:
                    try:
                        page_sizes.append(determine_document_dimensions(path))
                    except ValueError:
                        page_sizes.append(REMARKABLE_DOCUMENT)
                else:
                    page_sizes.append(REMARKABLE_DOCUMENT)

            # For each note page, add a blank page to the original document
            for i, dims in enumerate(page_sizes):
                mu_dims = dims.to_mm().to_mu()
                pdf_src.new_page(
                    width=mu_dims.width,
                    height=mu_dims.height,
                    pno=i,
                )

        return pdf_src

    def pages_magnitude(self):
        return math.floor(math.log10(len(self.pages_list))) + 1

    def pages(self):
        has_annotation_highlights = False

        page_uuids = set(
            [f.stem for f in self.rm_annotation_files]
            + [f.stem for f in self.rm_highlight_files]
        )

        for page_uuid in page_uuids:
            has_annotations = False
            rm_annotation_file = None

            rm_highlights_file = None
            has_smart_highlights = False

            page_idx = self.pages_list.index(f"{page_uuid}")

            for f in self.rm_annotation_files:
                if page_uuid == f.stem and check_rm_file_version(f):
                    rm_annotation_file = f
                    has_annotations = True

            for f in self.rm_highlight_files:
                if page_uuid == f.stem:
                    rm_highlights_file = f
                    has_smart_highlights = True

            yield (
                page_uuid,
                page_idx,
                rm_annotation_file,
                has_annotations,
                rm_highlights_file,
                has_smart_highlights,
            )
