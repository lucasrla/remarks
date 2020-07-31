import pathlib
import argparse

from remarks import run_remarks

__prog_name__ = "remarks"
__version__ = "0.1.0"


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
        "--include-only",
        help="Include only PDFs files whose original names (visibleName) contain string pattern",
        metavar="STRING_PATTERN",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        help="Target file formats. Choose at least one of: pdf png md svg. Defaults to: png md",
        default=["md", "png"],
        metavar="FILE_FORMAT",
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

