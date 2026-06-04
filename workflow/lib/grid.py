import logging
from pathlib import Path

import numpy as np
import xarray as xr

LOGGER = logging.getLogger(__name__)


def regridding_label(config: dict) -> str:
    rg = config["regridding"]
    resolution = rg.get("resolution_degrees")
    if resolution:
        value = f"{float(resolution):g}".replace(".", "p")
        return f"{value}deg"
    return f"lat{rg['target_lat_count']}_lon{rg['target_lon_count']}"


def normalize_lon_lat(ds: xr.Dataset) -> xr.Dataset:
    if "lon" in ds.coords:
        ds = ds.assign_coords(lon=ds["lon"] % 360).sortby("lon")
    if "lat" in ds.coords and ds["lat"][0] > ds["lat"][-1]:
        ds = ds.sortby("lat")
    return ds


def decreasing_lat(ds: xr.Dataset) -> xr.Dataset:
    if "lat" in ds.coords and ds["lat"][0] < ds["lat"][-1]:
        return ds.sortby("lat", ascending=False)
    return ds


def coordinate_values(start: float, stop: float, resolution: float) -> np.ndarray:
    direction = 1 if stop >= start else -1
    count = int(round(abs(stop - start) / resolution)) + 1
    values = start + direction * resolution * np.arange(count)
    if not np.isclose(values[-1], stop):
        raise ValueError(
            f"Resolution {resolution} does not land exactly on {start} -> {stop}"
        )
    return values


def target_grid(config: dict) -> xr.Dataset:
    rg = config["regridding"]
    resolution = rg.get("resolution_degrees")
    if resolution:
        resolution = float(resolution)
        lat = coordinate_values(
            rg.get("target_lat_start", -90.0 + resolution / 2),
            rg.get("target_lat_stop", 90.0 - resolution / 2),
            resolution,
        )
        lon = coordinate_values(
            rg.get("target_lon_start", 0.0),
            rg.get("target_lon_stop", 360.0 - resolution),
            resolution,
        )
    else:
        lat = np.linspace(
            rg["target_lat_start"],
            rg["target_lat_stop"],
            rg["target_lat_count"],
        )
        lon = np.linspace(
            rg["target_lon_start"],
            rg["target_lon_stop"],
            rg["target_lon_count"],
        )
    LOGGER.info(
        "Target grid: lat=%s (%s -> %s), lon=%s (%s -> %s)",
        len(lat),
        float(lat[0]),
        float(lat[-1]),
        len(lon),
        float(lon[0]),
        float(lon[-1]),
    )
    return xr.Dataset(coords={"lat": lat, "lon": lon})


def regrid_with_xarray(ds: xr.Dataset, config: dict) -> xr.Dataset:
    target = target_grid(config)
    LOGGER.info("Interpolating with xarray to target grid")
    return ds.interp(lat=target["lat"], lon=target["lon"], method="linear")


def build_regridder(
    ds: xr.Dataset, config: dict, kind: str, variable: str | None = None
):
    import xesmf as xe

    rg = config["regridding"]
    weights_dir = Path(config["runtime"]["weights_dir"])
    weights_dir.mkdir(parents=True, exist_ok=True)
    weight_stem = f"{kind}.{variable}" if variable else kind
    weights_path = (
        weights_dir / f"{weight_stem}.{regridding_label(config)}.{rg['method']}.nc"
    )
    LOGGER.info("xESMF weights path: %s", weights_path)

    return xe.Regridder(
        ds,
        target_grid(config),
        method=rg["method"],
        periodic=rg["periodic"],
        filename=str(weights_path),
        reuse_weights=weights_path.exists(),
    )
