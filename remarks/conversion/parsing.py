import logging
import math
import struct
from enum import Enum
from pprint import pprint
from typing import Dict, List, Any, TypedDict, Tuple

import shapely.geometry as geom  # Shapely
from rmscene import read_blocks, SceneTree, build_tree, RootTextBlock, LwwValue
from rmscene.scene_items import Line, GlyphRange, Rectangle, ParagraphStyle, END_MARKER
from rmscene.text import TextDocument

from ..utils import (
    RM_WIDTH,
    RM_HEIGHT,
)

from ..dimensions import ReMarkableDimensions, REMARKABLE_DOCUMENT

# reMarkable tools
# http://web.archive.org/web/20190806120447/https://support.remarkable.com/hc/en-us/articles/115004558545-5-1-Tools-Overview
RM_TOOLS = {
    0: "Brush",
    12: "Brush",
    2: "Ballpoint",
    15: "Ballpoint",
    4: "Fineliner",
    17: "Fineliner",
    3: "Marker",
    16: "Marker",
    6: "Eraser",
    8: "EraseArea",
    7: "SharpPencil",
    13: "SharpPencil",
    1: "TiltPencil",
    14: "TiltPencil",
    5: "Highlighter",
    18: "Highlighter",
    21: "CalligraphyPen",
}


# TODO: My parsing & drawing is such a mess... Refactor it someday

# TODO: Review stroke-width and opacity for all tools

# TODO: Add support for pressure and tilting as well
# for e.g. Paintbrush (Brush), CalligraphyPen, TiltPencil, etc


def process_tool(pen, dims, w, opc):
    tool = RM_TOOLS[pen]

    if tool == "Brush" or tool == "CalligraphyPen":
        pass
    elif tool == "Ballpoint" or tool == "Fineliner":
        pass
    elif tool == "Marker":
        w = (64 * w - 112) / 2
        opc = 0.9
    elif tool == "Highlighter":
        w = 30
        opc = 0.6
        # cc = 3
    elif tool == "Eraser":
        w = w * 18 * 2.3
        # cc = 2
    elif tool == "SharpPencil" or tool == "TiltPencil":
        w = 16 * w - 27
        opc = 0.9
    elif tool == "EraseArea":
        opc = 0.0
    else:
        raise ValueError(f"Found an unknown tool: {pen}")

    w /= 2.3  # Adjust to A4

    name_code = f"{tool}_{pen}"

    # Shorthands: w for stroke-width, opc for opacity
    return name_code, w, opc


def adjust_xypos_sizes(xpos, ypos, dims: ReMarkableDimensions):
    ratio = (dims.height / dims.height) / (RM_HEIGHT / RM_WIDTH)

    if ratio > 1:
        xpos = ratio * ((xpos * dims.height) / RM_WIDTH)
        ypos = (ypos * dims.height) / RM_HEIGHT
    else:
        xpos = (xpos * dims.height) / RM_WIDTH
        ypos = (1 / ratio) * (ypos * dims.height) / RM_HEIGHT

    return xpos, ypos


def update_stroke_dict(st, tool):
    st[tool] = {}
    st[tool]["segments"] = []
    return st


def create_seg_dict(opacity, stroke_width, cc):
    sg = {}
    sg["style"] = {}
    sg["style"]["opacity"] = f"{opacity:.3f}"
    sg["style"]["stroke-width"] = f"{stroke_width:.3f}"
    sg["style"]["color-code"] = cc
    sg["points"] = []
    return sg


def update_boundaries_from_point(x, y, boundaries):
    boundaries["x_max"] = max(boundaries["x_max"], x)
    boundaries["y_max"] = max(boundaries["y_max"], y)
    boundaries["x_min"] = min(boundaries["x_min"], x)
    boundaries["y_min"] = min(boundaries["y_min"], y)


class TRemarksRectangle:
    color: int
    rectangles: List[Rectangle]


class TLayer(TypedDict):
    strokes: Dict[str, Any]
    rectangles: List[TRemarksRectangle]


class TTextBlock(TypedDict):
    pos_x: float
    pos_y: float
    width: float
    text: TextDocument


class TLayers(TypedDict):
    layers: List[TLayer]
    highlights: List[str]
    text: TTextBlock | None


class TextStyles(Enum):
    BOLD_OPEN = 1
    BOLD_CLOSE = 2
    ITALIC_OPEN = 3
    ITALIC_CLOSE = 4


def parse_v6(file_path: str) -> Tuple[TLayers, bool]:
    output: TLayers = {
        "layers": [{"strokes": {}, "rectangles": []}],
        "highlights": [],
        "text": None,
    }

    dims = determine_document_dimensions(file_path)

    with open(file_path, "rb") as f:
        tree = SceneTree()
        blocks = [b for b in read_blocks(f)]
        build_tree(tree, blocks)

        try:
            for block in blocks:
                if isinstance(block, RootTextBlock):
                    output["text"] = {
                        "pos_x": block.value.pos_x,
                        "pos_y": block.value.pos_y,
                        "width": block.value.width,
                        "text": TextDocument.from_scene_item(tree.root_text),
                    }
            for el in tree.walk():
                if isinstance(el, GlyphRange):
                    layer = output["layers"][0]
                    highlight: TRemarksRectangle = {
                        "rectangles": el.rectangles,
                        "color": el.color.value,
                    }
                    layer["rectangles"].append(highlight)
                    output["highlights"].append(el)
                if isinstance(el, Line):
                    layer = output["layers"][0]

                    if el.points is None:
                        break
                    pen = el.tool.value
                    color = el.color.value
                    opacity = 1
                    stroke_width = el.thickness_scale

                    tool, stroke_width, opacity = process_tool(
                        pen, dims, stroke_width, opacity
                    )
                    segment = create_seg_dict(opacity, stroke_width, color)
                    points_ = [(f"{p.x:.3f}", f"{p.y:.3f}") for p in el.points]
                    segment["points"].append(points_)
                    if tool not in layer["strokes"].keys():
                        layer["strokes"] = update_stroke_dict(layer["strokes"], tool)
                    layer["strokes"][tool]["segments"].append(segment)
        except AssertionError:
            print("ReMarkable broken data")

    return output, False


class UnexpectedTextStylingException(Exception):
    pass


def style_text(bold: bool, italic: bool, value: int) -> Tuple[bool, bool]:
    """
    1 = <b>
    2 = </b>
    3 = <i>
    4 = </i>
    """
    if value == TextStyles.BOLD_OPEN.value:
        return True, italic
    elif value == TextStyles.BOLD_CLOSE.value:
        return False, italic
    elif value == TextStyles.ITALIC_OPEN.value:
        return bold, True
    elif value == TextStyles.ITALIC_CLOSE.value:
        return bold, False
    else:
        raise UnexpectedTextStylingException(f"Unexpected text style value: {value}")


def roundup(num, increment):
    return int(math.ceil(num / increment)) * increment


def rounddown(num, increment):
    return int(math.floor(num / increment)) * increment


def determine_document_dimensions(file_path) -> ReMarkableDimensions:
    """The ReMarkable has dynamic document size in v6. The dimensions are not available anywhere, so we'll compute
    them from points"""
    # This is the horizontal space you get as defined by ReMarkable.
    # Not coincidentally, this is (RM_HEIGHT - RM_WIDTH)/2
    # Adding two increments, which is the max, you end up with an exactly square aspect ratio
    # hori = (RM_HEIGHT - RM_WIDTH) / 2
    dims = {
        "x_min": -RM_WIDTH / 2,
        "x_max": RM_WIDTH / 2 - 1,
        "y_min": 0,
        "y_max": RM_HEIGHT - 1,
    }
    with open(file_path, "rb") as f:
        blocks = read_blocks(f)
        tree = SceneTree()
        build_tree(tree, blocks)

        try:
            for el in tree.walk():
                if isinstance(el, Line):
                    for p in el.points:
                        update_boundaries_from_point(p.x, p.y, dims)
        except AssertionError:
            print("ReMarkable broken data")

    return ReMarkableDimensions(
        dims["x_max"] - dims["x_min"], dims["y_max"] - dims["y_min"]
    )


def check_rm_file_version(file_path):
    with open(file_path, "rb") as f:
        data = f.read()

    expected_header_fmt = b"reMarkable .lines file, version=0          "

    if len(data) < len(expected_header_fmt) + 4:
        logging.error(f"- .rm file ({file_path}) seems too short to be valid")
        return False

    offset = 0
    fmt = f"<{len(expected_header_fmt)}sI"

    header, nlayers = struct.unpack_from(fmt, data, offset)

    is_v3 = header == b"reMarkable .lines file, version=3          "
    is_v5 = header == b"reMarkable .lines file, version=5          "
    is_v6 = header == b"reMarkable .lines file, version=6          "

    if is_v6:
        return True
        # logging.error(
        #     f"- Found a v6 .rm file ({file_path}) created with reMarkable software >= 3.0. Unfortunately we do not support this version yet. More info: https://github.com/lucasrla/remarks/issues/58"
        # )

    if (not is_v3 and not is_v5) or nlayers < 1:
        logging.error(
            f"- .rm file ({file_path}) doesn't look like a valid one: <header={header}><nlayers={nlayers}>"
        )
        return False

    return True


def parse_rm_file(file_path: str, dims=None) -> Tuple[Tuple[TLayers, bool], str]:
    if dims is None:
        dims = REMARKABLE_DOCUMENT
    with open(file_path, "rb") as f:
        data = f.read()

    expected_header_fmt = b"reMarkable .lines file, version=0          "

    expected_header_v3 = b"reMarkable .lines file, version=3          "
    expected_header_v5 = b"reMarkable .lines file, version=5          "
    expected_header_v6 = b"reMarkable .lines file, version=6          "
    if len(data) < len(expected_header_v5) + 4:
        raise ValueError(f"{file_path} is too short to be a valid .rm file")

    offset = 0
    fmt = f"<{len(expected_header_fmt)}sI"

    header, nlayers = struct.unpack_from(fmt, data, offset)

    offset += struct.calcsize(fmt)

    is_v3 = header == expected_header_v3
    is_v5 = header == expected_header_v5
    is_v6 = header == expected_header_v6

    if is_v3 or is_v5:
        return parse_v3_to_v5(data, dims, is_v3, nlayers, offset), "V5"

    if is_v6:
        return parse_v6(file_path), "V6"

    raise ValueError(
        f"{file_path} is not a valid .rm file: <header={header}><nlayers={nlayers}>"
    )


def parse_v3_to_v5(data, dims: ReMarkableDimensions, is_v3, nlayers, offset):
    output: TLayers = {"layers": [], "highlights": [], "text": []}
    has_highlighter = False
    for _ in range(nlayers):
        fmt = "<I"
        (nstrokes,) = struct.unpack_from(fmt, data, offset)
        offset += struct.calcsize(fmt)

        new_layer: TLayer = {"strokes": {}, "rectangles": []}

        for _ in range(nstrokes):
            if is_v3:
                fmt = "<IIIfI"
                # cc for color-code, w for stroke-width
                pen, cc, _, w, nsegs = struct.unpack_from(fmt, data, offset)
                offset += struct.calcsize(fmt)
            else:
                fmt = "<IIIffI"
                pen, cc, _, w, _, nsegs = struct.unpack_from(fmt, data, offset)
                offset += struct.calcsize(fmt)

            opc = 1  # opacity

            tool, stroke_width, opacity = process_tool(pen, dims, w, opc)

            if "Highlighter" in tool:
                has_highlighter = True

            if tool not in new_layer["strokes"].keys():
                new_layer["strokes"] = update_stroke_dict(new_layer["strokes"], tool)

            sg = create_seg_dict(opacity, stroke_width, cc)
            p = []

            for _ in range(nsegs):
                fmt = "<ffffff"
                x, y, press, tilt, _, _ = struct.unpack_from(fmt, data, offset)
                offset += struct.calcsize(fmt)

                xpos, ypos = adjust_xypos_sizes(x, y, dims)
                p.append((f"{xpos:.3f}", f"{ypos:.3f}"))

            sg["points"].append(p)
            new_layer["strokes"][tool]["segments"].append(sg)

        output["layers"].append(new_layer)
    return output, has_highlighter


# TODO: make the rescale part of the parsing (or perhaps drawing?) process
def rescale_parsed_data(
    parsed_data: TLayers, scale: float, offset_x: int, offset_y: int
):
    for layer in parsed_data["layers"]:
        for _, st_value in layer["strokes"].items():
            for _, sg_value in enumerate(st_value["segments"]):
                sg_value["style"][
                    "stroke-width"
                ] = f"{float(sg_value['style']['stroke-width']):.3f}"

                for i, points in enumerate(sg_value["points"]):
                    for k, point in enumerate(points):
                        sg_value["points"][i][k] = (
                            f"{float(point[0]) * scale + offset_x:.3f}",
                            f"{float(point[1]) * scale + offset_y:.3f}",
                        )

    if "text" in parsed_data and parsed_data["text"]:
        parsed_data["text"]["pos_x"] = parsed_data["text"]["pos_x"] + offset_x
        parsed_data["text"]["pos_y"] = parsed_data["text"]["pos_y"] + offset_y

    for layer in parsed_data["layers"]:
        for rmRectangles in layer["rectangles"]:
            for geomRectangle in rmRectangles["rectangles"]:
                geomRectangle.x = geomRectangle.x + offset_x
                geomRectangle.y = geomRectangle.y + offset_y
                # geomRectangle.w = geomRectangle.w
                # geomRectangle.h = geomRectangle.h

    return parsed_data


# The line segment will pop up hundreds or thousands of times in notebooks where it is relevant.
# this flag ensures it will print at most once.
_line_segment_warning_has_been_shown = False


def get_ann_max_bound(parsed_data):
    global _line_segment_warning_has_been_shown
    # https://shapely.readthedocs.io/en/stable/manual.html#LineString
    # https://shapely.readthedocs.io/en/stable/manual.html#MultiLineString
    # https://shapely.readthedocs.io/en/stable/manual.html#object.bounds

    collection = []

    for strokes in parsed_data["layers"]:
        for _, st_value in strokes["strokes"].items():
            for _, sg_value in enumerate(st_value["segments"]):
                for points in sg_value["points"]:
                    if len(points) <= 1:
                        # line needs at least two points, see testcase v2_notebook_complex
                        if not _line_segment_warning_has_been_shown:
                            logging.warning(
                                "- Found a segment with a single point, will ignore it. Please report this "
                                "issue at: https://github.com/lucasrla/remarks/issues/64 "
                            )
                            _line_segment_warning_has_been_shown = True
                        continue
                    line = geom.LineString([(float(p[0]), float(p[1])) for p in points])
                    collection.append(line)

    if len(collection) > 0:
        (minx, miny, maxx, maxy) = geom.MultiLineString(collection).bounds
        return (maxx, maxy, minx, miny)
    else:
        return (0, 0, 0, 0)
