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
        help="Base directory for exported (.pdf, .png, .md, and/or .svg) files",
        metavar="OUTPUT_DIRECTORY",
    )
    parser.add_argument(
        "--targets",
        nargs="+",
        help="Target file formats. Choose at least one of: pdf png md svg. Defaults to exporting all of them",
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

    if not pathlib.Path(args.input_dir).exists():
        parser.error(f'Directory "{args.input_dir}" does not exist.')

    if not pathlib.Path(args.output_dir).is_dir():
        pathlib.Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    if args.targets:
        run_remarks(args.input_dir, args.output_dir, targets=args.targets)
    else:
        run_remarks(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()

