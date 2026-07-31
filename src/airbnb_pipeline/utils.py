from __future__ import annotations

import ast
import glob
from pathlib import Path

import numpy as np
import pandas as pd


def concat_csv_dir(folder: Path) -> pd.DataFrame:
    """Concatenate every CSV checkpoint batch in a folder into one DataFrame."""
    files = sorted(glob.glob(str(folder / "*.csv")))
    if not files:
        raise FileNotFoundError(f"No CSV batches found in {folder}")
    frames = [pd.read_csv(f, low_memory=False) for f in files]
    df = pd.concat(frames, ignore_index=True)
    return df.loc[:, ~df.columns.str.startswith("Unnamed")]


def get_base_url(url: str) -> str:
    return str(url).split("?", 1)[0]


def convert_to_months(duration) -> float:
    if pd.isna(duration):
        return np.nan
    num, unit = str(duration).split()
    num = int(num)
    if unit.startswith("year"):
        return num * 12
    if unit.startswith("month"):
        return num
    return np.nan


def extract_lat_lng(url) -> tuple[float | None, float | None]:
    if not isinstance(url, str):
        return None, None
    params = url.split("?")[1].split("&")
    for param in params:
        key, _, value = param.partition("=")
        if key == "ll":
            lat_str, lng_str = value.split(",")
            return float(lat_str), float(lng_str)
    return None, None


def remove_unavailable(facilities):
    """Drop 'Unavailable: X' entries from a stringified facilities list."""
    if not isinstance(facilities, str):
        return facilities
    try:
        facilities_list = ast.literal_eval(facilities)
    except (ValueError, SyntaxError):
        return facilities
    filtered = [f for f in facilities_list if not f.startswith("Unavailable")]
    return str(filtered)


def parse_string_list(value) -> list[str]:
    """Parse a stringified Python list column (e.g. host_confirmed_information) safely."""
    if not isinstance(value, str):
        return []
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return []
    return parsed if isinstance(parsed, list) else []
