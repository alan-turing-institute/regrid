from __future__ import annotations

import pandas as pd


def time_windows(config: dict) -> list[dict[str, str]]:
    """Return stable half-open time windows for the configured selection."""
    sel = config["selection"]
    start = pd.Timestamp(sel["time_start"])
    end = pd.Timestamp(sel["time_end"])
    if start >= end:
        raise ValueError(f"time_start must be before time_end: {start} >= {end}")

    freq = sel.get("time_window")
    fmt = sel.get("time_label_format", "%Y%m%d")

    if not freq:
        return [_window(start, end, fmt)]

    starts = list(pd.date_range(start=start, end=end, freq=freq))
    if not starts or starts[0] != start:
        starts.insert(0, start)

    windows = []
    for idx, window_start in enumerate(starts):
        next_start = starts[idx + 1] if idx + 1 < len(starts) else end
        window_end = min(next_start, end)
        if window_start >= end:
            continue
        windows.append(_window(window_start, window_end, fmt))
    return windows


def _window(start: pd.Timestamp, end: pd.Timestamp, fmt: str) -> dict[str, str]:
    return {
        "label": f"{start.strftime(fmt)}_{end.strftime(fmt)}",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "include_end": "false",
    }
