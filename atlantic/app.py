"""
app.py
======
Streamlit dashboard for the Atlantic US Top 50 Playlist analysis.

Modules:
  1. Overview — KPIs, timeline, key stats
  2. Song Ranking Trends — individual song trajectory charts
  3. Artist Dominance Leaderboard — artist chart presence and performance
  4. Popularity vs Rank — scatter plots and tier analysis
  5. Explicit vs Non-Explicit — content attribute performance panels
  6. Playlist Timeline Explorer — daily snapshot with filters

    streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import config

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="US Top 50 Playlist Analytics",
    page_icon="🎵",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data
def load_data():
    df = pd.read_csv(config.OUTPUT_DIR / "playlist_clean.csv", parse_dates=["date"])
    return df

@st.cache_data
def load_song_stats():
    return pd.read_csv(config.TABLE_DIR / "song_stats.csv",
                       parse_dates=["first_appearance", "last_appearance"])

@st.cache_data
def load_artist_stats():
    return pd.read_csv(config.TABLE_DIR / "artist_stats.csv")

@st.cache_data
def load_daily():
    return pd.read_csv(config.TABLE_DIR / "daily_summary.csv", parse_dates=["date"])

@st.cache_data
def load_metrics():
    with open(config.OUTPUT_DIR / "metrics.json") as f:
        return json.load(f)


df = load_data()
song_stats = load_song_stats()
artist_stats = load_artist_stats()
daily = load_daily()
metrics = load_metrics()


# ---------------------------------------------------------------------------
# Sidebar navigation and global filters
# ---------------------------------------------------------------------------
st.sidebar.title("US Top 50 Playlist Analytics")
st.sidebar.markdown("**Atlantic Recording Corp.**")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Song Ranking Trends", "Artist Dominance",
     "Popularity vs Rank", "Explicit vs Non-Explicit",
     "Playlist Timeline Explorer"],
)

st.sidebar.markdown("---")

# Global filters
date_min = df["date"].min().date()
date_max = df["date"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max,
)

if len(date_range) == 2:
    mask = (df["date"].dt.date >= date_range[0]) & (df["date"].dt.date <= date_range[1])
    df_filtered = df[mask]
else:
    df_filtered = df

rank_range = st.sidebar.slider("Rank range", 1, 50, (1, 50))
df_filtered = df_filtered[
    (df_filtered["position"] >= rank_range[0]) &
    (df_filtered["position"] <= rank_range[1])
]

album_types = st.sidebar.multiselect(
    "Album type",
    options=sorted(df["album_type"].unique()),
    default=sorted(df["album_type"].unique()),
)
if album_types:
    df_filtered = df_filtered[df_filtered["album_type"].isin(album_types)]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def kpi_row(cols_data: list[tuple[str, str]]):
    cols = st.columns(len(cols_data))
    for col, (label, value) in zip(cols, cols_data):
        col.metric(label, value)


# =====================================================================
# PAGE: Overview
# =====================================================================
if page == "Overview":
    st.title("US Top 50 Playlist — Overview")
    st.caption(f"Data: {metrics['data_quality']['date_range']}")

    kpi_row([
        ("Total Songs", f"{metrics['data_quality']['unique_songs']:,}"),
        ("Total Artists", f"{metrics['data_quality']['unique_artists']:,}"),
        ("Daily Snapshots", f"{metrics['data_quality']['unique_dates']:,}"),
        ("Avg Popularity", f"{metrics['eda']['avg_popularity']}"),
        ("Explicit Share", f"{metrics['data_quality']['explicit_share_pct']}%"),
    ])

    st.markdown("---")

    # Popularity timeline
    st.subheader("Popularity Trend Over Time")
    daily_plot = daily.copy()
    daily_plot["rolling_avg"] = daily_plot["avg_popularity"].rolling(7, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily_plot["date"], y=daily_plot["avg_popularity"],
                             mode="lines", name="Daily avg", opacity=0.3,
                             line=dict(color="#2c3e50")))
    fig.add_trace(go.Scatter(x=daily_plot["date"], y=daily_plot["rolling_avg"],
                             mode="lines", name="7-day rolling avg",
                             line=dict(color="#e74c3c", width=2)))
    fig.update_layout(yaxis_title="Average Popularity", height=350,
                      margin=dict(l=40, r=20, t=20, b=30))
    st.plotly_chart(fig, width="stretch")

    # Entry/exit chart
    st.subheader("Playlist Turnover")
    daily_plot["roll_new"] = daily_plot["new_entries"].rolling(7, min_periods=1).mean()
    daily_plot["roll_exit"] = daily_plot["exits"].rolling(7, min_periods=1).mean()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=daily_plot["date"], y=daily_plot["roll_new"],
                              mode="lines", name="New entries (7d avg)",
                              line=dict(color="#27ae60")))
    fig2.add_trace(go.Scatter(x=daily_plot["date"], y=daily_plot["roll_exit"],
                              mode="lines", name="Exits (7d avg)",
                              line=dict(color="#e74c3c")))
    fig2.update_layout(yaxis_title="Songs per day", height=300,
                       margin=dict(l=40, r=20, t=20, b=30))
    st.plotly_chart(fig2, width="stretch")

    # Top songs table
    st.subheader("Top 10 Songs by Chart Longevity")
    top10_songs = song_stats.nlargest(10, "days_on_chart")[
        ["song", "artist", "days_on_chart", "avg_rank", "best_rank",
         "rank_volatility", "avg_popularity"]
    ].reset_index(drop=True)
    top10_songs.index += 1
    st.dataframe(top10_songs, width="stretch")


# =====================================================================
# PAGE: Song Ranking Trends
# =====================================================================
elif page == "Song Ranking Trends":
    st.title("Song Ranking Trends")

    # Song filter
    all_songs = sorted(df_filtered["song"].unique())
    selected_songs = st.multiselect(
        "Select songs to compare (up to 5)",
        options=all_songs,
        default=all_songs[:3] if len(all_songs) >= 3 else all_songs[:1],
        max_selections=5,
    )

    if selected_songs:
        fig = go.Figure()
        for song in selected_songs:
            sub = df_filtered[df_filtered["song"] == song].sort_values("date")
            artist = sub["artist"].iloc[0]
            fig.add_trace(go.Scatter(
                x=sub["date"], y=sub["position"],
                mode="lines+markers", name=f"{song} ({artist[:20]})",
                marker=dict(size=4),
            ))
        fig.update_layout(
            yaxis=dict(title="Rank", autorange="reversed"),
            height=450,
            margin=dict(l=40, r=20, t=20, b=30),
        )
        st.plotly_chart(fig, width="stretch")

        # Stats table for selected songs
        sel_stats = song_stats[song_stats["song"].isin(selected_songs)][
            ["song", "artist", "days_on_chart", "avg_rank", "best_rank",
             "rank_volatility", "avg_popularity", "popularity_trend_score"]
        ].reset_index(drop=True)
        st.dataframe(sel_stats, width="stretch")
    else:
        st.info("Select at least one song above to see its ranking trajectory.")

    # Longevity chart
    st.subheader("Top 20 Songs by Days on Chart")
    top20 = song_stats.nlargest(20, "days_on_chart")
    fig2 = px.bar(top20, y="song", x="days_on_chart", orientation="h",
                  color="avg_popularity", color_continuous_scale="RdYlGn",
                  hover_data=["artist", "best_rank"])
    fig2.update_layout(yaxis=dict(autorange="reversed"), height=600,
                       margin=dict(l=10, r=20, t=20, b=30))
    st.plotly_chart(fig2, width="stretch")


# =====================================================================
# PAGE: Artist Dominance
# =====================================================================
elif page == "Artist Dominance":
    st.title("Artist Dominance Leaderboard")

    sort_by = st.selectbox("Sort by", ["total_chart_days", "unique_songs",
                                        "avg_popularity", "dominance_index"])
    top_n = st.slider("Show top N artists", 5, 50, 20)

    top = artist_stats.nlargest(top_n, sort_by)

    fig = px.bar(top, y="artist", x=sort_by, orientation="h",
                 color="avg_popularity", color_continuous_scale="Viridis",
                 hover_data=["unique_songs", "total_chart_days", "dominance_index"])
    fig.update_layout(yaxis=dict(autorange="reversed"), height=max(400, top_n * 25),
                      margin=dict(l=10, r=20, t=20, b=30))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Full Leaderboard")
    display_cols = ["artist", "unique_songs", "total_chart_days", "avg_rank",
                    "best_rank", "avg_popularity", "dominance_index", "explicit_pct"]
    st.dataframe(top[display_cols].reset_index(drop=True), width="stretch")


# =====================================================================
# PAGE: Popularity vs Rank
# =====================================================================
elif page == "Popularity vs Rank":
    st.title("Popularity vs Rank Analysis")

    corr = metrics.get("pop_rank_correlation", "N/A")
    st.info(f"Overall correlation between playlist position and popularity score: **r = {corr}**")

    # Scatter
    sample_size = min(5000, len(df_filtered))
    sample = df_filtered.sample(sample_size, random_state=42) if len(df_filtered) > sample_size else df_filtered
    fig = px.scatter(sample, x="position", y="popularity",
                     color="is_explicit", opacity=0.3,
                     hover_data=["song", "artist", "date"],
                     color_discrete_map={True: "#e74c3c", False: "#2c3e50"})
    fig.update_layout(xaxis_title="Playlist Position (1 = Top)",
                      yaxis_title="Popularity Score", height=450)
    st.plotly_chart(fig, width="stretch")

    # Tier analysis
    st.subheader("Performance by Rank Tier")
    tier_data = metrics.get("tier_analysis", [])
    if tier_data:
        tier_df = pd.DataFrame(tier_data)
        st.dataframe(tier_df, width="stretch")

    # Popularity stability
    st.subheader("Songs with Highest Popularity Stability")
    stable = song_stats[song_stats["days_on_chart"] >= 10].nsmallest(10, "popularity_std")[
        ["song", "artist", "days_on_chart", "avg_popularity", "popularity_std"]
    ].reset_index(drop=True)
    st.dataframe(stable, width="stretch")


# =====================================================================
# PAGE: Explicit vs Non-Explicit
# =====================================================================
elif page == "Explicit vs Non-Explicit":
    st.title("Explicit vs Non-Explicit Performance")

    ea = metrics.get("explicit_analysis", {})
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Explicit Avg Popularity", ea.get("explicit_avg_popularity", "N/A"))
        st.metric("Explicit Avg Rank", ea.get("explicit_avg_rank", "N/A"))
        st.metric("Explicit Entries", f"{ea.get('explicit_count', 0):,}")
    with col2:
        st.metric("Non-Explicit Avg Popularity", ea.get("non_explicit_avg_popularity", "N/A"))
        st.metric("Non-Explicit Avg Rank", ea.get("non_explicit_avg_rank", "N/A"))
        st.metric("Non-Explicit Entries", f"{ea.get('non_explicit_count', 0):,}")

    st.markdown("---")

    # Side-by-side histograms
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Popularity Distribution")
        fig = go.Figure()
        for flag, label, color in [(True, "Explicit", "#e74c3c"), (False, "Non-Explicit", "#2c3e50")]:
            sub = df_filtered[df_filtered["is_explicit"] == flag]
            fig.add_trace(go.Histogram(x=sub["popularity"], name=label,
                                        opacity=0.6, marker_color=color, nbinsx=30))
        fig.update_layout(barmode="overlay", height=350)
        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Rank Distribution")
        fig2 = go.Figure()
        for flag, label, color in [(True, "Explicit", "#e74c3c"), (False, "Non-Explicit", "#2c3e50")]:
            sub = df_filtered[df_filtered["is_explicit"] == flag]
            fig2.add_trace(go.Histogram(x=sub["position"], name=label,
                                         opacity=0.6, marker_color=color, nbinsx=25))
        fig2.update_layout(barmode="overlay", height=350)
        st.plotly_chart(fig2, width="stretch")

    # Monthly explicit share trend
    st.subheader("Monthly Explicit Content Share")
    monthly = df_filtered.copy()
    monthly["month"] = monthly["date"].dt.to_period("M").astype(str)
    m_explicit = monthly.groupby("month")["is_explicit"].mean().reset_index()
    m_explicit["pct"] = (100 * m_explicit["is_explicit"]).round(1)
    fig3 = px.bar(m_explicit, x="month", y="pct",
                  labels={"pct": "Explicit %", "month": "Month"})
    fig3.update_layout(height=300)
    st.plotly_chart(fig3, width="stretch")

    # Album type comparison
    st.subheader("Album Type Performance")
    at_data = metrics.get("album_type_analysis", [])
    if at_data:
        st.dataframe(pd.DataFrame(at_data), width="stretch")


# =====================================================================
# PAGE: Playlist Timeline Explorer
# =====================================================================
elif page == "Playlist Timeline Explorer":
    st.title("Playlist Timeline Explorer")
    st.caption("Browse the daily Top 50 snapshot for any date in the dataset.")

    # Artist filter
    all_artists_filt = sorted(df_filtered["artist"].unique())
    artist_filter = st.multiselect("Filter by artist", options=all_artists_filt)

    if artist_filter:
        df_display = df_filtered[df_filtered["artist"].isin(artist_filter)]
    else:
        df_display = df_filtered

    # Date picker
    available_dates = sorted(df_display["date"].dt.date.unique())
    if available_dates:
        selected_date = st.select_slider(
            "Select date",
            options=available_dates,
            value=available_dates[-1],
        )

        snapshot = df_display[df_display["date"].dt.date == selected_date].sort_values("position")
        st.subheader(f"Top 50 Snapshot — {selected_date}")
        st.dataframe(
            snapshot[["position", "song", "artist", "popularity", "duration_min",
                      "album_type", "is_explicit"]].reset_index(drop=True),
            width="stretch",
            height=600,
        )

        # Song trajectory from this date's songs
        st.subheader("Track a Song's Full Journey")
        songs_today = snapshot["song"].tolist()
        track_song = st.selectbox("Pick a song from this date", songs_today)
        if track_song:
            track_data = df[(df["song"] == track_song)].sort_values("date")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=track_data["date"], y=track_data["position"],
                mode="lines+markers", marker=dict(size=5),
                line=dict(color="#2c3e50"),
            ))
            fig.update_layout(yaxis=dict(title="Rank", autorange="reversed"),
                              xaxis_title="Date", height=300)
            st.plotly_chart(fig, width="stretch")
    else:
        st.warning("No data matches the current filters.")


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.caption(
    "Gauri Shinde · Second-year CS, University of Greenwich\n\n"
    "Atlantic Recording Corp. · US Top 50 Playlist Analysis"
)
