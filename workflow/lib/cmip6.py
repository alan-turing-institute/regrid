import logging
import re
from pathlib import Path

import pandas as pd
from tqdm import tqdm

CMIP6_TIME_RANGE_RE = re.compile(r"_(\d{8,12})-(\d{8,12})\.nc$")
LOGGER = logging.getLogger(__name__)


def variable_dir(config: dict, variable: str) -> Path:
    cmip6 = config["cmip6"]
    table_id = cmip6["table_id_by_variable"][variable]
    return (
        Path(cmip6["root"])
        / cmip6["activity_id"]
        / cmip6["institution_id"]
        / cmip6["source_id"]
        / cmip6["experiment_id"]
        / cmip6["member_id"]
        / table_id
        / variable
        / cmip6["grid_label"]
        / cmip6.get("version", "latest")
    )


def parse_cmip6_time(value: str) -> pd.Timestamp:
    if len(value) == 8:
        return pd.to_datetime(value, format="%Y%m%d")
    if len(value) == 12:
        return pd.to_datetime(value, format="%Y%m%d%H%M")
    raise ValueError(f"Unsupported CMIP6 timestamp format: {value}")


def file_overlaps_window(path: Path, start: str | None, end: str | None) -> bool:
    if not start or not end:
        return True

    match = CMIP6_TIME_RANGE_RE.search(path.name)
    if not match:
        return True

    file_start = parse_cmip6_time(match.group(1))
    file_end = parse_cmip6_time(match.group(2))
    window_start = pd.Timestamp(start)
    window_end = pd.Timestamp(end)
    return file_start <= window_end and file_end >= window_start


def variable_files(
    config: dict,
    variable: str,
    window_start: str | None = None,
    window_end: str | None = None,
) -> list[str]:
    var_dir = variable_dir(config, variable)
    candidates = sorted(var_dir.glob(f"{variable}_*.nc"))
    LOGGER.info(
        "Found %s candidate CMIP6 files for %s in %s",
        len(candidates),
        variable,
        var_dir,
    )
    files = [
        path
        for path in tqdm(
            candidates,
            desc=f"filter {variable} files",
            unit="file",
            leave=False,
            disable=len(candidates) < 2,
        )
        if file_overlaps_window(path, window_start, window_end)
    ]
    if not files:
        window = ""
        if window_start and window_end:
            window = f" overlapping {window_start} -> {window_end}"
        raise FileNotFoundError(
            f"No CMIP6 files found for {variable}{window} in {var_dir}"
        )
    if window_start and window_end:
        LOGGER.info(
            "Selected %s CMIP6 files for %s overlapping %s -> %s",
            len(files),
            variable,
            window_start,
            window_end,
        )
    return [str(path) for path in files]
