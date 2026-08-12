"""One-command entry point for the Bangladesh Airbnb ETL pipeline.

Runs merge -> clean -> validate against the existing raw/interim data
(no live scraping or re-geocoding) and writes the Power BI source files
(listings, hosts, facilities) plus the reviews table and a data-quality report.

Usage: python run_pipeline.py
"""
from __future__ import annotations

import logging

from airbnb_pipeline.config import Config
from airbnb_pipeline.logging_setup import configure_logging
from airbnb_pipeline.stages.clean import clean_listings, load_location_data
from airbnb_pipeline.stages.geocode_backfill import apply_backfill, write_unresolved_localities
from airbnb_pipeline.stages.merge import build_listings_and_hosts
from airbnb_pipeline.stages.review_nlp import enrich_reviews
from airbnb_pipeline.stages.reviews import load_and_clean_reviews
from airbnb_pipeline.stages.validate import add_division_flag, build_data_quality_report, write_data_quality_report

log = logging.getLogger("run_pipeline")


def main() -> None:
    configure_logging()
    cfg = Config.load()

    log.info("stage 1/4: merge")
    raw_listings, hosts_df = build_listings_and_hosts(cfg)

    log.info("stage 2/4: clean")
    location_data = load_location_data(cfg)
    location_data = apply_backfill(location_data, cfg.path("interim.locality_backfill"))
    listings_df, facilities_df = clean_listings(raw_listings, location_data)

    # clean_listings' inner join to location_data can drop a few more listings
    # (no geocoded location) than build_listings_and_hosts saw, which could
    # leave a host in hosts_df with zero matching rows in the final listings.
    # Re-filter against the post-clean listings to keep the two tables consistent.
    hosts_df = hosts_df[hosts_df["host_link"].isin(listings_df["host_link"])].reset_index(drop=True)

    log.info("stage 3/4: validate")
    listings_df = add_division_flag(listings_df, cfg)
    report = build_data_quality_report(listings_df, hosts_df, facilities_df, cfg)
    write_data_quality_report(report, cfg)

    listings_out = cfg.path("processed.listings")
    hosts_out = cfg.path("processed.hosts")
    facilities_out = cfg.path("processed.facilities")
    listings_out.parent.mkdir(parents=True, exist_ok=True)
    listings_df.to_csv(listings_out, index=False)
    hosts_df.to_csv(hosts_out, index=False)
    facilities_df.to_csv(facilities_out, index=False)
    log.info("wrote %s (%d rows)", listings_out, len(listings_df))
    log.info("wrote %s (%d rows)", hosts_out, len(hosts_df))
    log.info("wrote %s (%d rows)", facilities_out, len(facilities_df))

    write_unresolved_localities(listings_df, cfg.valid_bd_divisions, cfg.path("processed.unresolved_localities"))

    log.info("stage 4/5: reviews")
    reviews_df = load_and_clean_reviews(cfg)

    log.info("stage 5/5: review NLP (sentiment + theme tags)")
    reviews_df = enrich_reviews(reviews_df)

    reviews_out = cfg.path("processed.reviews")
    reviews_out.parent.mkdir(parents=True, exist_ok=True)
    reviews_df.to_csv(reviews_out, index=False)
    log.info("wrote %s (%d rows)", reviews_out, len(reviews_df))

    rc = report["row_counts"]
    log.info(
        "summary: %d listings (%d in BD divisions, %d geocoding noise), %d distinct hosts (%d with multiple listings)",
        rc["total_listings"], rc["bd_division_listings"], rc["non_bd_division_listings"],
        rc["total_hosts"], rc["hosts_with_multiple_listings"],
    )


if __name__ == "__main__":
    main()
