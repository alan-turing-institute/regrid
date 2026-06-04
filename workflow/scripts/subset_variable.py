import argparse

import _bootstrap  # noqa: F401  # pylint: disable=unused-import

from workflow.lib.io import load_config
from workflow.lib.logging import configure_logging
from workflow.lib.processing import subset_variable


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--kind", choices=("surface", "atmos"), required=True)
    parser.add_argument("--variable", required=True)
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    parser.add_argument("--include-window-end", default="true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    subset_variable(
        load_config(args.config),
        kind=args.kind,
        variable=args.variable,
        window_start=args.window_start,
        window_end=args.window_end,
        include_window_end=args.include_window_end,
        output=args.output,
    )


if __name__ == "__main__":
    main()
