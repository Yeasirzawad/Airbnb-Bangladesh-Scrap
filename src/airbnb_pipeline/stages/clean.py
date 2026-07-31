from __future__ import annotations

import logging

import pandas as pd

from airbnb_pipeline.config import Config
from airbnb_pipeline.utils import extract_lat_lng, remove_unavailable

log = logging.getLogger(__name__)

# Every facility flag column the scraper recognizes. Kept as the raw scraped
# labels (not renamed) so existing Power BI measures referencing e.g.
# facilities[hdtv] keep working against v2 output.
FACILITY_COLUMNS = [
    "hdtv", "stove", "wifi", "disney+", "amazon prime video", "netflix", "hbo max",
    "apple tv", "soap", "shampoo", "conditioner", "view", "oven", "clothing storage",
    "fireplace", "refrigerator", "air conditioning", "pool", "gym", "housekeeping",
    "free parking", "paid parking", "washer", "dryer", "children’s books and toys",
    "coffee maker", "bbq grill", "exercise equipment", "sound system", "security cameras",
    "golf", "sauna", "bathtub", "board games", "game console", "smoke alarm",
    "fire alarm", "fire extinguisher",
]


def _parse_title_bed_bath(df: pd.DataFrame) -> pd.DataFrame:
    """Split Airbnb's combined meta string (e.g. "Studio in Dhaka - 4.5 - 2 beds - 1 bath")
    into listing_title / listing_rating / bedrooms / beds / baths.

    This is positional string-splitting tied to Airbnb's mid-2024 listing-card
    format; it has no schema to validate against and will silently misparse if
    that format changes (e.g. a studio with no bedroom count shifts every
    downstream field by one position). Ported as-is from the original
    notebooks/clean_data.py rather than redesigned, per the v2 scope.
    """
    copy = df["title_bed_bats_review"].str.replace("·", ",").str.title()
    split_cols = copy.str.split(",", expand=True)
    split_cols.columns = [f"part_{i + 1}" for i in range(split_cols.shape[1])]
    df = pd.concat([df, split_cols], axis=1)

    bedroom = split_cols.get("part_2", pd.Series(index=df.index, dtype=object)).str.replace("★", "")
    beds = split_cols.get("part_3", pd.Series(index=df.index, dtype=object))
    baths = split_cols.get("part_4", pd.Series(index=df.index, dtype=object))
    part_5 = split_cols.get("part_5", pd.Series(index=df.index, dtype=object))

    has_bedroom = bedroom.str.contains("Bed", na=False)
    listing_rating = bedroom.where(~has_bedroom)
    main_bedroom = bedroom.where(has_bedroom, beds)

    beds_norm = beds.str.replace("Bedroom ", "Bedrooms")
    beds_main = baths.where(beds_norm.str.contains("Bedrooms", na=False), beds)

    main_beds = beds_main.where(~beds_main.str.contains("Bath", na=False))

    bath_main = beds_main.where(baths.isna(), baths)
    main_baths = bath_main.where(part_5.isna(), part_5)

    for series_name, series in [("bedrooms", main_bedroom), ("beds", main_beds), ("baths", main_baths)]:
        for old, new in [
            ("Bedroom", ""), ("s", ""), ("Beds", ""), ("Bed", ""), ("Bath", ""),
            ("Private", ""), ("Shared", ""), ("Half", "1"), ("-", ""), ("Studio", ""),
        ]:
            series = series.str.replace(old, new)
        df[series_name] = series

    df["listing_title"] = split_cols.get("part_1")
    df["listing_rating"] = listing_rating
    return df.drop(columns=[c for c in split_cols.columns] + ["title_bed_bats_review"])


def clean_listings(listings: pd.DataFrame, location_data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Transform the raw listings table into the listings + facilities outputs.
    Host attributes live in a separate hosts table (see stages/merge.py) and
    are not touched here — only host_link (FK) and host_response_rate (a
    listing-page attribute, not a host-profile attribute) pass through.
    """
    df = listings.copy()

    df = _parse_title_bed_bath(df)

    df["price_per_night"] = df["price_per_night"].replace(r"[\$,]", "", regex=True).astype(float)
    df["host_response_rate"] = (
        df["host_response_rate"].str.split(":", expand=True)[1].str.replace("%", "").astype(float)
    )
    df["review_count"] = (
        pd.to_numeric(df["review_count"].str.extract(r"(\d+)")[0], errors="coerce").fillna(0).astype(int)
    )
    df[["latitude", "longitude"]] = df["google_map_location_link"].apply(
        lambda x: pd.Series(extract_lat_lng(x))
    )

    df["facilities"] = df["facilities"].apply(remove_unavailable)
    for facility in FACILITY_COLUMNS:
        df[facility] = df["facilities"].str.contains(facility, case=False, na=False, regex=False).astype(int)

    facilities_df = df[["base_urls", "facilities"] + FACILITY_COLUMNS].copy()

    df = df.merge(
        location_data[["listing_link", "principalSubdivision", "city", "localityName", "country_name"]],
        on="listing_link", how="inner",
    )

    keep_cols = [
        "listing_link", "base_urls", "listing_title", "listing_rating", "bedrooms", "beds", "baths",
        "latitude", "longitude", "price_per_night", "review_count", "review_count_link",
        "listing_description", "host_link", "host_response_rate", "cleanliness_ratings",
        "accuracy_ratings", "check-in_ratings", "communication_ratings", "location_ratings",
        "value_ratings", "facilities", "principalSubdivision", "city", "localityName", "country_name",
    ]
    listings_df = df[keep_cols]

    log.info("cleaned listings: %d rows, %d columns", len(listings_df), len(listings_df.columns))
    return listings_df, facilities_df


def load_location_data(cfg: Config) -> pd.DataFrame:
    return pd.read_csv(cfg.path("interim.location_data"))
