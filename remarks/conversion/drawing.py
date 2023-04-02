import logging

import fitz  # PyMuPDF
import shapely.geometry as geom  # Shapely

from ..utils import (
    RM_WIDTH,
    RM_HEIGHT,
)


HL_COLOR_CODES = {
    3: "yellow",
    4: "green",
    5: "magenta",
    8: "gray",
}

SC_COLOR_CODES = {
    0: "black",
    1: "gray",
    2: "white",
    6: "blue",
    7: "red",
}


def draw_svg(data, dims={"x": RM_WIDTH, "y": RM_HEIGHT}):
    stroke_color = SC_COLOR_CODES

    output = f'<svg xmlns="http://www.w3.org/2000/svg" width="{dims["x"]}" height="{dims["y"]}">'

    output += """
        <script type="application/ecmascript"> <![CDATA[
            var visiblePage = 'p1';
            function goToPage(page) {
                document.getElementById(visiblePage).setAttribute('style', 'display: none');
                document.getElementById(page).setAttribute('style', 'display: inline');
                visiblePage = page;
            }
        ]]> </script>
    """

    for i, layer in enumerate(data["layers"]):
        output += f'<g id="layer-{i}" style="display:inline">'

        for st_name, st_content in layer["strokes"].items():
            output += f'<g id="stroke-{st_name}" style="display:inline">'
            st_color = stroke_color[st_content["tool"]["color-code"]]

            for sg_name, sg_content in st_content["segments"].items():
                sg_width = sg_content["style"]["stroke-width"]
                sg_opacity = sg_content["style"]["opacity"]

                for segment in sg_content["points"]:
                    output += f'<polyline style="fill:none;stroke:{st_color};stroke-width:{sg_width};opacity:{sg_opacity}" points="'

                    for point in segment:
                        output += f"{point[0]},{point[1]} "

                    output += '" />\n'

            output += "</g>"  # Close stroke

        output += "</g>"  # Close layer

    # Overlay it with a clickable rect for flipping pages
    output += (
        f'<rect x="0" y="0" width="{dims["x"]}" height="{dims["y"]}" fill-opacity="0"/>'
    )

    output += "</svg>"

    return output


def prepare_segments(data):
    segs = {}

    for layer in data["layers"]:
        for st_name, st_content in layer["strokes"].items():
            for i, sg_content in enumerate(st_content["segments"]):
                name = f"{st_name}_{i}"
                segs[name] = {}

                segs[name]["stroke-width"] = float(sg_content["style"]["stroke-width"])

                segs[name]["opacity"] = float(sg_content["style"]["opacity"])
                segs[name]["color-code"] = sg_content["style"]["color-code"]

                segs[name]["points"] = []
                segs[name]["lines"] = []
                segs[name]["rects"] = []

                for segment in sg_content["points"]:
                    points = []
                    if len(segment) <= 1:
                        # line needs at least two points, see testcase v2_notebook_complex
                        continue
                    for p in segment:
                        points.append((float(p[0]), float(p[1])))

                    segs[name]["points"].append(points)
                    line = geom.LineString(points)
                    segs[name]["lines"].append(line)

                    if line.length > 0.0:
                        segs[name]["rects"].append(fitz.Rect(*line.bounds))

    return segs


def draw_annotations_on_pdf(data, page, inplace=False):
    segments = prepare_segments(data)

    for seg_name, seg_data in segments.items():
        seg_type = seg_name.split("_")[0]

        # Highlights that were not recognized by reMarkable's own software,
        # these ones are "old style" and we must handle them ourselves

        # By "old style" I mean before Software releases 2.7 and 2.11
        # - https://support.remarkable.com/s/article/Software-release-2-7
        # - https://support.remarkable.com/s/article/Software-release-2-11

        if seg_type == "Highlighter":
            # print("seg_data:", seg_data)

            # If there are multiple rectangles per segment, do not want to
            # loop over them. Instead, just send them all to addHighlightAnnot.
            # It can handle a list of rectangles and will join them into one
            # annotation.

            # Sometimes small highlights will not be valid. If so, just print
            # a warning and carry on
            try:
                # https://pymupdf.readthedocs.io/en/latest/recipes-annotations.html#how-to-add-and-modify-annotations
                annot = page.add_highlight_annot(seg_data["rects"])

                # Now supporting colors
                try:
                    color_array = fitz.utils.getColor(
                        HL_COLOR_CODES[seg_data["color-code"]]
                    )
                except KeyError:
                    # Defaults to yellow if color hasn't been defined yet
                    color_array = fitz.utils.getColor("yellow")

                annot.set_colors(stroke=color_array)

                annot.set_opacity(seg_data["opacity"])
                annot.set_border(width=seg_data["stroke-width"])
                annot.update()

                # print("annot.rect:", annot.rect)
                # print("annot.border:", annot.border)
                # print("annot.opacity:", annot.opacity)
                # print("annot.colors:", annot.colors)

            except Exception as e:
                logging.warning(
                    f"- Just ran into an exception while adding a highlight. It probably happened because of a small highlight that PyMuPDF couldn't handle well enough: {e}"
                )

        # Scribbles
        else:
            if seg_data == "Eraser":
                # Overwrite eraser color to always be white.
                seg_data['color-code'] = 2
            for seg_points in seg_data["points"]:
                # https://pymupdf.readthedocs.io/en/latest/recipes-annotations.html#how-to-use-ink-annotations
                annot = page.add_ink_annot([seg_points])
                annot.set_border(width=seg_data["stroke-width"])
                annot.set_opacity(seg_data["opacity"])

                color_array = fitz.utils.getColor(
                    SC_COLOR_CODES[seg_data["color-code"]]
                )
                annot.set_colors(stroke=color_array)

                annot.update()

    if not inplace:
        return page


# Highlights from reMarkable's own "smart" highlighting (introduced in 2.7)
def add_smart_highlight_annotations(hl_data, page, scale, inplace=False):
    hl_list = hl_data["highlights"][0]

    for hl in hl_list:
        # print("hl=", hl)
        # print("hl[text]:", hl["text"])

        quads = page.search_for(hl["text"], quads=True)
        # print("len(quads)=", len(quads), "len(hl[rects])=", len(hl["rects"]))

        # Allowing for some padding around the hl["rects"]
        padding = 2

        # If page.search_for finds too many occurences of hl["text"]
        #
        # This often happens when hl["text"] is a very short string (e.g. "re")
        # - https://github.com/lucasrla/remarks/issues/57
        if len(quads) > len(hl["rects"]):
            logging.debug(
                "- Found several occurences of highlighted text on the same page. Will restrict search to their clip area"
            )

            points = []
            for r in hl["rects"]:
                points.append((r["x"] - padding, r["y"] - padding))
                points.append((r["x"] + r["width"] + padding, r["y"] - padding))
                points.append((r["x"] - padding, r["y"] + r["height"] + padding))
                points.append(
                    (
                        r["x"] + r["width"] + padding,
                        r["y"] + r["height"] + padding,
                    )
                )

            envelope = geom.MultiPoint(points).bounds
            # `bounds` returns minimum bounding region (minx, miny, maxx, maxy)

            scaled_envelope = [float(coord) * scale for coord in envelope]
            # print("scaled_envelope", scaled_envelope)

            quads = page.search_for(
                hl["text"], quads=True, clip=fitz.Rect(scaled_envelope)
            )
            # print("quads", quads)

        # If page.search_for cannot find hl["text"] in the PDF page
        # This fix was inspired by @danieluhricek posts at
        # - https://github.com/lucasrla/remarks/issues/52
        if not quads:
            logging.debug(
                "- Couldn't get the highlighted text on the PDF. Will annotate based on their rects"
            )

            quads = [
                fitz.Rect(
                    (rect["x"] - padding) * scale,
                    (rect["y"] - padding) * scale,
                    (rect["x"] + rect["width"] + padding) * scale,
                    (rect["y"] + rect["height"] + padding) * scale,
                )
                for rect in hl["rects"]
            ]

            # print("quads", quads)

        annot = page.add_highlight_annot(quads)

        # Support to colors
        try:
            color_array = fitz.utils.getColor(HL_COLOR_CODES[hl["color"]])
        except KeyError:
            # Defaults to yellow if color hasn't been defined yet
            color_array = fitz.utils.getColor("yellow")

        annot.set_colors(stroke=color_array)

        annot.update()

    if not inplace:
        return page
