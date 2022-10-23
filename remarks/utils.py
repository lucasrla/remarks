import json
import pathlib


# reMarkable's device dimensions
RM_WIDTH = 1404
RM_HEIGHT = 1872


def read_meta_file(path, suffix=".metadata"):
    file = path.with_name(f"{path.stem}{suffix}")
    if not file.exists():
        return None
    data = json.loads(open(file).read())
    return data


def is_document(path):
    metadata = read_meta_file(path)
    return metadata["type"] == "DocumentType"


def get_document_filetype(path):
    content = read_meta_file(path, suffix=".content")
    return content["fileType"]


def get_visible_name(path):
    metadata = read_meta_file(path)
    return metadata["visibleName"]


def get_ui_path(path):
    metadata = read_meta_file(path)
    parent_filename = metadata["parent"]

    # Check the parent
    ui_path = pathlib.Path("")

    while parent_filename != "":
        # First get the total path of the parent
        parent_path = pathlib.Path(path.parent, metadata["parent"])

        # Get the meta data of this parent
        metadata = read_meta_file(parent_path)
        if not metadata:
            return pathlib.Path(".")

        parent_title = metadata["visibleName"]

        # These go in reverse order up to the top level
        ui_path = pathlib.Path(parent_title).joinpath(ui_path)

        # Get the parent of this one
        parent_filename = metadata["parent"]

    return ui_path


def get_pages_data(path):
    content = read_meta_file(path, suffix=".content")
    if "redirectionPageMap" in content:
        return content["pages"], content["redirectionPageMap"]
    return content["pages"], []


def list_ann_rm_files(path):
    content_dir = pathlib.Path(f"{path.parents[0]}/{path.stem}/")
    # print("content_dir", content_dir, not content_dir.is_dir())
    if not content_dir.is_dir():
        return None
    return list(content_dir.glob("*.rm"))


def list_hl_json_files(path):
    hl_dir = pathlib.Path(f"{path.parents[0]}/{path.stem}.highlights/")
    # print("hl_dir", hl_dir, not hl_dir.is_dir())
    if not hl_dir.is_dir():
        return []
    return list(hl_dir.glob("*.json"))


def load_json_file(path):
    with open(path) as f:
        data = json.load(f)
    return data


def prepare_subdir(base_dir, fmt):
    fmt_dir = pathlib.Path(f"{base_dir}/{fmt}/")
    fmt_dir.mkdir(parents=True, exist_ok=True)
    return fmt_dir


def rescale_given_device_aspect_ratio(page_dims):
    page_width, page_height = page_dims
    page_aspect_ratio = page_width / page_height
    device_aspect_ratio = RM_WIDTH / RM_HEIGHT

    scale = 1
    page_width_rescaled = page_width
    page_height_rescaled = page_height

    # If doc page is wider than reMarkable's aspect ratio,
    # use doc_width as reference for the scale ratio.
    # There should be no "leftover" (gap) on the horizontal
    if page_aspect_ratio >= device_aspect_ratio:
        scale = page_width / RM_WIDTH
        page_width_rescaled = RM_WIDTH * scale

    # PDF page is narrower than reMarkable's a/r,
    # use pdf_height as reference for the scale ratio.
    # There should be no "leftover" (gap) on the vertical
    else:
        scale = page_height / RM_HEIGHT
        page_height_rescaled = RM_HEIGHT * scale

    return (page_width_rescaled, page_height_rescaled), scale
