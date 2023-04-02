import logging
import struct

import shapely.geometry as geom  # Shapely

from ..utils import (
    RM_WIDTH,
    RM_HEIGHT,
)

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
    # print(tool)

    if tool == "Brush" or tool == "CalligraphyPen":
        pass
    elif tool == "Ballpoint" or tool == "Fineliner":
        w = 32 * w * w - 116 * w + 107
        if dims["x"] == RM_WIDTH and dims["y"] == RM_HEIGHT:  # defaults
            w *= 1.8
    elif tool == "Marker":
        w = (64 * w - 112) / 2
        opc = 0.9
    elif tool == "Highlighter":
        w = 30
        opc = 0.6
        # cc = 3
    elif tool == "Eraser":
        w = w * 6 * 2.3
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


def adjust_xypos_sizes(xpos, ypos, dims):
    ratio = (dims["y"] / dims["x"]) / (RM_HEIGHT / RM_WIDTH)

    if ratio > 1:
        xpos = ratio * ((xpos * dims["x"]) / RM_WIDTH)
        ypos = (ypos * dims["y"]) / RM_HEIGHT
    else:
        xpos = (xpos * dims["x"]) / RM_WIDTH
        ypos = (1 / ratio) * (ypos * dims["y"]) / RM_HEIGHT

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


def check_rm_file_version(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    # print("data:", data)

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
        logging.error(
            f"- Found a v6 .rm file ({file_path}) created with reMarkable software >= 3.0. Unfortunately we do not support this version yet. More info: https://github.com/lucasrla/remarks/issues/58"
        )
        return False

    if (not is_v3 and not is_v5) or nlayers < 1:
        logging.error(
            f"- .rm file ({file_path}) doesn't look like a valid one: <header={header}><nlayers={nlayers}>"
        )
        return False

    return True


def parse_rm_file(file_path, dims={
    "x": RM_WIDTH,
    "y": RM_HEIGHT}):
    with open(file_path, "rb") as f:
        data = f.read()

    expected_header_fmt = b"reMarkable .lines file, version=0          "

    offset = 0
    fmt = f"<{len(expected_header_fmt)}sI"

    header, nlayers = struct.unpack_from(fmt, data, offset)
    # print("header, nlayers", header, nlayers)

    offset += struct.calcsize(fmt)

    is_v3 = header == b"reMarkable .lines file, version=3          "
    is_v5 = header == b"reMarkable .lines file, version=5          "

    output = {}
    output["layers"] = []

    has_highlighter = False

    for _ in range(nlayers):
        fmt = "<I"
        (nstrokes,) = struct.unpack_from(fmt, data, offset)
        offset += struct.calcsize(fmt)

        l = {}
        l["strokes"] = {}

        for _ in range(nstrokes):
            if is_v3:
                fmt = "<IIIfI"
                # cc for color-code, w for stroke-width
                pen, cc, _, w, nsegs = struct.unpack_from(fmt, data, offset)
                offset += struct.calcsize(fmt)
            if is_v5:
                fmt = "<IIIffI"
                pen, cc, _, w, _, nsegs = struct.unpack_from(fmt, data, offset)
                offset += struct.calcsize(fmt)

            opc = 1  # opacity

            tool, stroke_width, opacity = process_tool(pen, dims, w, opc)

            if "Highlighter" in tool:
                has_highlighter = True

            if tool not in l["strokes"].keys():
                l["strokes"] = update_stroke_dict(l["strokes"], tool)

            sg = create_seg_dict(opacity, stroke_width, cc)
            p = []

            for _ in range(nsegs):
                fmt = "<ffffff"
                x, y, press, tilt, _, _ = struct.unpack_from(fmt, data, offset)
                offset += struct.calcsize(fmt)

                xpos, ypos = adjust_xypos_sizes(x, y, dims)
                p.append((f"{xpos:.3f}", f"{ypos:.3f}"))

            sg["points"].append(p)
            # print("sg", sg)
            l["strokes"][tool]["segments"].append(sg)

        output["layers"].append(l)

    return output, has_highlighter


# TODO: make the rescale part of the parsing (or perhaps drawing?) process
def rescale_parsed_data(parsed_data, scale):
    if scale == 1:
        return parsed_data

    for strokes in parsed_data["layers"]:
        for _, st_value in strokes["strokes"].items():
            for _, sg_value in enumerate(st_value["segments"]):
                # print("sg_value", sg_value)

                sg_value["style"][
                    "stroke-width"
                ] = f"{float(sg_value['style']['stroke-width']) * scale:.3f}"

                for i, points in enumerate(sg_value["points"]):
                    for k, point in enumerate(points):
                        sg_value["points"][i][k] = (
                            f"{float(point[0]) * scale:.3f}",
                            f"{float(point[1]) * scale:.3f}",
                        )

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
                            logging.warning("- Found a segment with a single point, will ignore it. Please report this "
                                            "issue at: https://github.com/lucasrla/remarks/issues/64 ")
                            _line_segment_warning_has_been_shown = True
                        continue
                    line = geom.LineString([(float(p[0]), float(p[1])) for p in points])
                    collection.append(line)

    if len(collection) > 0:
        (minx, miny, maxx, maxy) = geom.MultiLineString(collection).bounds
        return (maxx, maxy)
    else:
        return (0, 0)
