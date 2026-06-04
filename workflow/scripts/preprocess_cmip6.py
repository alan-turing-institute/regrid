import argparse

import _bootstrap  # noqa: F401  # pylint: disable=unused-import

from workflow.lib.io import load_config
from workflow.lib.manifest import write_manifest
from workflow.lib.processing import interpolate_levels, regrid_dataset, subset_variable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compatibility wrapper around the single-purpose preprocessing scripts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subset = subparsers.add_parser("subset-variable")
    subset.add_argument("--config", required=True)
    subset.add_argument("--kind", choices=("surface", "atmos"), required=True)
    subset.add_argument("--variable", required=True)
    subset.add_argument("--window-start")
    subset.add_argument("--window-end")
    subset.add_argument("--include-window-end", default="true")
    subset.add_argument("--output", required=True)

    interp = subparsers.add_parser("interpolate-levels")
    interp.add_argument("--config", required=True)
    interp.add_argument("--input", required=True)
    interp.add_argument("--output", required=True)

    regrid = subparsers.add_parser("regrid")
    regrid.add_argument("--config", required=True)
    regrid.add_argument("--kind", choices=("surface", "atmos"), required=True)
    regrid.add_argument("--variable")
    regrid.add_argument("--input", required=True)
    regrid.add_argument("--output", required=True)

    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("--config", required=True)
    manifest.add_argument("--surface", nargs="+", required=True)
    manifest.add_argument("--atmos", nargs="+", required=True)
    manifest.add_argument("--time-start")
    manifest.add_argument("--time-end")
    manifest.add_argument("--time-window")
    manifest.add_argument("--output", required=True)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    if args.command == "subset-variable":
        subset_variable(
            config,
            kind=args.kind,
            variable=args.variable,
            window_start=args.window_start,
            window_end=args.window_end,
            include_window_end=args.include_window_end,
            output=args.output,
        )
    elif args.command == "interpolate-levels":
        interpolate_levels(config, args.input, args.output)
    elif args.command == "regrid":
        regrid_dataset(config, args.kind, args.input, args.output, args.variable)
    elif args.command == "manifest":
        if args.time_start:
            config["selection"]["time_start"] = args.time_start
        if args.time_end:
            config["selection"]["time_end"] = args.time_end
        if args.time_window:
            config["selection"]["time_window"] = args.time_window
        write_manifest(config, args.surface, args.atmos, args.output)


if __name__ == "__main__":
    main()
