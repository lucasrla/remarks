import json
import pathlib

import fitz  # PyMuPDF
from os.path import dirname, abspath, join


def get_pdf_name(path):
    metadata_file = path.with_name(f"{path.stem}.metadata")
    if not metadata_file.exists():
        return None
    metadata = json.loads(open(metadata_file).read())
    # print(metadata)
    return metadata["visibleName"]

def get_pdf_path(path):
    metadata_file = path.with_name(f"{path.stem}.metadata")
    if not metadata_file.exists():
        return None
    metadata = json.loads(open(metadata_file).read())
    # Check the parent 
    path_tmp = ""
    file_path = path
    parent_filename = metadata["parent"]
    while parent_filename != "":
        # First get the total path of the parent
        parent_path = join(dirname(abspath(file_path)), metadata["parent"])
        # Get the meta data of this parent
        metadata_file = parent_path + ".metadata"
        metadata = json.loads(open(metadata_file).read())
        parent_title = metadata["visibleName"]
        # These go in reverse order up to the top level
        path_tmp = join(parent_title,path_tmp)
        # Get the parent of this one
        parent_filename = metadata["parent"]
    # Strip off final slash
    path_tmp = path_tmp.strip("/")
    path_tmp = path_tmp.strip("\\")
    return path_tmp

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
