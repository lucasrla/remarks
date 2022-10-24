from .parsing import (
    parse_rm_file,
    rescale_parsed_data,
    get_ann_max_bound,
)

from .drawing import (
    draw_annotations_on_pdf,
    add_smart_highlight_annotations,
)

from .text import (
    check_if_text_extractable,
    extract_groups_from_pdf_ann_hl,
    extract_groups_from_smart_hl,
    prepare_md_from_hl_groups,
)

from .ocrmypdf import is_executable_available, run_ocr
