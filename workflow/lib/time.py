import numpy as np
import pandas as pd
import xarray as xr


def include_window_end(value: str) -> bool:
    return value.lower() in {"1", "true", "yes"}


def select_time_window(
    ds: xr.Dataset,
    start: pd.Timestamp,
    end: pd.Timestamp,
    include_end: bool,
) -> xr.Dataset:
    try:
        if include_end:
            mask = (ds.time >= np.datetime64(start)) & (ds.time <= np.datetime64(end))
        else:
            mask = (ds.time >= np.datetime64(start)) & (ds.time < np.datetime64(end))
        return ds.where(mask, drop=True)
    except TypeError:
        start_text = start.strftime("%Y-%m-%d %H:%M:%S")
        end_text = end.strftime("%Y-%m-%d %H:%M:%S")
        keep = []
        for value in ds.time.values:
            value_text = str(value)
            if include_end:
                keep.append(start_text <= value_text <= end_text)
            else:
                keep.append(start_text <= value_text < end_text)
        return ds.isel(time=keep)


def subset_window(
    ds: xr.Dataset,
    window_start: str | None,
    window_end: str | None,
    include_end_value: str = "true",
) -> xr.Dataset:
    if not window_start or not window_end:
        return ds

    start = pd.Timestamp(window_start)
    end = pd.Timestamp(window_end)
    windowed = select_time_window(ds, start, end, include_window_end(include_end_value))
    if windowed.sizes.get("time", 0) == 0:
        raise ValueError(f"No timesteps found in requested window {start} -> {end}")

    windowed.attrs["preprocess_time_start"] = start.isoformat()
    windowed.attrs["preprocess_time_end"] = end.isoformat()
    windowed.attrs["preprocess_time_end_inclusive"] = include_end_value
    return windowed
