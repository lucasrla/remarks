from itertools import groupby

import fitz


def get_highlight_rects(page):
    highlight_rects = []

    # https://pymupdf.readthedocs.io/en/latest/page.html#Page.annots
    # https://pymupdf.readthedocs.io/en/latest/vars.html#annotation-related-constants
    for ann in page.annots(types=(fitz.PDF_ANNOT_HIGHLIGHT,)):
        highlight_rects.append(ann.rect)

    return highlight_rects


def get_page_words(page, flags=(1 + 2 + 8), sort=True):
    # https://pymupdf.readthedocs.io/en/latest/app2.html#text-extraction-flags-defaults
    # https://github.com/pymupdf/PyMuPDF/issues/363
    words = page.getText("words", flags=flags)

    if sort:
        words.sort(key=lambda w: (w[3], w[0]))  # ascending y, then x coordinate
    # print(words)

    return words


def get_page_blocks(page, flags=(1 + 2 + 8)):
    blocks = page.getText("blocks", flags=flags)

    # print(blocks)
    txt_blocks = [b[4] for b in blocks]

    return txt_blocks


def is_text_extractable(page, assume_wellformed=False):
    # TODO: improve this check, it is still very rudimentary

    text_encoded = page.getText("text").encode("utf-8")
    # print(text_encoded)

    if len(text_encoded) == 0:  # empty, likely a scanned page
        return False

    # a few references that might be of interest:
    # - https://github.com/pymupdf/PyMuPDF/issues/567 No text extractable from scanned pages
    # - https://github.com/pymupdf/PyMuPDF/issues/112 Is there any way to determine if a pdf is scanned has obfuscated fonts
    # - https://github.com/pymupdf/PyMuPDF/issues/365 Extracted text shows unicode character 65533
    # - https://github.com/pymupdf/PyMuPDF/issues/530 Editing CMap / ToUnicode to achieve correct character mapping when extracting text
    # - https://github.com/pymupdf/PyMuPDF/issues/398 Looking for font supporting Nepali
    # - https://github.com/pymupdf/PyMuPDF/issues/413 Unicode Normalization with word extraction?
    # you can also search for newer issues at https://github.com/pymupdf/PyMuPDF/search

    # see also: https://pymupdf.readthedocs.io/en/latest/faq.html#how-to-analyze-font-characteristics

    # TODO: maybe reconstruct the CMap that is missing?
    # https://github.com/adobe-type-tools/cmap-resources/blob/master/Adobe-Identity-0/CMap/Identity-H
    # https://github.com/adobe-type-tools/perl-scripts/blob/master/cmap-tool.pl

    # b"\xef\xbf\xbd" maps to �
    # it may happen in a page with an obsfucated font
    # but it seems it might also appear due to perfectly fine LateX equations
    # see: https://github.com/lucasrla/remarks/pull/19
    
    if b"\xef\xbf\xbd" in text_encoded and not assume_wellformed:
        return False
        # raise ValueError(f"Found an unmapped character: �. Something might be off with a PDF font. Check out `page.getFontList(full=True)`")

    return True


def extract_highlighted_words_nosort(page):
    '''
    Modified version of extract_highlighted_words, but without sorting text by
    physical coordinates.
    '''
    words = get_page_words(page, flags=(2), sort=False)
    highlight_rects = get_highlight_rects(page)

    # Create a boolean mask for each extracted word, depending on whether it
    # was highlighted.
    highlight_mask = [any([fitz.Rect(w[:4]).intersects(rect)
                           for rect in highlight_rects])
                      for w in words]

    # Each group of consecutively highlighted words will be joined.
    new_group = True
    current_group = []
    highlighted_groups = []
    for word, highlighted in zip(words, highlight_mask):
        if highlighted:
            current_group.append(word[4])
            new_group = False
        else:
            if len(current_group) > 0:
                highlighted_groups.append(current_group)
                current_group = []
            new_group = True
    # Append group if it is at the end of the page
    if len(current_group) > 0:
        highlighted_groups.append(current_group)

    highlighted_groups = ['- ' + ' '.join(g) for g in highlighted_groups]

    return '\n'.join(highlighted_groups)


def extract_highlighted_words(page):
    # main refs:
    # - https://pymupdf.readthedocs.io/en/latest/app2.html Appendix 2: Details on Text Extraction
    # - https://pymupdf.readthedocs.io/en/latest/faq.html#how-to-extract-text-from-within-a-rectangle
    # - https://github.com/pymupdf/PyMuPDF-Utilities/blob/master/examples/textboxtract.py

    # see also:
    # - https://github.com/benlongo/remarkable-highlights/blob/master/remarkable_highlights/extract.py#L131

    words = get_page_words(page)
    highlight_rects = get_highlight_rects(page)

    highlighted_groups = []

    for rect in highlight_rects:
        highlighted_words = [w for w in words if fitz.Rect(w[:4]).intersects(rect)]
        # print("highlighted_words", highlighted_words)

        same_y1_group = groupby(highlighted_words, key=lambda w: w[3])

        for y1, gwords in same_y1_group:
            highlighted_groups.append(" ".join(w[4] for w in gwords))

    # print("highlighted_groups", highlighted_groups)

    return highlighted_groups


def md_from_blocks(page):
    highlighted_groups = extract_highlighted_words(page)

    if len(highlighted_groups) == 0:
        return ""

    txt_blocks = get_page_blocks(page)
    # print("txt_blocks", txt_blocks)

    # TODO: for malformed PDFs it might be necessary to use the script below
    # https://pymupdf.readthedocs.io/en/latest/faq.html#how-to-extract-text-in-natural-reading-order

    out_blocks = []

    # Loops with the simplest logic ever!
    for txt_block in txt_blocks:

        # Getting rid of \n \t double/triple/multiple spaces inside a block
        # https://stackoverflow.com/questions/1546226/is-there-a-simple-way-to-remove-multiple-spaces-in-a-string
        block = " ".join(txt_block.split())

        append = False

        for group in highlighted_groups:
            if group in block:
                block = block.replace(group, f"<mark>{group}</mark>")
                append = True

        if append:
            # dirty fix for joining consecutive marks
            block = block.replace("</mark>\n<mark>", " ").replace("</mark> <mark>", " ")
            out_blocks.append(block)

    # print("out_blocks", out_blocks)

    return "\n\n".join(out_blocks)
