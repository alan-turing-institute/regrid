import logging
from pathlib import Path

import xarray as xr
import yaml

LOGGER = logging.getLogger(__name__)


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def write_netcdf(ds: xr.Dataset, output: str | Path) -> None:
    LOGGER.info("Writing NetCDF: %s", output)
    ensure_parent(output)
    encoding = {
        name: {"zlib": True, "complevel": 1}
        for name in ds.data_vars
        if ds[name].dtype.kind in {"f", "i", "u"}
    }
    ds.to_netcdf(output, encoding=encoding)
    LOGGER.info("Finished writing NetCDF: %s", output)


def chunk_map(config: dict) -> dict:
    return config.get("runtime", {}).get("chunks", {})


def netcdf_files(path: str | Path) -> list[Path]:
    input_path = Path(path)
    if input_path.is_file():
        return [input_path]

    files = sorted(input_path.glob("*.nc"))
    if not files:
        raise FileNotFoundError(f"No NetCDF files found in {path}")
    return files


def resolve_netcdf_inputs(paths: list[str]) -> list[Path]:
    files = []
    for path in paths:
        files.extend(netcdf_files(path))
    return sorted(files)


def open_many(paths: list[str], chunks: dict) -> xr.Dataset:
    LOGGER.info("Opening %s NetCDF files", len(paths))
    ds = xr.open_mfdataset(
        paths,
        combine="by_coords",
        compat="override",
        coords="minimal",
        data_vars="minimal",
    )
    if chunks:
        LOGGER.info("Applying chunks: %s", chunks)
        ds = ds.chunk(chunks)
    return ds
