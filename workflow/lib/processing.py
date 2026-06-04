import logging

import numpy as np
import xarray as xr
from tqdm import tqdm

from workflow.lib import cmip6
from workflow.lib.grid import (
    build_regridder,
    decreasing_lat,
    normalize_lon_lat,
    regrid_with_xarray,
)
from workflow.lib.io import chunk_map, open_many, write_netcdf
from workflow.lib.time import subset_window

LOGGER = logging.getLogger(__name__)


def assert_no_nans(ds: xr.Dataset, context: str) -> None:
    nan_counts = {}
    items = list(ds.data_vars.items())
    for name, data_array in tqdm(
        items,
        desc=f"check NaNs: {context}",
        unit="var",
        leave=False,
        disable=len(items) < 2,
    ):
        count = data_array.isnull().sum()
        if hasattr(count.data, "compute"):
            count = count.compute()
        count_value = int(count.item())
        if count_value:
            nan_counts[name] = count_value

    if nan_counts:
        details = ", ".join(f"{name}: {count}" for name, count in nan_counts.items())
        raise ValueError(f"NaNs found in {context}: {details}")
    LOGGER.info("NaN check passed for %s", context)


def subset_common(ds: xr.Dataset, config: dict) -> xr.Dataset:
    sel = config["selection"]
    ds = normalize_lon_lat(ds)
    return ds.sel(time=slice(sel["time_start"], sel["time_end"]))


def subset_variable(
    config: dict,
    kind: str,
    variable: str,
    output: str,
    window_start: str | None = None,
    window_end: str | None = None,
    include_window_end: str = "true",
) -> None:
    LOGGER.info(
        "Subsetting %s variable %s for window %s -> %s",
        kind,
        variable,
        window_start,
        window_end,
    )
    expected_vars = config["selection"][f"{kind}_variables"]
    if variable not in expected_vars:
        raise ValueError(f"{variable} is not configured as a {kind} variable")

    ds = open_many(
        cmip6.variable_files(config, variable, window_start, window_end),
        chunk_map(config),
    )
    ds = normalize_lon_lat(ds)
    if not window_start:
        ds = subset_common(ds, config)
    ds = ds[[variable]]
    ds = subset_window(ds, window_start, window_end, include_window_end)
    LOGGER.info("Subset sizes for %s: %s", variable, dict(ds.sizes))
    assert_no_nans(ds, f"{variable} subset")
    write_netcdf(ds, output)


def interpolate_levels(config: dict, input_path: str, output: str) -> None:
    LOGGER.info("Interpolating pressure levels from %s to %s", input_path, output)
    target_plev = np.array(config["selection"]["pressure_levels_pa"], dtype=float)
    LOGGER.info("Target pressure levels: %s", target_plev.tolist())

    ds = xr.open_dataset(input_path)
    if chunk_map(config):
        ds = ds.chunk(chunk_map(config))
    assert_no_nans(ds, f"{input_path} level interpolation input")
    ds = ds.sortby("plev")
    ds = ds.interp(
        plev=target_plev,
        method="linear",
        kwargs={"fill_value": "extrapolate"},
    )
    ds = ds.assign_coords(plev=target_plev)
    LOGGER.info("Interpolated level output sizes: %s", dict(ds.sizes))
    assert_no_nans(ds, f"{output} level interpolation output")
    write_netcdf(ds, output)


def regrid_xesmf(
    config: dict,
    kind: str,
    input_path: str,
    output: str,
    variable: str | None = None,
) -> None:
    LOGGER.info("Regridding %s %s from %s to %s", kind, variable, input_path, output)
    engine = config["regridding"].get("engine", "xarray_interp")
    LOGGER.info("Regridding engine: %s", engine)

    ds = xr.open_dataset(input_path)
    if chunk_map(config):
        ds = ds.chunk(chunk_map(config))
    ds = normalize_lon_lat(ds)
    assert_no_nans(ds, f"{input_path} regrid input")

    if engine == "xesmf":
        LOGGER.info("Building xESMF regridder")
        regridder = build_regridder(ds, config, kind, variable)
        LOGGER.info("Applying xESMF regridder")
        out = regridder(ds, keep_attrs=True)
        if not config["runtime"].get("keep_weights", True):
            regridder.clean_weight_file()
    elif engine == "xarray_interp":
        LOGGER.info("Applying xarray interpolation regridder")
        out = regrid_with_xarray(ds, config)
    else:
        raise ValueError(f"Unsupported regridding engine: {engine}")

    out = decreasing_lat(out)
    LOGGER.info("Regridded output sizes: %s", dict(out.sizes))
    assert_no_nans(out, f"{output} regrid output")
    write_netcdf(out, output)


def regrid_dataset(
    config: dict,
    kind: str,
    input_path: str,
    output: str,
    variable: str | None = None,
) -> None:
    LOGGER.info("Regridding %s %s from %s to %s", kind, variable, input_path, output)
    engine = config["regridding"].get("engine", "xarray_interp")
    LOGGER.info("Regridding engine: %s", engine)

    ds = xr.open_dataset(input_path)
    if chunk_map(config):
        ds = ds.chunk(chunk_map(config))
    ds = normalize_lon_lat(ds)
    assert_no_nans(ds, f"{input_path} regrid input")

    if engine == "xesmf":
        LOGGER.info("Building xESMF regridder")
        regridder = build_regridder(ds, config, kind, variable)
        LOGGER.info("Applying xESMF regridder")
        out = regridder(ds, keep_attrs=True)
        if not config["runtime"].get("keep_weights", True):
            regridder.clean_weight_file()
    elif engine == "xarray_interp":
        LOGGER.info("Applying xarray interpolation regridder")
        out = regrid_with_xarray(ds, config)
    else:
        raise ValueError(f"Unsupported regridding engine: {engine}")

    out = decreasing_lat(out)
    LOGGER.info("Regridded output sizes: %s", dict(out.sizes))
    assert_no_nans(out, f"{output} regrid output")
    write_netcdf(out, output)
