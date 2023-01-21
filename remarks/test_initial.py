import remarks
import os


def test_can_process_demo_with_default_args():
    initial_args = {
        'file_name': None,
        'ann_type': ['scribbles', 'highlights'],
        'combined_pdf': True,
        'combined_md': True,
        'modified_pdf': False,
        'md_hl_format': 'whole_block',
        'md_page_offset': 0,
        'md_header_format': 'atx',
        'per_page_targets': [],
        'assume_malformed_pdfs': False,
        'avoid_ocr': False
    }
    remarks.run_remarks("demo/on-computable-numbers/xochitl", "tests/out", **initial_args)

    assert os.path.isfile("tests/out/1936 On Computable Numbers, with an Application to the Entscheidungsproblem - A. "
                          "M _remarks.pdf")
    assert os.path.isfile("tests/out/1936 On Computable Numbers, with an Application to the Entscheidungsproblem - A. "
                          "M _highlights.md")


def test_can_handle_drawing_with_many_scribbles():
    initial_args = {
        'file_name': None,
        'ann_type': ['scribbles', 'highlights'],
        'combined_pdf': True,
        'combined_md': True,
        'modified_pdf': False,
        'md_hl_format': 'whole_block',
        'md_page_offset': 0,
        'md_header_format': 'atx',
        'per_page_targets': [],
        'assume_malformed_pdfs': False,
        'avoid_ocr': False
    }
    remarks.run_remarks("tests/in/v2_notebook_complex", "tests/out", **initial_args)

    assert os.path.isfile("tests/out/Gosper _remarks.pdf")


def test_can_handle_book():
    initial_args = {
        'file_name': None,
        'ann_type': ['scribbles', 'highlights'],
        'combined_pdf': True,
        'combined_md': True,
        'modified_pdf': False,
        'md_hl_format': 'whole_block',
        'md_page_offset': 0,
        'md_header_format': 'atx',
        'per_page_targets': [],
        'assume_malformed_pdfs': False,
        'avoid_ocr': False
    }
    remarks.run_remarks("tests/in/v2_book_with_ann", "tests/out", **initial_args)

    assert os.path.isfile("tests/out/Gosper _remarks.pdf")
