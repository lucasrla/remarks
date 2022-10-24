from itertools import groupby
import operator

import fitz


# TODO: improve this check, it is still very rudimentary
def check_if_text_extractable(page, malformed=False):
    text_encoded = page.get_text("text").encode("utf-8")
    # print(text_encoded)

    if len(text_encoded) == 0:  # empty, likely a scanned page
        return False

    # A few references that might be of interest:
    # - https://github.com/pymupdf/PyMuPDF/issues/567
    # No text extractable from scanned pages
    # - https://github.com/pymupdf/PyMuPDF/issues/112
    # Is there any way to determine if a pdf is scanned has obfuscated fonts
    # - https://github.com/pymupdf/PyMuPDF/issues/365
    # Extracted text shows unicode character 65533
    # - https://github.com/pymupdf/PyMuPDF/issues/530
    # Editing CMap to achieve correct character mapping when extracting text
    # - https://github.com/pymupdf/PyMuPDF/issues/398
    # Looking for font supporting Nepali
    # - https://github.com/pymupdf/PyMuPDF/issues/413
    # Unicode Normalization with word extraction?
    #
    # Or search for newer issues at https://github.com/pymupdf/PyMuPDF/search

    # Also: https://pymupdf.readthedocs.io/en/latest/recipes-text.html#how-to-analyze-font-characteristics

    # TODO: maybe reconstruct the CMap that is missing?
    # https://github.com/adobe-type-tools/cmap-resources/blob/master/Adobe-Identity-0/CMap/Identity-H
    # https://github.com/adobe-type-tools/perl-scripts/blob/master/cmap-tool.pl

    # b"\xef\xbf\xbd" maps to �
    # It may happen in a page with an obsfucated font,
    # but it might also appear on perfectly fine LateX equations
    # See: https://github.com/lucasrla/remarks/pull/19

    if b"\xef\xbf\xbd" in text_encoded and malformed:
        return False
        # raise ValueError(
        #     f"Found an unmapped character: �. Something might be off with a PDF font. Check out `page.getFontList(full=True)`"
        # )

    return True


def get_highlight_rects(page, sort=True):
    hl_rects = []

    # https://pymupdf.readthedocs.io/en/latest/page.html#Page.annots
    # https://pymupdf.readthedocs.io/en/latest/vars.html#annotation-related-constants
    for ann in page.annots(types=(fitz.PDF_ANNOT_HIGHLIGHT,)):
        hl_rects.append(ann.rect)

    if sort:
        # Sort by y1 and then by x0
        hl_rects.sort(key=lambda r: (r[3], r[0]))

    return hl_rects


def get_page_text_tuples(
    page, option="words", flags=(1 + 2 + 16 + 64), sort=True, text_only=False
):
    # https://pymupdf.readthedocs.io/en/latest/app1.html#text-extraction-flags-defaults
    # https://pymupdf.readthedocs.io/en/latest/vars.html#textpreserve
    #
    # For "words":
    # fitz.TEXT_PRESERVE_LIGATURES == 1 | Default: ON
    # fitz.TEXT_PRESERVE_WHITESPACE == 2 | Default: ON
    # fitz.TEXT_PRESERVE_IMAGES == 4 | Default: OFF (not available!)
    # fitz.TEXT_INHIBIT_SPACES == 8 | Default: OFF
    # fitz.TEXT_DEHYPHENATE == 16 | Default: OFF (but I have turned it on)
    # fitz.TEXT_PRESERVE_SPANS == 32 | Default: OFF
    # fitz.TEXT_MEDIABOX_CLIP == 64 | Default: ON

    # sort=True and "words":
    # Sorts the output by vertical, then horizontal coordinates
    # That is, it sorts by (y1, x0) of the words’ bboxes
    # https://pymupdf.readthedocs.io/en/latest/page.html#Page.get_text

    # For "blocks" is basically the same!

    tuples_list = page.get_text(option, flags=flags, sort=sort)

    # https://pymupdf.readthedocs.io/en/latest/textpage.html#TextPage.extractWORDS
    # example of a word tuple:
    # `(x0, y0, x1, y1, "word", block_no, line_no, word_no)`

    # https://pymupdf.readthedocs.io/en/latest/textpage.html#TextPage.extractBLOCKS
    # example of a block tuple:
    # `(x0, y0, x1, y1, "lines in the block", block_no, block_type)`

    if text_only:
        return [item[4] for item in tuples_list]
    else:
        return tuples_list


def extract_groups_from_pdf_ann_hl(page, malformed=False):
    # https://pymupdf.readthedocs.io/en/latest/recipes-text.html#how-to-extract-text-from-within-a-rectangle
    # https://github.com/pymupdf/PyMuPDF-Utilities/tree/master/textbox-extraction
    # https://github.com/benlongo/remarkable-highlights/blob/0608dea6ba1f5ce46c540e623c55649f8f918b5c/remarkable_highlights/extract.py#L131

    # If PDF is well-formed, no need for sorted words
    is_sort_needed = malformed

    # Get all words (highlighted or not) from a PDF page
    words_tuples_list = get_page_text_tuples(page, sort=is_sort_needed)
    # print("words_tuples_list:", words_tuples_list)

    # Get all rectangles of highlight annotations that exist on PDF page
    hl_rects = get_highlight_rects(page)
    # print("hl_rects:", hl_rects)

    hl_word_groups = []

    # An alternative for the method below would be to use word numbers
    # and order words within each "block"

    # If "wellformed"
    if not malformed:
        # Create a boolean mask for each word, depending on whether it was
        # highlighted (or not)
        #
        # w[:4] for the bbbox coordinates of a word tuple: (x0, y0, x1, y1)
        hl_words_mask = [
            any([fitz.Rect(w[:4]).intersects(r) for r in hl_rects])
            for w in words_tuples_list
        ]

        # Join each sequence of consecutively highlighted words into a group
        curr_group = []
        for word_tuple, is_highlighted in zip(words_tuples_list, hl_words_mask):
            if is_highlighted:
                # w[4] for the actual text content of a word tuple
                curr_group.append(word_tuple[4])
            # If this word_tuple hasn't been highlighted, append current group
            # and create a new one
            else:
                if len(curr_group) > 0:
                    hl_word_groups.append(curr_group)
                    curr_group = []

        # Append a group at the end of the page if it's not empty
        if len(curr_group) > 0:
            hl_word_groups.append(curr_group)

    # print("hl_word_groups:", hl_word_groups)

    # If malformed
    else:
        # If PDF can't be taken as well-formed, infer which words are
        # consecutive by their y_1 coordinate. Note that this implies several
        # limitations. For instance: (1) we won't "merge" highlighted words
        # that are separated by line breaks; (2) we might "merge" words that
        # are in the same line but were highlighted separately
        hl_word_tuples = []
        for word_tuple in words_tuples_list:
            already_highlighted = False
            for hl_rect in hl_rects:
                if (
                    fitz.Rect(word_tuple[:4]).intersects(hl_rect)
                    and not already_highlighted
                ):
                    # print("hl_rect + word_tuple:", hl_rect, word_tuple)
                    hl_word_tuples.append(word_tuple)
                    already_highlighted = True

        # print("hl_word_tuples:", hl_word_tuples)

        # w[3] is the y1 coord (sort of a "base line") of a word's bbox
        hl_words_grouped_by_line = groupby(hl_word_tuples, key=lambda w: w[3])

        for y1, hl_word_tuple in hl_words_grouped_by_line:
            hl_word_groups.append([w[4] for w in hl_word_tuple])

    # print("hl_word_groups:", hl_word_groups)
    return hl_word_groups


def extract_groups_from_smart_hl(hl_data):
    hl_list = hl_data["highlights"][0]

    # Sorting is needed because highlights are added to list according to
    # "timestamp", not necessarily natural order
    sorted_hl_list = sorted(hl_list, key=operator.itemgetter("start"))

    # Create a new key for easier iteration over highlights.
    # `start` and `length` seem to be character-based counts
    for hl in sorted_hl_list:
        hl["end"] = hl["start"] + hl["length"]

    curr_group = []
    hl_word_groups = []

    for i, hl in enumerate(sorted_hl_list):
        curr_group.append(hl["text"])
        # print("curr_group:", curr_group)

        # Number of characters to act as a tolerance between groups
        gap = 2

        # This is not the last item
        if (i + 1) < len(sorted_hl_list):
            hl_next = sorted_hl_list[i + 1]

            # Is the next highlight fully "contained" within the current one?
            curr_contains_next = (
                hl["end"] > hl_next["start"] and hl["end"] > hl_next["end"]
            )

            # Start a new group to split highlights apart if either the
            # (current highlight + gap) ends before the next one OR the current
            # highlight fully contains the next one
            if hl["end"] + gap < hl_next["start"] or curr_contains_next:
                hl_word_groups.append(curr_group)
                curr_group = []
                # print("smart_hl_word_groups:", hl_word_groups)

        # For the last one
        else:
            hl_word_groups.append(curr_group)

    # print("smart_hl_word_groups:", hl_word_groups)
    return hl_word_groups


def prepare_md_from_hl_groups(
    page,
    ann_hl_groups,
    smart_hl_groups,
    presentation="whole_block",
):
    hl_word_groups = ann_hl_groups + smart_hl_groups
    # print("hl_word_groups", hl_word_groups)

    if presentation == "whole_block":
        # TODO: Should we avoid sorting here if PDF is well-formed? Need some
        # ugly documents to dig deeper and test this out...
        text_blocks_list = get_page_text_tuples(
            page, option="blocks", sort=True, text_only=True
        )
        # print("text_blocks_list:", text_blocks_list)

        md_blocks_with_marks = []
        already_matched = []

        for text_block in text_blocks_list:
            # Remove any \n \t double/triple/multiple spaces inside a block
            # https://stackoverflow.com/questions/1546226/is-there-a-simple-way-to-remove-multiple-spaces-in-a-string
            text_block_str = " ".join(text_block.split())
            # print(f"text_block_str: {text_block_str}")

            has_highlight = False
            md_str = text_block_str

            for hl_group in hl_word_groups:
                hl_group_str = " ".join(hl_group)
                # print(f"hl_group_str: {hl_group_str}")
                if hl_group_str in text_block_str and hl_group not in already_matched:
                    md_str = md_str.replace(
                        hl_group_str, f"<mark>{hl_group_str}</mark>"
                    )
                    has_highlight = True
                    already_matched.append(hl_group)

            # TODO: Are these quick fixes for consecutive mark still necessary?
            if has_highlight:
                md_str = md_str.replace("</mark>\n<mark>", " ")
                md_str = md_str.replace("</mark> <mark>", " ")
                md_blocks_with_marks.append(md_str)

        # In case any `hl_group_str` is not contained in any text_block_str,
        # something which actually happens -- PDFs are crazy things!
        if len(hl_word_groups) > len(already_matched):
            for hl_group in hl_word_groups:
                if hl_group not in already_matched:
                    hl_group_str = " ".join(hl_group)
                    md_str = f"<mark>{hl_group_str}</mark>"
                    md_blocks_with_marks.append(md_str)

        # print("md_blocks_with_marks:", md_blocks_with_marks)

        return "\n\n".join(md_blocks_with_marks)

    elif presentation == "bullet_points":
        hl_word_groups = ["- " + " ".join(group) for group in hl_word_groups]

        return "\n".join(hl_word_groups)

    else:
        raise ValueError(
            "Invalid formatting for Markdown. Check your `--hl_md_format` flag"
        )
