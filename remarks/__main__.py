import pathlib
import argparse

from remarks import run_remarks

__prog_name__ = "remarks"
__version__ = "0.1.1"


def main():
    parser = argparse.ArgumentParser(__prog_name__, add_help=False)

    parser.add_argument(
        "input_dir",
        help="xochitl-derived directory that contains *.pdf, *.content, *.metadata, and */*.rm files",
        metavar="INPUT_DIRECTORY",
    )
    parser.add_argument(
        "output_dir",
        help="Base directory for exported (*.pdf, *.png, *.md, and/or *.svg) files",
        metavar="OUTPUT_DIRECTORY",
    )
    parser.add_argument(
        "--pdf_name",
        help="Work only on PDF files whose original names (visibleName) contain this string",
        metavar="FILENAME_STRING",
    )
    parser.add_argument(
        "--ann_type",
        help="Parse only a specific type of annotation: highlights or scribbles (i.e. everything not highlighted)",
        metavar="ANNOTATION_TYPE",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        help="Target file formats. Choose at least one of the following extensions: pdf png md svg. Defaults to: png md",
        default=["md", "png"],
        metavar="FILE_EXTENSION",
    )
    parser.add_argument(
        "--combined_pdf",
        dest="combined_pdf",
        action="store_true",
        help="Create a '*_remarks.pdf' file with all annotated pages merged into the original (unannotated) PDF",
    )
    parser.add_argument(
        "--modified_pdf",
        dest="modified_pdf",
        action="store_true",
        help="Create a '*_remarks-only.pdf' file with all annotated pages",
    )
    parser.add_argument(
        "-f",
        "--assume_wellformed",
        dest="assume_wellformed",
        action="store_true",
        help="Assumes a well-formed PDF where words are in order."
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        help="Show version number",
        version="%(prog)s {version}".format(version=__version__),
    )
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message",
    )

    parser.set_defaults(combined_pdf=False, modified_pdf=False,
                        assume_wellformed=False)

    args = parser.parse_args()
    args_dict = vars(args)

    input_dir = args_dict.pop("input_dir")
    output_dir = args_dict.pop("output_dir")

    if not pathlib.Path(input_dir).exists():
        parser.error(f'Directory "{input_dir}" does not exist.')

    if not pathlib.Path(output_dir).is_dir():
        pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

    run_remarks(input_dir, output_dir, **args_dict)


if __name__ == "__main__":
    main()

