from .parsing import (
    parse_rm_file,
    get_page_to_device_ratio,
    get_adjusted_page_dims,
    get_rescaled_device_dims,
    rescale_parsed_data,
    get_ann_max_bound,
)

from .drawing import (
    # draw_svg,
    draw_annotations,
    add_smart_highlight_annotations,
)

from .text import (
    check_if_text_extractable,
    create_md_from_word_blocks,
    extract_text_from_smart_highlights,
)

from .ocrmypdf import is_tool, run_ocr
