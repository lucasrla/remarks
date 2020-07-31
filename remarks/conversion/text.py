from itertools import groupby

import fitz


def extract_highlighted_text(page):
    highlight_rects = []

    # https://pymupdf.readthedocs.io/en/latest/page.html#Page.annots
    # https://pymupdf.readthedocs.io/en/latest/vars.html#annotation-related-constants
    for ann in page.annots(types=(fitz.PDF_ANNOT_HIGHLIGHT,)):
        highlight_rects.append(ann.rect)

    # main refs:
    # - https://pymupdf.readthedocs.io/en/latest/app2.html Appendix 2: Details on Text Extraction
    # - https://pymupdf.readthedocs.io/en/latest/faq.html#how-to-extract-text-from-within-a-rectangle
    # - https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/examples/textboxtract.py

    # see also:
    # - https://github.com/benlongo/remarkable-highlights/blob/master/remarkable_highlights/extract.py#L131

    words = page.getText("words")  # list of words on page
    words.sort(key=lambda w: (w[3], w[0]))  # ascending y, then x coordinate
    # print(words)

    highlighted_groups = []

    for rect in highlight_rects:
        highlighted_words = [w for w in words if fitz.Rect(w[:4]).intersects(rect)]
        # print("highlighted_words", highlighted_words)

        same_y1_group = groupby(highlighted_words, key=lambda w: w[3])

        for y1, gwords in same_y1_group:
            for w in gwords:
                # a very naive handling of an edge case
                for c in w[4]:
                    if b"\xef\xbf\xbd" == c.encode("utf-8"):  # �
                        # a few references that might be of interest:
                        # - https://github.com/pymupdf/PyMuPDF/issues/567 No text extractable from scanned pages
                        # - https://github.com/pymupdf/PyMuPDF/issues/112 Is there any way to determine if a pdf is scanned has obfuscated fonts
                        # - https://github.com/pymupdf/PyMuPDF/issues/365 Extracted text shows unicode character 65533
                        # - https://github.com/pymupdf/PyMuPDF/issues/530 Editing CMap / ToUnicode to achieve correct character mapping when extracting text
                        # - https://github.com/pymupdf/PyMuPDF/issues/398 Looking for font supporting Nepali
                        # - https://github.com/pymupdf/PyMuPDF/issues/413 Unicode Normalization with word extraction?
                        # you can also search for newer issues at https://github.com/pymupdf/PyMuPDF/search
                        raise ValueError(
                            f"Found an unmapped character: �. Something might be off with a PDF font. Fonts used in this page are: {page.getFontList(full=True)}"
                        )

            highlighted_groups.append(" ".join(w[4] for w in gwords))

    # print(highlighted_groups)

    return highlighted_groups


def create_paragraph_md(page, highlighted_groups):
    blocks = page.getText("blocks")
    # print(blocks)
    txt_blocks = [b[4] for b in blocks]

    # TODO: for malformed PDFs, it may be necessary to use script showed in the link below
    # https://pymupdf.readthedocs.io/en/latest/faq.html#how-to-extract-text-in-natural-reading-order

    out_blocks = []

    # loops with the simplest logic ever!
    for txt_block in txt_blocks:
        block = txt_block
        append = False

        for group in highlighted_groups:
            if group in block:
                block = block.replace(group, f"<mark>{group}</mark>")
                append = True

        if append:
            # dirty fix for joining marks in consecutive lines
            block = block.replace("</mark>\n<mark>", " ")
            out_blocks.append(block)

    return "\n\n".join(out_blocks)
