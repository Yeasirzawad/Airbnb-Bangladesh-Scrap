"""Backfill locality names for listings whose reverse-geocoded `localityName`
just echoes `city` (i.e. the original BigDataCloud geocoding pass couldn't
resolve a neighborhood-level name for that point).

Coordinates don't go stale, so this is safe to (re-)run independently of the
"keep the 2024 scrape snapshot" decision — it only enriches existing lat/lon,
it doesn't touch Airbnb at all. Uses OpenStreetMap's Nominatim reverse-geocoding
API (free, no key), rate-limited to 1 req/sec per its usage policy, with
incremental caching so a ~15-20 minute run is resumable if interrupted.

Usage: python -m airbnb_pipeline.stages.geocode_backfill
"""
from __future__ import annotations

import logging
import time

import pandas as pd
import requests

from airbnb_pipeline.config import Config
from airbnb_pipeline.logging_setup import configure_logging

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
USER_AGENT = "airbnb-bangladesh-market-research/1.0 (portfolio project, non-commercial)"
RATE_LIMIT_SECONDS = 1.1
# Preference order for which OSM address field best represents a "neighborhood".
LOCALITY_FIELD_PRIORITY = ["suburb", "neighbourhood", "quarter", "city_district", "borough"]


def find_unresolved_coordinates(listings_df: pd.DataFrame, valid_bd_divisions: list[str]) -> pd.DataFrame:
    """Rows where the geocoder fell back to repeating `city` as `localityName`,
    restricted to real Bangladesh divisions (no point resolving noise rows)."""
    bd = listings_df[listings_df["principalSubdivision"].isin(valid_bd_divisions)]
    unresolved = bd[bd["localityName"] == bd["city"]]
    return unresolved[["latitude", "longitude"]].drop_duplicates().reset_index(drop=True)


def reverse_geocode(lat: float, lon: float, timeout: int = 10) -> str | None:
    resp = requests.get(
        NOMINATIM_URL,
        params={"format": "json", "lat": lat, "lon": lon, "zoom": 16, "addressdetails": 1, "accept-language": "en"},
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    resp.raise_for_status()
    address = resp.json().get("address", {})
    for field in LOCALITY_FIELD_PRIORITY:
        if field in address:
            return address[field]
    return None


def run_backfill(coords: pd.DataFrame, cache_path) -> pd.DataFrame:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    existing = pd.read_csv(cache_path) if cache_path.exists() else pd.DataFrame(
        columns=["latitude", "longitude", "resolved_locality"]
    )
    done = set(zip(existing["latitude"], existing["longitude"]))
    results = existing.to_dict("records")

    todo = coords[~coords.apply(lambda r: (r["latitude"], r["longitude"]) in done, axis=1)]
    log.info("%d coordinates already cached, %d to fetch", len(done), len(todo))

    for i, row in enumerate(todo.itertuples(index=False), 1):
        try:
            locality = reverse_geocode(row.latitude, row.longitude)
        except Exception as e:
            log.warning("failed for %s,%s: %s", row.latitude, row.longitude, e)
            locality = None
        results.append({"latitude": row.latitude, "longitude": row.longitude, "resolved_locality": locality})

        if i % 20 == 0 or i == len(todo):
            pd.DataFrame(results).to_csv(cache_path, index=False)
            log.info("progress: %d/%d fetched this run (%d total cached)", i, len(todo), len(results))

        time.sleep(RATE_LIMIT_SECONDS)

    return pd.DataFrame(results)


def apply_backfill(location_df: pd.DataFrame, cache_path) -> pd.DataFrame:
    """Patch `localityName` using the cached Nominatim results, wherever it
    resolved something better than the original city-echo fallback."""
    if not cache_path.exists():
        log.warning("no locality backfill cache at %s — skipping", cache_path)
        return location_df

    cache = pd.read_csv(cache_path).dropna(subset=["resolved_locality"])
    location_df = location_df.merge(cache, on=["latitude", "longitude"], how="left")

    is_echo = location_df["localityName"] == location_df["city"]
    can_upgrade = is_echo & location_df["resolved_locality"].notna()
    location_df.loc[can_upgrade, "localityName"] = location_df.loc[can_upgrade, "resolved_locality"]
    log.info("locality backfill applied: upgraded %d/%d echo rows", can_upgrade.sum(), is_echo.sum())

    return location_df.drop(columns=["resolved_locality"])


def write_unresolved_localities(listings_df: pd.DataFrame, valid_bd_divisions: list[str], out_path) -> pd.DataFrame:
    """Export listings still stuck on the city-echo fallback after backfilling,
    with a clickable map link, so they can be reviewed/filled in by hand."""
    bd = listings_df[listings_df["principalSubdivision"].isin(valid_bd_divisions)]
    unresolved = bd[bd["localityName"] == bd["city"]].copy()

    unresolved["map_link"] = (
        "https://www.google.com/maps?q=" + unresolved["latitude"].astype(str) + "," + unresolved["longitude"].astype(str)
    )
    out_cols = [
        "listing_link", "base_urls", "listing_title", "principalSubdivision", "city",
        "latitude", "longitude", "map_link",
    ]
    unresolved = unresolved[out_cols].rename(columns={"city": "localityName_unresolved"})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    unresolved.to_csv(out_path, index=False)
    log.info("wrote %s (%d unresolved listings for manual review)", out_path, len(unresolved))
    return unresolved


def main() -> None:
    configure_logging()
    cfg = Config.load()

    listings = pd.read_csv(cfg.path("processed.listings"))
    coords = find_unresolved_coordinates(listings, cfg.valid_bd_divisions)
    log.info("%d unresolved unique coordinates to backfill", len(coords))

    cache_path = cfg.path("interim.locality_backfill")
    result = run_backfill(coords, cache_path)

    resolved = result["resolved_locality"].notna().sum()
    log.info("done: %d/%d coordinates resolved to a locality name", resolved, len(result))


if __name__ == "__main__":
    main()
