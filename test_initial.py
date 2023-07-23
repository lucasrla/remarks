import os
import tempfile

import pytest
from syrupy.extensions.single_file import SingleFileSnapshotExtension

import remarks


class JPEGImageExtension(SingleFileSnapshotExtension):
    _file_extension = "jpg"


@pytest.fixture
def snapshot(snapshot):
    return snapshot.use_extension(JPEGImageExtension)


default_args = {
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


def snapshot_test_pdf(filename: str, snapshot):
    """Snapshots a pdf by converting all pages to jpeg images and collecting their hashes.
       Makes a snapshot for each page"""
    assert os.path.isfile(f"tests/out/{filename}")
    with tempfile.TemporaryDirectory() as tempDir:
        os.system(f'convert -density 150 "tests/out/{filename}" -quality 100 {tempDir}/output-%3d.jpg')
        page_images = os.listdir(tempDir)
        for i, image in enumerate(page_images):
            name = f"{filename}:page-{i}"
            with open(f"{tempDir}/{image}", "rb") as f:
                assert f.read() == snapshot(name=name)


def test_pdf_with_inserted_pages(snapshot):
    remarks.run_remarks("tests/in/pdf_with_multiple_added_pages", "tests/out", **default_args)
    snapshot_test_pdf("pdf_longer _remarks.pdf", snapshot)


def test_can_process_demo_with_default_args():
    remarks.run_remarks("demo/on-computable-numbers/xochitl", "tests/out", **default_args)

    assert os.path.isfile(
        "tests/out/1936 On Computable Numbers, with an Application to the Entscheidungsproblem - A. M. Turing _remarks.pdf")
    assert os.path.isfile(
        "tests/out/1936 On Computable Numbers, with an Application to the Entscheidungsproblem - A. M. Turing _highlights.md")


def test_can_handle_drawing_with_many_scribbles():
    remarks.run_remarks("tests/in/v2_notebook_complex", "tests/out", **default_args)

    assert os.path.isfile("tests/out/Gosper _remarks.pdf")


def test_can_handle_book():
    remarks.run_remarks("tests/in/v2_book_with_ann", "tests/out", **default_args)

    assert os.path.isfile("tests/out/Gosper _remarks.pdf")
