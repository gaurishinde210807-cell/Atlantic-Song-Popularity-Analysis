"""
eda.py
======
Exploratory data analysis: generates all figures and summary statistics
for the research paper and dashboard.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import pandas as pd

import config


sns.set_theme(style="whitegrid", palette="muted", font_scale=0.95)
ACCENT = "#2c3e50"
COLORS = ["#2c3e50", "#e74c3c", "#27ae60", "#f39c12", "#8e44ad",
          "#3498db", "#1abc9c", "#d35400"]


def _save(fig, name: str) -> str:
    path = config.FIGURE_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


# ---------------------------------------------------------------------------
# Figure 1: Daily average popularity over time
# ---------------------------------------------------------------------------

def fig_popularity_timeline(daily: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(daily["date"], daily["avg_popularity"], color=ACCENT, linewidth=0.8, alpha=0.5)
    # 7-day rolling average
    rolling = daily["avg_popularity"].rolling(7, min_periods=1).mean()
    ax.plot(daily["date"], rolling, color="#e74c3c", linewidth=1.8, label="7-day rolling avg")
    ax.set_ylabel("Average Popularity Score")
    ax.set_title("Daily Average Popularity of Top 50 Songs", fontsize=13, fontweight="bold")
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    return _save(fig, "popularity_timeline.png")


# ---------------------------------------------------------------------------
# Figure 2: Rank distribution — how long songs stay on chart
# ---------------------------------------------------------------------------

def fig_days_on_chart_distribution(song_stats: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(10, 5))
    bins = range(0, int(song_stats["days_on_chart"].max()) + 10, 5)
    ax.hist(song_stats["days_on_chart"], bins=bins, color=ACCENT, edgecolor="white", alpha=0.85)
    median_days = song_stats["days_on_chart"].median()
    ax.axvline(median_days, color="#e74c3c", linestyle="--", linewidth=1.5,
               label=f"Median: {median_days:.0f} days")
    ax.set_xlabel("Days on Chart")
    ax.set_ylabel("Number of Songs")
    ax.set_title("Distribution of Chart Longevity", fontsize=13, fontweight="bold")
    ax.legend()
    return _save(fig, "days_on_chart_dist.png")


# ---------------------------------------------------------------------------
# Figure 3: Top 15 artists by total chart days
# ---------------------------------------------------------------------------

def fig_artist_dominance(artist_stats: pd.DataFrame) -> str:
    top = artist_stats.nlargest(15, "total_chart_days")
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(top["artist"], top["total_chart_days"], color=ACCENT, edgecolor="white")
    ax.set_xlabel("Total Days on Chart")
    ax.set_title("Top 15 Artists by Chart Presence", fontsize=13, fontweight="bold")
    ax.invert_yaxis()
    for bar, val in zip(bars, top["total_chart_days"]):
        ax.text(val + 2, bar.get_y() + bar.get_height() / 2, str(val),
                va="center", fontsize=9, color="#555")
    return _save(fig, "artist_dominance.png")


# ---------------------------------------------------------------------------
# Figure 4: Popularity vs Rank scatter
# ---------------------------------------------------------------------------

def fig_popularity_vs_rank(df: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(8, 6))
    # Sample if too many points
    sample = df.sample(min(5000, len(df)), random_state=42)
    ax.scatter(sample["position"], sample["popularity"], alpha=0.15, s=8, color=ACCENT)
    # Trend line
    from numpy.polynomial.polynomial import polyfit
    coeffs = polyfit(df["position"], df["popularity"], 1)
    xs = np.linspace(1, 50, 100)
    ax.plot(xs, coeffs[0] + coeffs[1] * xs, color="#e74c3c", linewidth=2,
            label=f"Trend (slope={coeffs[1]:.2f})")
    corr = df["position"].corr(df["popularity"])
    ax.set_xlabel("Playlist Position (1 = Top)")
    ax.set_ylabel("Popularity Score")
    ax.set_title(f"Popularity vs Rank  (r = {corr:.3f})", fontsize=13, fontweight="bold")
    ax.legend()
    return _save(fig, "popularity_vs_rank.png")


# ---------------------------------------------------------------------------
# Figure 5: Explicit vs Non-explicit performance comparison
# ---------------------------------------------------------------------------

def fig_explicit_comparison(df: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = {True: "Explicit", False: "Non-Explicit"}

    # (a) Popularity
    for flag, label in labels.items():
        sub = df[df["is_explicit"] == flag]
        axes[0].hist(sub["popularity"], bins=30, alpha=0.55, label=label,
                     color=COLORS[1] if flag else COLORS[0])
    axes[0].set_xlabel("Popularity Score")
    axes[0].set_ylabel("Frequency")
    axes[0].set_title("Popularity Distribution")
    axes[0].legend()

    # (b) Rank
    for flag, label in labels.items():
        sub = df[df["is_explicit"] == flag]
        axes[1].hist(sub["position"], bins=25, alpha=0.55, label=label,
                     color=COLORS[1] if flag else COLORS[0])
    axes[1].set_xlabel("Playlist Position")
    axes[1].set_ylabel("Frequency")
    axes[1].set_title("Rank Distribution")
    axes[1].legend()

    fig.suptitle("Explicit vs Non-Explicit Song Performance", fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    return _save(fig, "explicit_comparison.png")


# ---------------------------------------------------------------------------
# Figure 6: Album type breakdown (single vs album vs compilation)
# ---------------------------------------------------------------------------

def fig_album_type_performance(df: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    type_stats = df.groupby("album_type").agg(
        count=("song", "size"),
        avg_pop=("popularity", "mean"),
        avg_rank=("position", "mean"),
    ).reset_index()

    axes[0].bar(type_stats["album_type"], type_stats["avg_pop"], color=COLORS[:len(type_stats)],
                edgecolor="white")
    axes[0].set_ylabel("Average Popularity Score")
    axes[0].set_title("Avg Popularity by Album Type")

    axes[1].bar(type_stats["album_type"], type_stats["avg_rank"], color=COLORS[:len(type_stats)],
                edgecolor="white")
    axes[1].set_ylabel("Average Rank (lower = better)")
    axes[1].set_title("Avg Rank by Album Type")
    axes[1].invert_yaxis()

    fig.suptitle("Performance by Album Type", fontsize=13, fontweight="bold", y=1.02)
    fig.tight_layout()
    return _save(fig, "album_type_performance.png")


# ---------------------------------------------------------------------------
# Figure 7: New entries and exits over time
# ---------------------------------------------------------------------------

def fig_entry_exit_timeline(daily: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(12, 4))
    roll_new = daily["new_entries"].rolling(7, min_periods=1).mean()
    roll_exit = daily["exits"].rolling(7, min_periods=1).mean()
    ax.plot(daily["date"], roll_new, color="#27ae60", linewidth=1.5, label="New entries (7d avg)")
    ax.plot(daily["date"], roll_exit, color="#e74c3c", linewidth=1.5, label="Exits (7d avg)")
    ax.set_ylabel("Songs per Day")
    ax.set_title("Playlist Turnover: New Entries vs Exits", fontsize=13, fontweight="bold")
    ax.legend()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    return _save(fig, "entry_exit_timeline.png")


# ---------------------------------------------------------------------------
# Figure 8: Top 20 songs by chart longevity
# ---------------------------------------------------------------------------

def fig_top_songs_longevity(song_stats: pd.DataFrame) -> str:
    top = song_stats.nlargest(20, "days_on_chart")
    fig, ax = plt.subplots(figsize=(10, 7))
    labels = [f"{r.song}\n({r.artist[:25]})" for r in top.itertuples()]
    bars = ax.barh(range(len(top)), top["days_on_chart"], color=ACCENT, edgecolor="white")
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Days on Chart")
    ax.set_title("Top 20 Songs by Chart Longevity", fontsize=13, fontweight="bold")
    ax.invert_yaxis()
    for bar, val in zip(bars, top["days_on_chart"]):
        ax.text(val + 1, bar.get_y() + bar.get_height() / 2, str(val),
                va="center", fontsize=8, color="#555")
    fig.tight_layout()
    return _save(fig, "top_songs_longevity.png")


# ---------------------------------------------------------------------------
# Figure 9: Duration vs popularity scatter
# ---------------------------------------------------------------------------

def fig_duration_vs_popularity(song_stats: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(song_stats["avg_duration_min"], song_stats["avg_popularity"],
               alpha=0.4, s=15, color=ACCENT)
    corr = song_stats["avg_duration_min"].corr(song_stats["avg_popularity"])
    ax.set_xlabel("Song Duration (minutes)")
    ax.set_ylabel("Average Popularity Score")
    ax.set_title(f"Duration vs Popularity  (r = {corr:.3f})", fontsize=13, fontweight="bold")
    return _save(fig, "duration_vs_popularity.png")


# ---------------------------------------------------------------------------
# Figure 10: Monthly explicit content share
# ---------------------------------------------------------------------------

def fig_explicit_share_trend(df: pd.DataFrame) -> str:
    monthly = df.copy()
    monthly["month"] = monthly["date"].dt.to_period("M")
    m_stats = monthly.groupby("month").agg(
        explicit_pct=("is_explicit", "mean"),
    ).reset_index()
    m_stats["explicit_pct"] = (100 * m_stats["explicit_pct"]).round(1)
    m_stats["month_dt"] = m_stats["month"].dt.to_timestamp()

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(m_stats["month_dt"], m_stats["explicit_pct"], width=20, color=ACCENT, alpha=0.8)
    ax.set_ylabel("Explicit Content (%)")
    ax.set_title("Monthly Explicit Content Share in Top 50", fontsize=13, fontweight="bold")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    fig.autofmt_xdate()
    return _save(fig, "explicit_share_trend.png")


# ---------------------------------------------------------------------------
# Run all
# ---------------------------------------------------------------------------

def run_eda(df: pd.DataFrame, song_stats: pd.DataFrame,
            artist_stats: pd.DataFrame, daily: pd.DataFrame) -> dict:
    """Generate all figures and return a summary dict."""
    figures = {}
    figures["popularity_timeline"] = fig_popularity_timeline(daily)
    figures["days_on_chart_dist"] = fig_days_on_chart_distribution(song_stats)
    figures["artist_dominance"] = fig_artist_dominance(artist_stats)
    figures["popularity_vs_rank"] = fig_popularity_vs_rank(df)
    figures["explicit_comparison"] = fig_explicit_comparison(df)
    figures["album_type_performance"] = fig_album_type_performance(df)
    figures["entry_exit_timeline"] = fig_entry_exit_timeline(daily)
    figures["top_songs_longevity"] = fig_top_songs_longevity(song_stats)
    figures["duration_vs_popularity"] = fig_duration_vs_popularity(song_stats)
    figures["explicit_share_trend"] = fig_explicit_share_trend(df)

    summary = {
        "figures": figures,
        "total_songs": int(df["song"].nunique()),
        "total_artists": int(df["artist"].nunique()),
        "total_snapshots": int(df["date"].nunique()),
        "date_range": f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}",
        "avg_popularity": round(float(df["popularity"].mean()), 1),
        "median_days_on_chart": int(song_stats["days_on_chart"].median()),
        "max_days_on_chart": int(song_stats["days_on_chart"].max()),
        "explicit_share_pct": round(100 * float(df["is_explicit"].mean()), 1),
        "pop_rank_correlation": round(float(df["position"].corr(df["popularity"])), 3),
    }
    return summary
