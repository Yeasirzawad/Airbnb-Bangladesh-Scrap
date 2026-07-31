from __future__ import annotations

import logging

import pandas as pd

from airbnb_pipeline.config import Config
from airbnb_pipeline.utils import concat_csv_dir, convert_to_months, get_base_url, parse_string_list

log = logging.getLogger(__name__)

# Raw badge label (as scraped from Airbnb's "confirmed information" section) -> clean column name.
HOST_BADGE_COLUMNS = {
    "Identity": "host_verified_identity",
    "Email address": "host_verified_email",
    "Phone number": "host_verified_phone",
    "Work email": "host_verified_work_email",
}


def load_and_dedupe_hosts(cfg: Config) -> pd.DataFrame:
    """Consolidate raw host-profile scrape batches into one row per host.

    Fixes the legacy pipeline's ordering bug: hosts are deduplicated *before*
    being joined to listings, so the join can't temporarily inflate row counts.
    """
    hosts = concat_csv_dir(cfg.path("raw.host_batches_dir"))
    before = len(hosts)
    hosts = hosts.drop_duplicates(subset="host_link", keep="last").reset_index(drop=True)
    log.info("hosts: %d raw rows -> %d unique host_link", before, len(hosts))

    for raw_label, column in HOST_BADGE_COLUMNS.items():
        hosts[column] = hosts["host_confirmed_information"].apply(
            lambda info, label=raw_label: label in parse_string_list(info)
        )
    hosts = hosts.drop(columns=["host_confirmed_information"])

    hosts["host_hosting_duration_months"] = hosts["host_hosting_duration"].apply(convert_to_months)
    hosts = hosts.drop(columns=["host_hosting_duration"])

    return hosts


def load_and_dedupe_listings(cfg: Config) -> pd.DataFrame:
    """Consolidate raw listing-detail scrape batches (both rounds) into one row per listing."""
    round_1 = concat_csv_dir(cfg.path("raw.listing_batches_dir"))
    round_2 = concat_csv_dir(cfg.path("raw.listing_batches_v2_dir"))
    listings = pd.concat([round_1, round_2], ignore_index=True)

    listings["base_urls"] = listings["listing_link"].apply(get_base_url)
    before = len(listings)
    listings = listings.drop_duplicates(subset="base_urls", keep="last").reset_index(drop=True)
    log.info("listings: %d raw rows -> %d unique base_urls", before, len(listings))
    return listings


def build_listings_and_hosts(cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (listings, hosts) as two separate, properly-grained tables.

    A host can have many listings (one host in this dataset has 217), so this
    is a Hosts(1) -> Listings(Many) relationship, not 1:1. Keeping them as
    separate tables — instead of denormalizing host columns onto every one of
    that host's listing rows — avoids duplicating host attributes and lets
    Power BI model the real cardinality.
    """
    listings = load_and_dedupe_listings(cfg)
    hosts = load_and_dedupe_hosts(cfg)

    listings = listings[listings["host_link"].isin(hosts["host_link"])].reset_index(drop=True)
    hosts = hosts[hosts["host_link"].isin(listings["host_link"])].reset_index(drop=True)

    log.info(
        "listings x hosts: %d listings matched to %d distinct hosts",
        len(listings), len(hosts),
    )
    return listings, hosts
