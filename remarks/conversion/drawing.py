import fitz  # PyMuPDF
import shapely.geometry as geom  # Shapely

from ..utils import (
    RM_WIDTH,
    RM_HEIGHT,
)


GRAYSCALE = {0: "black", 1: "grey", 2: "white"}
COLOR = {0: "blue", 1: "red", 2: "white", 3: "yellow", 6: "blue", 7: "red"}


def draw_svg(data, dims={"x": RM_WIDTH, "y": RM_HEIGHT}, color=True):
    stroke_color = COLOR if color else GRAYSCALE

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

            for sg_name, sg_content in st_content["segments"].items():
                name = f"{st_name}_{sg_name}"
                segs[name] = {}

                segs[name]["stroke-width"] = float(sg_content["style"]["stroke-width"])

                segs[name]["opacity"] = float(sg_content["style"]["opacity"])
                segs[name]["color-code"] = st_content["tool"]["color-code"]

                segs[name]["points"] = []
                segs[name]["lines"] = []
                segs[name]["rects"] = []

                for segment in sg_content["points"]:
                    points = []
                    for p in segment:
                        points.append((float(p[0]), float(p[1])))

                    segs[name]["points"].append(points)
                    line = geom.LineString(points)
                    segs[name]["lines"].append(line)

                    if line.length > 0.0:
                        segs[name]["rects"].append(fitz.Rect(*line.bounds))

    return segs


def draw_annotations_on_pdf(data, page, color=True, inplace=False):
    c = COLOR if color else GRAYSCALE

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

            for seg_rect in seg_data["rects"]:
                # print("seg_rect:", seg_rect)

                # https://pymupdf.readthedocs.io/en/latest/recipes-annotations.html#how-to-add-and-modify-annotations
                # annot = page.add_highlight_annot(seg_rect)
                page.add_highlight_annot(seg_rect)
                # annot.update()

                # print("annot.rect:", annot.rect)
                # print("annot.border:", annot.border)
                # print("annot.opacity:", annot.opacity)
                # print("annot.colors:", annot.colors)

        # Scribbles
        else:
            for seg_points in seg_data["points"]:
                color_array = fitz.utils.getColor(c[seg_data["color-code"]])

                # Inspired by https://pymupdf.readthedocs.io/en/latest/recipes-annotations.html#how-to-use-ink-annotations
                annot = page.add_ink_annot([seg_points])
                annot.set_border(width=seg_data["stroke-width"])
                annot.set_opacity(seg_data["opacity"])
                annot.set_colors(stroke=color_array)
                annot.update()

    if not inplace:
        return page


# Highlights from reMarkable's own "smart" highlighting (introduced in 2.7)
def add_smart_highlight_annotations(hl_data, page, inplace=False):
    hl_list = hl_data["highlights"][0]

    for hl in hl_list:
        # https://pymupdf.readthedocs.io/en/latest/page.html#Page.add_highlight_annot
        quads = page.search_for(hl["text"], quads=True)
        page.add_highlight_annot(quads)

    if not inplace:
        return page
