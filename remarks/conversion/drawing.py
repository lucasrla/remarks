from .parsing import RM_WIDTH, RM_HEIGHT

import fitz  # PyMuPDF
import shapely.geometry as geom  # Shapely

GRAYSCALE = {0: "black", 1: "grey", 2: "white"}
COLOR = {0: "blue", 1: "red", 2: "white", 3: "yellow"}


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

            output += "</g>"  # close stroke

        output += "</g>"  # close layer

    # overlay it with a clickable rect for flipping pages
    output += (
        f'<rect x="0" y="0" width="{dims["x"]}" height="{dims["y"]}" fill-opacity="0"/>'
    )

    output += "</svg>"

    return output


def prepare_segments(data, color=True):
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

                for segment in sg_content["points"]:
                    points = []
                    for p in segment:
                        points.append((float(p[0]), float(p[1])))
                    segs[name]["points"].append(points)

    return segs


def draw_pdf(data, page, color=True):
    c = COLOR if color else GRAYSCALE

    segments = prepare_segments(data)

    for seg_name, seg_data in segments.items():
        for seg in seg_data["points"]:
            line = geom.LineString(seg)
            # print(seg)
            # print(line.bounds, line.length, line.area)

            seg_rect = fitz.Rect(*line.bounds)
            seg_type = seg_name.split("_")[0]

            if seg_type == "Highlighter":
                annot = page.addHighlightAnnot(seg_rect)

                # TODO: setOpacity and setBorder don't seem to have any effect on HighlightAnnot
                # maybe an issue related to https://github.com/pymupdf/PyMuPDF/issues/421
                annot.setOpacity(seg_data["opacity"])
                annot.setBorder(width=seg_data["stroke-width"])
                annot.update()

            else:  # some kind of Scribble
                color_array = fitz.utils.getColor(c[seg_data["color-code"]])

                # Inspired by https://github.com/pymupdf/PyMuPDF/blob/master/docs/faq.rst#how-to-use-ink-annotations
                annot = page.addInkAnnot([seg])
                annot.setBorder(width=seg_data["stroke-width"])
                annot.setOpacity(seg_data["opacity"])
                annot.setColors(stroke=color_array)
                annot.update()

    return page
