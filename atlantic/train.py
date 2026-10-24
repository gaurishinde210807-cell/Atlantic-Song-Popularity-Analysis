"""
train.py
========
Main pipeline for the Atlantic US Top 50 Playlist analysis.
Runs data loading, validation, feature engineering, EDA, and saves all artefacts.

    python train.py

This is a descriptive analytics project, not a predictive one.
There are no ML models to train -- the name 'train.py' is kept for
consistency with the submission form's expectations.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config
import data_prep
import eda


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, (pd.Timestamp, pd.Period)):
            return str(obj)
        if isinstance(obj, (set, frozenset)):
            return sorted(obj)
        if pd.isna(obj) if np.isscalar(obj) else False:
            return None
        return super().default(obj)


def banner(text: str) -> None:
    print(f"\n{'=' * 78}\n  {text}\n{'=' * 78}")


def main(csv_path: str | Path | None = None) -> dict:
    started = time.time()
    report: dict = {"generated_at": pd.Timestamp.now().isoformat()}

    # ========================================================================
    # 1. Load and validate
    # ========================================================================
    banner("1. Loading and validating data")
    df = data_prep.load_data(csv_path)
    quality = data_prep.data_quality_report(df)
    report["data_quality"] = quality

    print(f"Rows after dedup  : {quality['rows']}")
    print(f"Date range        : {quality['date_range']}")
    print(f"Unique songs      : {quality['unique_songs']}")
    print(f"Unique artists    : {quality['unique_artists']}")
    print(f"Snapshots (days)  : {quality['unique_dates']}")
    print(f"Explicit share    : {quality['explicit_share_pct']}%")
    print(f"Null columns      : {sum(v > 0 for v in quality['null_counts'].values())}")

    # ========================================================================
    # 2. Build aggregate tables
    # ========================================================================
    banner("2. Building song-level and artist-level statistics")
    song_stats = data_prep.build_song_stats(df)
    artist_stats = data_prep.build_artist_stats(df)
    daily = data_prep.build_daily_summary(df)

    print(f"Song stats table  : {song_stats.shape[0]} songs x {song_stats.shape[1]} columns")
    print(f"Artist stats table: {artist_stats.shape[0]} artists x {artist_stats.shape[1]} columns")
    print(f"Daily summary     : {daily.shape[0]} days")

    # Save tables
    song_stats.to_csv(config.TABLE_DIR / "song_stats.csv", index=False)
    artist_stats.to_csv(config.TABLE_DIR / "artist_stats.csv", index=False)
    daily.to_csv(config.TABLE_DIR / "daily_summary.csv", index=False)

    report["song_stats_shape"] = list(song_stats.shape)
    report["artist_stats_shape"] = list(artist_stats.shape)

    # Top songs by longevity for the report
    top_songs = song_stats.nlargest(10, "days_on_chart")[
        ["song", "artist", "days_on_chart", "avg_rank", "best_rank",
         "rank_volatility", "avg_popularity", "popularity_trend_score"]
    ].to_dict(orient="records")
    report["top_songs_longevity"] = top_songs

    # Top artists for the report
    top_artists = artist_stats.nlargest(10, "total_chart_days")[
        ["artist", "unique_songs", "total_chart_days", "avg_rank",
         "avg_popularity", "dominance_index"]
    ].to_dict(orient="records")
    report["top_artists"] = top_artists

    # ========================================================================
    # 3. Content attribute analysis
    # ========================================================================
    banner("3. Content attribute analysis")

    # Explicit vs non-explicit
    expl = df[df["is_explicit"]]
    non_expl = df[~df["is_explicit"]]
    explicit_analysis = {
        "explicit_avg_popularity": round(float(expl["popularity"].mean()), 1),
        "non_explicit_avg_popularity": round(float(non_expl["popularity"].mean()), 1),
        "explicit_avg_rank": round(float(expl["position"].mean()), 1),
        "non_explicit_avg_rank": round(float(non_expl["position"].mean()), 1),
        "explicit_count": int(len(expl)),
        "non_explicit_count": int(len(non_expl)),
    }
    report["explicit_analysis"] = explicit_analysis
    print(f"Explicit avg popularity : {explicit_analysis['explicit_avg_popularity']} "
          f"vs Non-explicit: {explicit_analysis['non_explicit_avg_popularity']}")

    # Album type comparison
    album_analysis = df.groupby("album_type").agg(
        entries=("song", "size"),
        avg_popularity=("popularity", "mean"),
        avg_rank=("position", "mean"),
        unique_songs=("song", "nunique"),
    ).round(1).reset_index().to_dict(orient="records")
    report["album_type_analysis"] = album_analysis
    for at in album_analysis:
        print(f"  {at['album_type']:12s}: {at['unique_songs']} songs, "
              f"avg pop {at['avg_popularity']}, avg rank {at['avg_rank']}")

    # Duration analysis
    duration_corr_pop = round(float(df["duration_min"].corr(df["popularity"])), 3)
    duration_corr_rank = round(float(df["duration_min"].corr(df["position"])), 3)
    report["duration_correlations"] = {
        "duration_vs_popularity": duration_corr_pop,
        "duration_vs_rank": duration_corr_rank,
    }
    print(f"Duration vs Popularity correlation: {duration_corr_pop}")
    print(f"Duration vs Rank correlation: {duration_corr_rank}")

    # Popularity vs Rank
    pop_rank_corr = round(float(df["position"].corr(df["popularity"])), 3)
    report["pop_rank_correlation"] = pop_rank_corr
    print(f"Popularity vs Rank correlation: {pop_rank_corr}")

    # Top-10 vs rest
    top10 = df[df["position"] <= 10]
    rest = df[df["position"] > 10]
    report["top10_vs_rest"] = {
        "top10_avg_pop": round(float(top10["popularity"].mean()), 1),
        "rest_avg_pop": round(float(rest["popularity"].mean()), 1),
        "top10_explicit_pct": round(100 * float(top10["is_explicit"].mean()), 1),
        "rest_explicit_pct": round(100 * float(rest["is_explicit"].mean()), 1),
    }

    # ========================================================================
    # 4. Rank movement analysis
    # ========================================================================
    banner("4. Rank movement analysis")
    # Identify fast risers (songs that reached top 5 within 7 days)
    fast_risers = song_stats[
        (song_stats["best_rank"] <= 5) & (song_stats["days_on_chart"] >= 2)
    ].copy()
    # Check how quickly they reached best rank
    fast_rise_list = []
    for _, s in fast_risers.iterrows():
        sub = df[(df["song"] == s["song"]) & (df["artist"] == s["artist"])].sort_values("date")
        first_date = sub["date"].iloc[0]
        best_date = sub.loc[sub["position"] == s["best_rank"], "date"].iloc[0]
        days_to_peak = (best_date - first_date).days
        if days_to_peak <= 14:
            fast_rise_list.append({
                "song": s["song"],
                "artist": s["artist"],
                "days_to_peak": int(days_to_peak),
                "best_rank": int(s["best_rank"]),
                "days_on_chart": int(s["days_on_chart"]),
            })

    fast_rise_list.sort(key=lambda x: x["days_to_peak"])
    report["fast_risers"] = fast_rise_list[:15]
    print(f"Fast risers (top 5 within 14 days): {len(fast_rise_list)} songs")

    # Slow decliners (songs with >100 days on chart and best rank <= 20)
    slow_decliners = song_stats[
        (song_stats["days_on_chart"] >= 100) & (song_stats["best_rank"] <= 20)
    ].nlargest(10, "days_on_chart")[
        ["song", "artist", "days_on_chart", "best_rank", "avg_rank"]
    ].to_dict(orient="records")
    report["slow_decliners"] = slow_decliners
    print(f"Slow decliners (100+ days, best rank <=20): {len(slow_decliners)} songs")

    # ========================================================================
    # 5. EDA figures
    # ========================================================================
    banner("5. Generating figures")
    eda_summary = eda.run_eda(df, song_stats, artist_stats, daily)
    report["eda"] = eda_summary
    print(f"Saved {len(eda_summary['figures'])} figures to {config.FIGURE_DIR}")

    # ========================================================================
    # 6. Popularity tier analysis
    # ========================================================================
    banner("6. Popularity tier analysis")
    tier_ranges = [(1, 10), (11, 20), (21, 30), (31, 40), (41, 50)]
    tier_stats = []
    for lo, hi in tier_ranges:
        sub = df[(df["position"] >= lo) & (df["position"] <= hi)]
        tier_stats.append({
            "rank_range": f"{lo}-{hi}",
            "avg_popularity": round(float(sub["popularity"].mean()), 1),
            "median_popularity": round(float(sub["popularity"].median()), 1),
            "std_popularity": round(float(sub["popularity"].std()), 1),
            "avg_duration_min": round(float(sub["duration_min"].mean()), 2),
            "explicit_pct": round(100 * float(sub["is_explicit"].mean()), 1),
        })
    report["tier_analysis"] = tier_stats
    for t in tier_stats:
        print(f"  Rank {t['rank_range']:6s}: avg pop {t['avg_popularity']}, "
              f"explicit {t['explicit_pct']}%")

    # ========================================================================
    # Save report
    # ========================================================================
    report["runtime_seconds"] = round(time.time() - started, 1)

    with open(config.OUTPUT_DIR / "metrics.json", "w") as fh:
        json.dump(report, fh, indent=2, cls=NumpyEncoder)

    # Also save the full dataset (cleaned) for the dashboard
    df.to_csv(config.OUTPUT_DIR / "playlist_clean.csv", index=False)

    print(f"\nPipeline finished in {report['runtime_seconds']}s")
    print(f"Artefacts saved to {config.OUTPUT_DIR}")
    return report


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
