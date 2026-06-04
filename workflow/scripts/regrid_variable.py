import argparse

import _bootstrap  # noqa: F401  # pylint: disable=unused-import

from workflow.lib.io import load_config
from workflow.lib.logging import configure_logging
from workflow.lib.processing import regrid_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--kind", choices=("surface", "atmos"), required=True)
    parser.add_argument("--variable")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)
    regrid_dataset(
        load_config(args.config),
        kind=args.kind,
        variable=args.variable,
        input_path=args.input,
        output=args.output,
    )


if __name__ == "__main__":
    main()
