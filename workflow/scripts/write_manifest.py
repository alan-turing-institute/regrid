import argparse

import _bootstrap  # noqa: F401  # pylint: disable=unused-import

from workflow.lib.io import load_config
from workflow.lib.logging import configure_logging
from workflow.lib.manifest import write_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--surface", nargs="+", required=True)
    parser.add_argument("--atmos", nargs="+", required=True)
    parser.add_argument("--time-start")
    parser.add_argument("--time-end")
    parser.add_argument("--time-window")
    parser.add_argument("--output", required=True)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    config = load_config(args.config)
    if args.time_start:
        config["selection"]["time_start"] = args.time_start
    if args.time_end:
        config["selection"]["time_end"] = args.time_end
    if args.time_window:
        config["selection"]["time_window"] = args.time_window
    write_manifest(config, args.surface, args.atmos, args.output)


if __name__ == "__main__":
    main()
