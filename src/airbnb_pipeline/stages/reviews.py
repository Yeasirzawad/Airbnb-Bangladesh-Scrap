from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

import pandas as pd

from airbnb_pipeline.config import Config
from airbnb_pipeline.utils import concat_csv_dir, get_base_url

log = logging.getLogger(__name__)

# Scrape happened ~June-July 2024 (listing search URLs carry check_in=2024-06-...
# dates; raw file timestamps aren't reliable). Relative dates like "3 weeks ago"
# are resolved against this, not against whenever the pipeline happens to run —
# using datetime.today() here would silently push every relative review date
# ~2 years into the future.
SCRAPE_REFERENCE_DATE = datetime(2024, 7, 1)

_MONTH_YEAR_RE = re.compile(
    r"(january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\s+(\d{4})",
    re.IGNORECASE,
)
_RELATIVE_RE = re.compile(r"(\d+)\s*(day|week|month|year)s?\s*ago", re.IGNORECASE)
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _resolve_review_date(date_text: str, reference: datetime = SCRAPE_REFERENCE_DATE) -> datetime | None:
    if not isinstance(date_text, str) or not date_text.strip():
        return None
    text = date_text.strip().lower()

    m = _MONTH_YEAR_RE.search(text)
    if m:
        return datetime(int(m.group(2)), _MONTHS[m.group(1)], 1)

    m = _RELATIVE_RE.search(text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days_per_unit = {"day": 1, "week": 7, "month": 30, "year": 365}[unit]
        return reference - timedelta(days=n * days_per_unit)

    if "yesterday" in text:
        return reference - timedelta(days=1)
    if "today" in text:
        return reference

    log.warning("unrecognized review date text: %r", date_text)
    return None


def _extract_review_date_text(info: pd.Series) -> pd.Series:
    """`info` looks like "Rating, 5 stars,  · August 2023,  · Group trip" —
    strip the rating prefix, then take the text up to (but not including) the
    next bullet-separated segment (trip-type note, when present)."""
    remainder = info.str.replace(r"^.*?stars?,?\s*", "", regex=True, flags=re.IGNORECASE)
    stripped = remainder.str.lstrip(" ,�·")
    return stripped.str.split(r"[�·]", n=1, regex=True).str[0].str.strip().str.rstrip(",")


def load_and_clean_reviews(cfg: Config) -> pd.DataFrame:
    raw = concat_csv_dir(cfg.path("raw.review_batches_dir"))
    log.info("reviews: %d raw rows across all batches", len(raw))

    df = raw[raw["info"].notna()].copy()

    df["reviewer_rating"] = pd.to_numeric(
        df["info"].str.extract(r"(\d+)\s*stars?", flags=re.IGNORECASE)[0], errors="coerce"
    ).astype("Int64")

    review_date_text = _extract_review_date_text(df["info"])
    df["review_date"] = review_date_text.apply(_resolve_review_date)

    df["base_urls"] = df["review_link"].apply(get_base_url).str.replace("/reviews", "", regex=False)

    unresolved = df["review_date"].isna().sum()
    if unresolved:
        log.warning("%d/%d reviews had an unparseable date", unresolved, len(df))

    out = df[[
        "base_urls", "review_link", "reviewer_name", "reviewer_rating",
        "review_date", "rating_comment",
    ]]
    log.info(
        "cleaned reviews: %d rows covering %d distinct listings",
        len(out), out["base_urls"].nunique(),
    )
    return out
