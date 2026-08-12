"""Enriches reviews.csv with sentiment scores and theme tags.

Sentiment: VADER (lexicon-based, via nltk) — a document-level compound score
per review, -1 (most negative) to +1 (most positive).

Themes: keyword/category matching, not topic modeling — flags which of a
fixed set of operationally meaningful categories a review mentions. This is
basic rule-based text classification, not a trained/statistical classifier:
it doesn't understand negation or do per-theme sentiment (a review can be
tagged both cleanliness and host_communication without knowing which one, if
either, was praised vs criticized — see docstring on tag_themes). Word lists
below were iteratively validated against real review samples, not a first
guess — see conversation history for the false negatives an earlier, narrower
list produced (e.g. "friendly host" / "great hospitality" missed under a
list that only had "host was").
"""
from __future__ import annotations

import logging

import nltk
import pandas as pd

log = logging.getLogger(__name__)

THEME_KEYWORDS = {
    "cleanliness": ["clean", "dirty", "dust", "spotless", "stain", "smell", "hygien", "tidy", "messy"],
    "host_communication": [
        "responsive", "communicat", "respond", "reply", "helpful", "host was", "host is",
        "friendly", "hospitality", "hospitable", "accommodating", "welcoming", "welcomed",
        "caring", "kind", "warm", "gracious", "attentive", "accessible", "cooperative",
        "great host", "amazing host", "wonderful host", "nice host", "best host",
    ],
    "value_price": ["worth", "price", "value", "expensive", "cheap", "overpriced", "money", "affordable", "budget"],
    "location": [
        "location", "located", "walk", "distance", "nearby", "close to", "far from",
        "neighborhood", "area", "convenient", "accessible location",
    ],
    "maintenance_amenities": [
        "broken", "not working", "ac ", "air condition", "wifi", "maintenance", "issue",
        "repair", "leak", "equipped", "amenities", "facilit",
    ],
}


def _ensure_vader_lexicon() -> None:
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        log.info("downloading nltk vader_lexicon (one-time, cached after this)")
        nltk.download("vader_lexicon", quiet=True)


def score_sentiment(texts: pd.Series) -> pd.Series:
    _ensure_vader_lexicon()
    from nltk.sentiment.vader import SentimentIntensityAnalyzer

    sia = SentimentIntensityAnalyzer()
    filled = texts.fillna("")
    return filled.apply(lambda t: sia.polarity_scores(t)["compound"] if t else None)


def tag_themes(texts: pd.Series) -> pd.DataFrame:
    """One boolean column per theme: does this review mention it at all.
    Presence only — not which reviews praised vs. criticized that theme."""
    lowered = texts.fillna("").str.lower()
    tags = {}
    for theme, keywords in THEME_KEYWORDS.items():
        tags[f"theme_{theme}"] = lowered.apply(lambda t, kws=keywords: any(kw in t for kw in kws))
    return pd.DataFrame(tags, index=texts.index)


def enrich_reviews(reviews_df: pd.DataFrame) -> pd.DataFrame:
    log.info("scoring sentiment + tagging themes for %d reviews", len(reviews_df))
    reviews_df = reviews_df.copy()
    reviews_df["sentiment_score"] = score_sentiment(reviews_df["rating_comment"])
    theme_tags = tag_themes(reviews_df["rating_comment"])
    enriched = pd.concat([reviews_df, theme_tags], axis=1)

    scored = enriched["sentiment_score"].notna().sum()
    any_theme = theme_tags.any(axis=1).sum()
    log.info("sentiment scored for %d/%d reviews; %d/%d matched at least one theme",
             scored, len(enriched), any_theme, len(enriched))
    return enriched
