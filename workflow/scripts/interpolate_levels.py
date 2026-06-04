import argparse

import _bootstrap  # noqa: F401  # pylint: disable=unused-import

from workflow.lib.io import load_config
from workflow.lib.logging import configure_logging
from workflow.lib.processing import interpolate_levels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    interpolate_levels(load_config(args.config), args.input, args.output)


if __name__ == "__main__":
    main()
