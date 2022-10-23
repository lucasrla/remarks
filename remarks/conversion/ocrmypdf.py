import logging
import subprocess

# TODO: evaluate using the python API (instead of cli)
# https://github.com/jbarlow83/OCRmyPDF/blob/master/src/ocrmypdf/api.py
# https://ocrmypdf.readthedocs.io/en/latest/api.html

# https://stackoverflow.com/questions/11210104/check-if-a-program-exists-from-a-python-script


def is_executable_available(name):
    """Check whether `name` is on PATH and marked as executable."""

    # from whichcraft import which
    from shutil import which

    return which(name) is not None


def run_ocr(tmp_file_name, languages="eng"):
    cmd_args = []

    # TODO: use parallel for batch processing?
    # https://ocrmypdf.readthedocs.io/en/latest/batch.html

    cmd_args += ("ocrmypdf", tmp_file_name, tmp_file_name)  # modify in place

    # cmd_args += ("--pages", str(page_number))
    # cmd_args += ("--sidecar", sidecar_file)
    # ERROR: --pages and --sidecar are mutually exclusive

    cmd_args += ("--force-ocr",)

    if languages:
        cmd_args += ("-l", languages)

    # print(cmd_args)

    p = subprocess.run(
        cmd_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    logging.debug(f"{p.stdout}\n")

    return tmp_file_name
