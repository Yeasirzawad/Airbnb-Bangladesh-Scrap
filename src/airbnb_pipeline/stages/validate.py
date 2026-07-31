from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import pandas as pd

from airbnb_pipeline.config import Config

log = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "listing_link", "base_urls", "host_link", "price_per_night", "review_count",
    "listing_rating", "principalSubdivision",
]
REQUIRED_HOST_COLUMNS = ["host_link", "host_name", "host_verified_identity"]


def add_division_flag(listings_df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Flag rows whose reverse-geocoded division isn't a real Bangladesh division
    (e.g. "West Bengal", "Meghalaya") instead of silently dropping them.
    Rows are kept — division-level analysis should filter on is_bd_division=True.
    """
    listings_df = listings_df.copy()
    listings_df["is_bd_division"] = listings_df["principalSubdivision"].isin(cfg.valid_bd_divisions)
    return listings_df


def build_data_quality_report(
    listings_df: pd.DataFrame, hosts_df: pd.DataFrame, facilities_df: pd.DataFrame, cfg: Config
) -> dict:
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in listings_df.columns]
    if missing_cols:
        raise ValueError(f"final listings table is missing required columns: {missing_cols}")
    missing_host_cols = [c for c in REQUIRED_HOST_COLUMNS if c not in hosts_df.columns]
    if missing_host_cols:
        raise ValueError(f"final hosts table is missing required columns: {missing_host_cols}")

    dup_base_urls = int(listings_df["base_urls"].duplicated().sum())
    if dup_base_urls:
        log.warning("found %d duplicate base_urls in final listings table", dup_base_urls)

    dup_host_links = int(hosts_df["host_link"].duplicated().sum())
    if dup_host_links:
        log.warning("found %d duplicate host_link in final hosts table", dup_host_links)

    multi_listing_hosts = int((listings_df["host_link"].value_counts() > 1).sum())

    non_bd_rows = int((~listings_df["is_bd_division"]).sum())

    def completeness(col: str, frame: pd.DataFrame = listings_df) -> float:
        return round(float(frame[col].notna().mean()), 4)

    def unparseable_count(col: str) -> int:
        """bedrooms/beds/baths come from a positional string-split heuristic on
        Airbnb's listing-card meta text; it silently misparses when that text
        deviates from the expected pattern (e.g. a "New listing" badge shifts
        every field over by one). Count non-numeric survivors so the report
        surfaces this instead of hiding it."""
        values = listings_df[col]
        non_numeric = pd.to_numeric(values, errors="coerce").isna() & values.notna()
        return int(non_numeric.sum())

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_counts": {
            "total_listings": len(listings_df),
            "bd_division_listings": int(listings_df["is_bd_division"].sum()),
            "non_bd_division_listings": non_bd_rows,
            "total_facilities_rows": len(facilities_df),
            "total_hosts": len(hosts_df),
            "hosts_with_multiple_listings": multi_listing_hosts,
        },
        "integrity": {
            "duplicate_base_urls": dup_base_urls,
            "duplicate_host_links": dup_host_links,
            "unparseable_bedrooms": unparseable_count("bedrooms"),
            "unparseable_beds": unparseable_count("beds"),
            "unparseable_baths": unparseable_count("baths"),
            "unparseable_listing_rating": unparseable_count("listing_rating"),
        },
        "completeness": {
            "price_per_night": completeness("price_per_night"),
            "listing_rating": completeness("listing_rating"),
            "review_count": completeness("review_count"),
            "host_rating": completeness("host_rating", hosts_df),
        },
        "division_breakdown": (
            listings_df["principalSubdivision"].value_counts(dropna=False).to_dict()
        ),
        "notes": [
            "listing_rating is expected to be missing for listings without enough "
            "reviews yet (Airbnb doesn't surface a rating until then) — not a defect.",
            "non_bd_division_listings are reverse-geocoding noise near the Bangladesh "
            "border; kept in the data with is_bd_division=False rather than dropped.",
            "unparseable_bedrooms/beds/baths/listing_rating come from the same fragile "
            "positional string-split on Airbnb's listing-card text (see "
            "clean.py:_parse_title_bed_bath docstring) — e.g. a 'New listing' badge lands "
            "in the rating position instead of a star rating. completeness.listing_rating "
            "counts non-null values, which is HIGHER than the count of genuinely numeric "
            "ratings; subtract unparseable_listing_rating for the true usable rate.",
            "hosts_with_multiple_listings host_link appears >1 time in listings.csv "
            "(one host has 217) — this is why listings and hosts are kept as separate "
            "tables (Hosts 1 -> Listings Many) instead of one denormalized table.",
        ],
    }
    return report


def write_data_quality_report(report: dict, cfg: Config) -> None:
    out_path = cfg.path("processed.data_quality_report")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log.info("wrote data-quality report -> %s", out_path)
