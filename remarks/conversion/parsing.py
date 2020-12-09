import struct

import shapely.geometry as geom  # Shapely

# reMarkable defaults
RM_WIDTH = 1404
RM_HEIGHT = 1872

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
    7: "SharpPencil",
    13: "SharpPencil",
    1: "TiltPencil",
    14: "TiltPencil",
    8: "EraseArea",
    5: "Highlighter",
    18: "Highlighter",
}

# TODO: support Calligraphy pen (added in 2.3)
# https://support.remarkable.com/hc/en-us/articles/360013230697-Software-release-2-3


# TODO: review stroke-width and opacity for all tools,
# especially the ones with pressure and tilting capabilities.
# As of July 2020 (version 2.2.0.48), the parameters below
# don't seem to match reMarkable's (on device) rendering


def get_adjusted_pdf_dims(pdf_width, pdf_height, scale):
    if (pdf_width / pdf_height) >= (RM_WIDTH / RM_HEIGHT):
        adj_w = RM_WIDTH * scale  # "perfect" fitting, no gap
        adj_h = pdf_height
    else:
        adj_w = pdf_width
        adj_h = RM_HEIGHT * scale  # "perfect" fitting, no gap

    return adj_w, adj_h


def get_rescaled_device_dims(scale):
    return RM_WIDTH * scale, RM_HEIGHT * scale


def get_pdf_to_device_ratio(pdf_width, pdf_height):
    pdf_aspect_ratio = pdf_width / pdf_height
    device_aspect_ratio = RM_WIDTH / RM_HEIGHT

    # if PDF page is wider than reMarkable's aspect ratio,
    # use pdf_width as reference for the scale ratio.
    # there should be no "leftover" (gap) on the horizontal
    if pdf_aspect_ratio >= device_aspect_ratio:
        scale = pdf_width / RM_WIDTH

    # PDF page is narrower than reMarkable's a/r,
    # use pdf_height as reference for the scale ratio.
    # there should be no "leftover" (gap) on the vertical
    else:
        scale = pdf_height / RM_HEIGHT

    return scale


def process_tool_meta(pen, dims, w, opc, cc):
    tool = RM_TOOLS[pen]
    # print(tool)

    if tool == "Brush":
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
        cc = 3
    elif tool == "Eraser":
        w = 1280 * w * w - 4800 * w + 4510
        cc = 2
    elif tool == "SharpPencil" or tool == "TiltPencil":
        w = 16 * w - 27
        opc = 0.9
    elif tool == "EraseArea":
        opc = 0.0
    else:
        raise ValueError("Found an unknown tool: {pen}")

    w /= 2.3  # adjust for transformation to A4

    meta = {}
    meta["pen-code"] = pen
    meta["color-code"] = cc

    name_code = f"{tool}_{pen}"

    # w for stroke-width, opc for opacity
    return name_code, meta, w, opc


def adjust_xypos_sizes(xpos, ypos, dims):

    ratio = (dims["y"] / dims["x"]) / (RM_HEIGHT / RM_WIDTH)

    if ratio > 1:
        xpos = ratio * ((xpos * dims["x"]) / RM_WIDTH)
        ypos = (ypos * dims["y"]) / RM_HEIGHT
    else:
        xpos = (xpos * dims["x"]) / RM_WIDTH
        ypos = (1 / ratio) * (ypos * dims["y"]) / RM_HEIGHT

    return xpos, ypos


def update_stroke_dict(st, tool, tool_meta):
    st[tool] = {}
    st[tool]["tool"] = tool_meta
    st[tool]["segments"] = {}
    return st


def update_segment_dict(sg, seg_name, opacity, stroke_width):
    sg[seg_name] = {}
    sg[seg_name]["style"] = {}
    sg[seg_name]["style"]["opacity"] = f"{opacity:.3f}"
    sg[seg_name]["style"]["stroke-width"] = f"{stroke_width:.3f}"
    sg[seg_name]["points"] = []
    return sg


def split_ann_types(output):
    highlights = {}
    highlights["layers"] = []

    scribbles = {}
    scribbles["layers"] = []

    for layer in output["layers"]:
        for st_name, st_value in layer["strokes"].items():
            strokes = {"strokes": {st_name: st_value}}

            if "Highlighter" in st_name:
                highlights["layers"].append(strokes)
            else:
                scribbles["layers"].append(strokes)

    return highlights, scribbles


def parse_rm_file(file_path, dims={"x": RM_WIDTH, "y": RM_HEIGHT}):
    with open(file_path, "rb") as f:
        data = f.read()

    expected_header_v3 = b"reMarkable .lines file, version=3          "
    expected_header_v5 = b"reMarkable .lines file, version=5          "
    if len(data) < len(expected_header_v5) + 4:
        raise ValueError(f"{file_path} is too short to be a valid .rm file")

    offset = 0
    fmt = f"<{len(expected_header_v5)}sI"

    header, nlayers = struct.unpack_from(fmt, data, offset)
    offset += struct.calcsize(fmt)

    is_v3 = header == expected_header_v3
    is_v5 = header == expected_header_v5

    if (not is_v3 and not is_v5) or nlayers < 1:
        raise ValueError(
            f"{file_path} is not a valid .rm file: <header={header}><nlayers={nlayers}>"
        )

    output = {}
    output["layers"] = []

    for layer in range(nlayers):
        fmt = "<I"
        (nstrokes,) = struct.unpack_from(fmt, data, offset)
        offset += struct.calcsize(fmt)

        l = {}
        l["strokes"] = {}

        for stroke in range(nstrokes):
            if is_v3:
                fmt = "<IIIfI"
                # cc for color-code, w for stroke-width
                pen, cc, i_unk, w, nsegs = struct.unpack_from(fmt, data, offset)
                offset += struct.calcsize(fmt)
            if is_v5:
                fmt = "<IIIffI"
                pen, cc, i_unk, w, unk, nsegs = struct.unpack_from(fmt, data, offset)
                offset += struct.calcsize(fmt)

            opc = 1  # opacity
            last_x = -1.0
            last_y = -1.0

            tool, tool_meta, stroke_width, opacity = process_tool_meta(
                pen, dims, w, opc, cc
            )

            seg_name = "default"

            if tool not in l["strokes"].keys():
                l["strokes"] = update_stroke_dict(l["strokes"], tool, tool_meta)

                l["strokes"][tool]["segments"] = update_segment_dict(
                    l["strokes"][tool]["segments"], seg_name, opacity, stroke_width
                )

            p = []

            for segment in range(nsegs):
                fmt = "<ffffff"
                xpos, ypos, pressure, tilt, i_unk2, _ = struct.unpack_from(
                    fmt, data, offset
                )
                offset += struct.calcsize(fmt)

                xpos, ypos = adjust_xypos_sizes(xpos, ypos, dims)
                # print(f"segment: {segment} | xpos: {xpos} | ypos: {ypos}")

                if pen == 0:  # "Brush"
                    if 0 == segment % 8:
                        l["strokes"][tool]["segments"][seg_name]["points"].append(p)

                        seg_width = (
                            (5.0 * tilt)
                            * (6.0 * stroke_width - 10)
                            * (1 + 2.0 * pressure * pressure * pressure)
                        )
                        seg_name = f"tilt+press_{seg_width:.3f}_{opacity:.3f}"

                        if seg_name not in l["strokes"][tool]["segments"].keys():
                            l["strokes"][tool]["segments"] = update_segment_dict(
                                l["strokes"][tool]["segments"],
                                seg_name,
                                opacity,
                                seg_opacity,
                            )

                        p = []

                        if last_x != -1.0:
                            p.append((f"{last_x:.3f}", f"{last_y:.3f}"))

                        last_x = xpos
                        last_y = ypos

                elif pen == 1:  # "Tilt Pencil"
                    if 0 == segment % 8:
                        l["strokes"][tool]["segments"][seg_name]["points"].append(p)

                        seg_width = (10.0 * tilt - 2) * (8.0 * stroke_width - 14)
                        seg_opacity = (pressure - 0.2) * (pressure - 0.2)
                        seg_name = f"tilt+press_{seg_width:.3f}_{seg_opacity:.3f}"

                        if seg_name not in l["strokes"][tool]["segments"].keys():
                            l["strokes"][tool]["segments"] = update_segment_dict(
                                l["strokes"][tool]["segments"],
                                seg_name,
                                seg_opacity,
                                seg_opacity,
                            )

                        p = []

                        if last_x != -1.0:
                            p.append((f"{last_x:.3f}", f"{last_y:.3f}"))

                        last_x = xpos
                        last_y = ypos

                p.append((f"{xpos:.3f}", f"{ypos:.3f}"))

            l["strokes"][tool]["segments"][seg_name]["points"].append(p)

        output["layers"].append(l)

    # quick and dirty workaround to split highlights and scribbles
    # TODO: refactor!
    highlights, scribbles = split_ann_types(output)

    return highlights, scribbles


# TODO: make the rescale part of the parsing (or perhaps drawing?) process
def rescale_parsed_data(parsed_data, scale):
    if scale == 1:
        return parsed_data

    for strokes in parsed_data["layers"]:
        for _, st_value in strokes["strokes"].items():
            for _, sg_value in st_value["segments"].items():

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


def get_ann_max_bound(parsed_data):
    # https://shapely.readthedocs.io/en/stable/manual.html#LineString
    # https://shapely.readthedocs.io/en/stable/manual.html#MultiLineString
    # https://shapely.readthedocs.io/en/stable/manual.html#object.bounds

    collection = []

    for strokes in parsed_data["layers"]:
        for _, st_value in strokes["strokes"].items():
            for _, sg_value in st_value["segments"].items():
                for points in sg_value["points"]:
                    line = geom.LineString(
                        [(float(p[0]), float(p[1])) for p in points]
                    )
                    collection.append(line)

    (minx, miny, maxx, maxy) = geom.MultiLineString(collection).bounds

    return (maxx, maxy)
