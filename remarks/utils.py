import json
import pathlib

import fitz  # PyMuPDF


def get_pdf_name(path):
    metadata_file = path.with_name(f"{path.stem}.metadata")
    if not metadata_file.exists():
        return None
    metadata = json.loads(open(metadata_file).read())
    # print(metadata)
    return metadata["visibleName"]


def get_pdf_page_dims(path, page_number=0):
    with fitz.open(path) as doc:
        # doc.pageCount
        first_page = doc.loadPage(page_number)
        return first_page.rect.width, first_page.rect.height


def list_pages_uuids(path):
    content_file = path.with_name(f"{path.stem}.content")
    if not content_file.exists():
        return None
    content = json.loads(open(content_file).read())
    # print(content)
    return content["pages"]


def list_ann_rm_files(path):
    content_dir = pathlib.Path(f"{path.parents[0]}/{path.stem}/")
    if not content_dir.is_dir():
        return None
    # print(content_dir)
    return list(content_dir.glob("*.rm"))
