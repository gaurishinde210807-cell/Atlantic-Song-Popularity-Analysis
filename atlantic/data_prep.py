"""
data_prep.py
============
Load, validate, clean, and enrich the Atlantic US Top 50 playlist dataset.

The raw CSV has daily snapshots of 50 songs. This module:
  1. Parses dates (DD-MM-YYYY -> proper datetime).
  2. Deduplicates the 2025-03-01 double-snapshot (keeps first occurrence).
  3. Validates rank range (1-50) and flags anomalies.
  4. Standardises artist names (strip whitespace, collapse internal spaces).
  5. Derives duration_min from duration_ms.
  6. Builds song-level and artist-level aggregate tables with the KPIs from the brief.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

import config


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------

def load_data(path: str | Path | None = None) -> pd.DataFrame:
    """Load the CSV, parse dates, clean, and deduplicate."""
    if path is None:
        path = config.DATA_DIR / config.CSV_NAME
    df = pd.read_csv(path)

    # Parse dates
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df = df.sort_values(["date", "position"]).reset_index(drop=True)

    # Deduplicate: 2025-03-01 has two complete snapshots (100 rows).
    # Keep the first 50 (by row order, already sorted by position).
    df = df.drop_duplicates(subset=["date", "position"], keep="first").reset_index(drop=True)

    # Validate rank range
    assert df["position"].min() >= 1 and df["position"].max() <= 50, \
        f"Position range {df['position'].min()}-{df['position'].max()} outside 1-50"

    # Standardise artist names
    df["artist"] = df["artist"].str.strip().str.replace(r"\s+", " ", regex=True)

    # Derived column: duration in minutes
    df["duration_min"] = (df["duration_ms"] / 60_000).round(2)

    # Boolean conversion (already bool from pandas, but be safe)
    df["is_explicit"] = df["is_explicit"].astype(bool)

    return df


def data_quality_report(df: pd.DataFrame) -> dict:
    """Return a dict summarising the dataset's vital signs."""
    return {
        "rows": len(df),
        "unique_dates": df["date"].nunique(),
        "date_range": f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}",
        "unique_songs": df["song"].nunique(),
        "unique_artists": df["artist"].nunique(),
        "null_counts": df.isnull().sum().to_dict(),
        "position_range": f"{df['position'].min()}-{df['position'].max()}",
        "album_types": df["album_type"].value_counts().to_dict(),
        "explicit_share_pct": round(100 * df["is_explicit"].mean(), 1),
        "popularity_range": f"{df['popularity'].min()}-{df['popularity'].max()}",
        "duration_min_range": f"{df['duration_min'].min():.2f}-{df['duration_min'].max():.2f}",
        "rows_per_date_min": int(df.groupby("date").size().min()),
        "rows_per_date_max": int(df.groupby("date").size().max()),
    }


# ---------------------------------------------------------------------------
# Song-level aggregation (KPIs from the brief)
# ---------------------------------------------------------------------------

def build_song_stats(df: pd.DataFrame) -> pd.DataFrame:
    """One row per unique song with its KPIs."""
    grp = df.groupby(["song", "artist"])
    stats = grp.agg(
        days_on_chart=("date", "nunique"),
        avg_rank=("position", "mean"),
        best_rank=("position", "min"),
        worst_rank=("position", "max"),
        rank_volatility=("position", "std"),
        avg_popularity=("popularity", "mean"),
        max_popularity=("popularity", "max"),
        min_popularity=("popularity", "min"),
        popularity_std=("popularity", "std"),
        avg_duration_min=("duration_min", "first"),
        album_type=("album_type", "first"),
        total_tracks=("total_tracks", "first"),
        is_explicit=("is_explicit", "first"),
        first_appearance=("date", "min"),
        last_appearance=("date", "max"),
    ).reset_index()

    # Rank volatility is NaN for songs that appeared only once
    stats["rank_volatility"] = stats["rank_volatility"].fillna(0).round(2)
    stats["popularity_std"] = stats["popularity_std"].fillna(0).round(2)
    stats["avg_rank"] = stats["avg_rank"].round(2)
    stats["avg_popularity"] = stats["avg_popularity"].round(1)

    # Popularity trend score: difference between last-week avg popularity and first-week avg
    def _pop_trend(name):
        sub = df[(df["song"] == name[0]) & (df["artist"] == name[1])].sort_values("date")
        if len(sub) < 2:
            return 0.0
        first_week = sub.head(min(7, len(sub)))["popularity"].mean()
        last_week = sub.tail(min(7, len(sub)))["popularity"].mean()
        return round(last_week - first_week, 1)

    stats["popularity_trend_score"] = [
        _pop_trend((row.song, row.artist)) for row in stats.itertuples()
    ]

    # Lifespan in calendar days
    stats["lifespan_days"] = (stats["last_appearance"] - stats["first_appearance"]).dt.days

    return stats.sort_values("days_on_chart", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Artist-level aggregation
# ---------------------------------------------------------------------------

def _split_artists(artist_str: str) -> list[str]:
    """Split collaborative artist strings into individual names."""
    # Handle common separators: &, feat., ft., ","
    parts = re.split(r"\s*(?:&|feat\.|ft\.|,)\s*", artist_str, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def build_artist_stats(df: pd.DataFrame) -> pd.DataFrame:
    """One row per individual artist (collaborations credited to each)."""
    rows = []
    for _, r in df.iterrows():
        for artist in _split_artists(r["artist"]):
            rows.append({
                "artist": artist,
                "date": r["date"],
                "position": r["position"],
                "song": r["song"],
                "popularity": r["popularity"],
                "is_explicit": r["is_explicit"],
            })
    expanded = pd.DataFrame(rows)

    grp = expanded.groupby("artist")
    stats = grp.agg(
        unique_songs=("song", "nunique"),
        total_appearances=("date", "size"),
        total_chart_days=("date", "nunique"),
        avg_rank=("position", "mean"),
        best_rank=("position", "min"),
        avg_popularity=("popularity", "mean"),
        max_popularity=("popularity", "max"),
        explicit_pct=("is_explicit", "mean"),
    ).reset_index()

    stats["avg_rank"] = stats["avg_rank"].round(2)
    stats["avg_popularity"] = stats["avg_popularity"].round(1)
    stats["explicit_pct"] = (100 * stats["explicit_pct"]).round(1)

    # Artist dominance index: total chart appearances / total available slots
    total_slots = expanded["date"].nunique() * 50
    stats["dominance_index"] = (100 * stats["total_appearances"] / total_slots).round(3)

    return stats.sort_values("total_chart_days", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Daily summary for timeline
# ---------------------------------------------------------------------------

def build_daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per date: avg popularity, explicit share, new entries, exits."""
    daily = df.groupby("date").agg(
        avg_popularity=("popularity", "mean"),
        median_popularity=("popularity", "median"),
        avg_duration_min=("duration_min", "mean"),
        explicit_count=("is_explicit", "sum"),
        unique_songs=("song", "nunique"),
    ).reset_index()

    daily["explicit_share_pct"] = (100 * daily["explicit_count"] / 50).round(1)
    daily["avg_popularity"] = daily["avg_popularity"].round(1)

    # New entries and exits per day
    songs_by_date = df.groupby("date")["song"].apply(set)
    dates_sorted = sorted(songs_by_date.index)
    new_entries = {}
    exits = {}
    for i, d in enumerate(dates_sorted):
        if i == 0:
            new_entries[d] = len(songs_by_date[d])
            exits[d] = 0
        else:
            prev = songs_by_date[dates_sorted[i - 1]]
            curr = songs_by_date[d]
            new_entries[d] = len(curr - prev)
            exits[d] = len(prev - curr)

    daily["new_entries"] = daily["date"].map(new_entries).fillna(0).astype(int)
    daily["exits"] = daily["date"].map(exits).fillna(0).astype(int)

    return daily.sort_values("date").reset_index(drop=True)
