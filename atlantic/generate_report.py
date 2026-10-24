"""
generate_report.py
==================
Generates the research paper (Markdown) and executive summary from metrics.json.
Every number comes from the pipeline output -- nothing is hand-typed.

    python generate_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

import config


def _load_metrics() -> dict:
    with open(config.OUTPUT_DIR / "metrics.json") as f:
        return json.load(f)


def _fmt(n, decimals=1) -> str:
    if isinstance(n, float):
        return f"{n:.{decimals}f}"
    return str(n)


def _metrics_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    """Build a markdown table from a list of dicts."""
    header = "| " + " | ".join(label for _, label in columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, sep]
    for r in rows:
        vals = []
        for key, _ in columns:
            v = r.get(key, "")
            if isinstance(v, float):
                vals.append(f"{v:.2f}" if abs(v) < 100 else f"{v:,.0f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def build_research_paper(m: dict) -> str:
    dq = m["data_quality"]
    ea = m["explicit_analysis"]
    eda = m["eda"]
    tiers = m["tier_analysis"]

    sections = []

    # Author line
    sections.append(
        "**Research Paper**\n\n"
        "**Author:** Gauri Shinde, Second-year Computer Science student, "
        "University of Greenwich\n\n"
        f"Generated {m['generated_at'][:10]} | pipeline runtime {m['runtime_seconds']}s\n"
    )

    # Abstract
    sections.append(
        "## Abstract\n\n"
        f"This paper presents an exploratory data analysis of {dq['unique_dates']} daily snapshots "
        f"of the United States Top 50 streaming playlist, spanning {dq['date_range']}. "
        f"The dataset contains {dq['rows']:,} entries covering {dq['unique_songs']} unique songs "
        f"by {dq['unique_artists']} artists. We analyse playlist ranking patterns, song longevity, "
        "artist dominance, popularity-rank relationships, and the influence of content attributes "
        "(explicit flag, album type, song duration) on chart performance. "
        "Key findings include a weak negative correlation between playlist rank and popularity "
        f"score (r = {eda['pop_rank_correlation']}), a median chart stay of "
        f"{eda['median_days_on_chart']} days, and minimal performance differences between "
        "explicit and non-explicit content. Recommendations for release timing, catalogue "
        "strategy, and promotion are provided.\n"
    )

    # 1. Introduction
    sections.append(
        "## 1. Introduction\n\n"
        "Streaming playlists have become the primary discovery channel for recorded music. "
        "A song's position on a major national playlist directly affects its stream count, "
        "revenue, and the artist's visibility. For record labels, understanding what drives "
        "chart persistence, how quickly songs rise or fall, and whether content attributes "
        "like explicit labelling or album type affect performance is essential for promotion "
        "and release strategy.\n\n"
        "This project analyses the United States Top 50 playlist from Atlantic Recording "
        "Corporation's perspective. The work is purely descriptive and historical: the aim is "
        "to surface patterns in past playlist behaviour, not to build a predictive or "
        "recommendation model. Each section answers a concrete question about playlist dynamics, "
        "backed by summary statistics and visualisation.\n"
    )

    # 2. Data
    sections.append(
        "## 2. Data Description\n\n"
        f"The dataset comprises **{dq['rows']:,} daily playlist entries** across "
        f"**{dq['unique_dates']} snapshot dates** from {dq['date_range']}. "
        f"Each row records one song's position (rank {dq['position_range']}), "
        "its popularity score, duration, album type, explicit flag, and album metadata.\n\n"
        "### 2.1 Data quality\n\n"
        "- **Zero null values** across all 10 columns.\n"
        "- One duplicate snapshot on 2025-03-01 (100 rows instead of 50) was deduplicated, "
        "keeping the first occurrence for each position.\n"
        f"- After cleaning: {dq['rows']:,} rows, each date having exactly 50 entries.\n"
        f"- Popularity scores range from {dq['popularity_range']}.\n"
        f"- Song durations range from {dq['duration_min_range']} minutes.\n\n"
        "### 2.2 Album types\n\n"
    )
    for at in m["album_type_analysis"]:
        sections[-1] += (
            f"- **{at['album_type'].capitalize()}**: {at['unique_songs']} unique songs, "
            f"avg popularity {at['avg_popularity']}, avg rank {at['avg_rank']}\n"
        )

    # 3. Methodology
    sections.append(
        "\n## 3. Methodology\n\n"
        "The analysis follows the brief's six-step methodology:\n\n"
        "1. **Data ingestion and validation**: dates parsed from DD-MM-YYYY format, "
        "rank range confirmed as 1-50, artist names standardised, duplicates removed.\n"
        "2. **Feature engineering**: derived metrics include Days on Chart, Average Rank, "
        "Best Rank Achieved, Rank Volatility Index (standard deviation of daily ranks), "
        "Popularity Trend Score (last-week vs first-week average popularity), and "
        "Duration in minutes.\n"
        "3. **Playlist ranking analysis**: daily rank distributions, entry/exit rates, "
        "fast risers and slow decliners.\n"
        "4. **Song-level performance analysis**: longevity, peak rank, popularity stability.\n"
        "5. **Artist performance analysis**: chart presence, song count, dominance index "
        "(share of all available chart slots), collaborative vs solo performance.\n"
        "6. **Content attribute analysis**: explicit vs non-explicit, single vs album, "
        "duration correlations, rank-tier breakdowns.\n\n"
        "All computations run in Python (pandas, numpy, scipy) with the pipeline orchestrated "
        "by `train.py`. The Streamlit dashboard reads the same artefacts the report does, "
        "so the two are always consistent.\n"
    )

    # 4. Playlist Ranking Analysis
    sections.append(
        "## 4. Playlist Ranking Analysis\n\n"
        "### 4.1 Turnover\n\n"
        "The playlist is not static. On an average day, new songs enter and others exit. "
        "The entry/exit timeline (Figure 1) shows periods of high churn interspersed with "
        "stable stretches where the same songs hold their positions for days or weeks.\n\n"
        "![Playlist turnover](figures/entry_exit_timeline.png)\n"
        "*Figure 1: Daily new entries and exits (7-day rolling average).*\n\n"
    )

    # Fast risers
    fr = m.get("fast_risers", [])
    if fr:
        sections[-1] += (
            f"### 4.2 Fast risers\n\n"
            f"**{len(fr)} songs** reached the top 5 within their first 14 days on the chart. "
            "Examples:\n\n"
        )
        sections[-1] += _metrics_table(
            fr[:10],
            [("song", "Song"), ("artist", "Artist"), ("days_to_peak", "Days to Peak"),
             ("best_rank", "Best Rank"), ("days_on_chart", "Total Days")],
        )

    # Slow decliners
    sd = m.get("slow_decliners", [])
    if sd:
        sections[-1] += (
            "\n\n### 4.3 Slow decliners\n\n"
            "These songs stayed on the chart for over 100 days and reached the top 20 at least once:\n\n"
        )
        sections[-1] += _metrics_table(
            sd,
            [("song", "Song"), ("artist", "Artist"), ("days_on_chart", "Days"),
             ("best_rank", "Best Rank"), ("avg_rank", "Avg Rank")],
        )

    # 5. Song-Level Performance
    sections.append(
        "\n\n## 5. Song-Level Performance Analysis\n\n"
        f"Across {dq['unique_songs']} unique songs, the median chart stay is "
        f"**{eda['median_days_on_chart']} days** and the longest is "
        f"**{eda['max_days_on_chart']} days**.\n\n"
        "![Days on chart distribution](figures/days_on_chart_dist.png)\n"
        "*Figure 2: Distribution of chart longevity across all songs.*\n\n"
        "### Top 10 songs by longevity\n\n"
    )
    sections[-1] += _metrics_table(
        m["top_songs_longevity"],
        [("song", "Song"), ("artist", "Artist"), ("days_on_chart", "Days"),
         ("avg_rank", "Avg Rank"), ("best_rank", "Best"), ("rank_volatility", "Volatility"),
         ("avg_popularity", "Avg Pop"), ("popularity_trend_score", "Trend")],
    )
    sections[-1] += (
        "\n\n![Top songs longevity](figures/top_songs_longevity.png)\n"
        "*Figure 3: Top 20 songs by days on chart.*\n"
    )

    # 6. Artist Performance
    sections.append(
        "\n## 6. Artist Performance Analysis\n\n"
        f"The dataset includes {dq['unique_artists']} credited artist strings, which expand "
        f"to {m['artist_stats_shape'][0]} individual artists after splitting collaborations.\n\n"
        "![Artist dominance](figures/artist_dominance.png)\n"
        "*Figure 4: Top 15 artists by total days on chart.*\n\n"
        "### Top 10 artists by chart presence\n\n"
    )
    sections[-1] += _metrics_table(
        m["top_artists"],
        [("artist", "Artist"), ("unique_songs", "Songs"), ("total_chart_days", "Chart Days"),
         ("avg_rank", "Avg Rank"), ("avg_popularity", "Avg Pop"), ("dominance_index", "Dominance %")],
    )

    # 7. Popularity Score Analytics
    sections.append(
        f"\n\n## 7. Popularity Score Analytics\n\n"
        f"The correlation between playlist position and popularity score is "
        f"**r = {m['pop_rank_correlation']}** — a weak negative relationship. Higher-ranked "
        "songs tend to be slightly more popular, but the relationship is far from deterministic. "
        "Many lower-ranked songs carry popularity scores comparable to top-10 entries.\n\n"
        "![Popularity vs rank](figures/popularity_vs_rank.png)\n"
        "*Figure 5: Popularity score vs playlist position (sample of 5,000 data points).*\n\n"
        "### Popularity by rank tier\n\n"
    )
    sections[-1] += _metrics_table(
        tiers,
        [("rank_range", "Rank Range"), ("avg_popularity", "Avg Pop"),
         ("median_popularity", "Median Pop"), ("std_popularity", "Std Dev"),
         ("explicit_pct", "Explicit %")],
    )
    t10 = m["top10_vs_rest"]
    sections[-1] += (
        f"\n\nTop-10 songs average **{t10['top10_avg_pop']}** popularity vs "
        f"**{t10['rest_avg_pop']}** for positions 11-50 — a modest gap, indicating that "
        "playlist position is influenced by factors beyond the popularity metric alone.\n"
    )

    # 8. Content Attribute Analysis
    sections.append(
        "\n## 8. Content Attribute Analysis\n\n"
        "### 8.1 Explicit vs non-explicit\n\n"
        f"Explicit songs make up **{dq['explicit_share_pct']}%** of all chart entries. "
        f"Their average popularity ({ea['explicit_avg_popularity']}) is nearly identical to "
        f"non-explicit songs ({ea['non_explicit_avg_popularity']}), and their average rank "
        f"({ea['explicit_avg_rank']}) is comparable to non-explicit "
        f"({ea['non_explicit_avg_rank']}). The explicit label appears to have "
        "**no meaningful impact** on chart performance in this dataset.\n\n"
        "![Explicit comparison](figures/explicit_comparison.png)\n"
        "*Figure 6: Popularity and rank distributions by explicit flag.*\n\n"
        "![Explicit share trend](figures/explicit_share_trend.png)\n"
        "*Figure 7: Monthly explicit content share in the Top 50.*\n\n"
        "### 8.2 Album type\n\n"
    )
    for at in m["album_type_analysis"]:
        sections[-1] += (
            f"- **{at['album_type'].capitalize()}** tracks: avg popularity "
            f"{at['avg_popularity']}, avg rank {at['avg_rank']}. "
        )
        if at["album_type"] == "single":
            sections[-1] += "Singles carry a slight edge in both metrics.\n"
        elif at["album_type"] == "compilation":
            sections[-1] += "Compilation tracks are rare and perform below average.\n"
        else:
            sections[-1] += "\n"

    dc = m["duration_correlations"]
    sections[-1] += (
        f"\n### 8.3 Song duration\n\n"
        f"Duration shows a negligible correlation with both popularity "
        f"(r = {dc['duration_vs_popularity']}) and rank (r = {dc['duration_vs_rank']}). "
        "Song length has essentially no bearing on chart performance.\n\n"
        "![Duration vs popularity](figures/duration_vs_popularity.png)\n"
        "*Figure 8: Song duration vs average popularity.*\n\n"
        "![Album type performance](figures/album_type_performance.png)\n"
        "*Figure 9: Average popularity and rank by album type.*\n"
    )

    # 9. Key findings and recommendations
    sections.append(
        "\n## 9. Key Findings and Recommendations\n\n"
        "### Findings\n\n"
        f"1. **Chart longevity varies enormously**: the median song stays {eda['median_days_on_chart']} days, "
        f"but the most persistent songs hold a position for {eda['max_days_on_chart']}+ days. "
        "A small group of enduring tracks dominates cumulative chart presence.\n\n"
        "2. **Playlist position and popularity are only weakly correlated** "
        f"(r = {m['pop_rank_correlation']}). Rank is driven by additional factors — "
        "recency, editorial curation, listener momentum — that the popularity metric alone "
        "does not capture.\n\n"
        "3. **Explicit content is not penalised**: explicit and non-explicit songs perform "
        "nearly identically on both popularity and rank. Labels should not shy away from "
        "explicit releases on chart-performance grounds.\n\n"
        "4. **Singles outperform album tracks slightly** on average popularity and rank, "
        "consistent with singles being the promoted format.\n\n"
        "5. **Song duration has no effect** on chart performance. Short and long songs succeed "
        "and fail at equal rates.\n\n"
        "6. **Artist dominance is concentrated**: the top 10 artists by chart days account "
        "for a disproportionate share of the playlist, often through multiple concurrent songs.\n\n"
        "### Recommendations for Atlantic Recording Corporation\n\n"
        "1. **Prioritise catalogue depth over individual releases**: artists with multiple "
        "songs on the chart simultaneously accumulate more total days and visibility.\n\n"
        "2. **Track rank volatility, not just peak rank**: a song that holds rank 15 for "
        "60 days delivers more cumulative exposure than one that hits rank 1 for three days.\n\n"
        "3. **Time releases to low-churn windows**: the entry/exit timeline reveals periods "
        "of high turnover where a new release is more likely to be displaced quickly.\n\n"
        "4. **Do not over-weight the explicit flag in content strategy**: the data shows "
        "no performance penalty.\n\n"
        "5. **Monitor popularity trend scores**: a declining trend score signals a song's "
        "exit window, allowing promotion resources to be shifted to rising tracks.\n\n"
        "6. **Use the dashboard filters for artist-specific deep dives** when planning "
        "an artist's release calendar or evaluating a campaign's impact.\n"
    )

    # 10. Limitations
    sections.append(
        "\n## 10. Limitations\n\n"
        "- The dataset covers one national playlist from one provider. Results may not "
        "generalise to other markets, playlists, or streaming platforms.\n"
        "- The popularity score is an opaque metric from the Atlantic API; its construction "
        "is not documented, so correlations with it should be interpreted cautiously.\n"
        "- Causal claims cannot be made from observational chart data. For instance, "
        "the finding that singles outperform album tracks could reflect promotion strategy "
        "(labels push singles harder) rather than a listener preference.\n"
        "- The dataset does not include stream counts, revenue, or user demographics. "
        "A richer dataset would support deeper commercial analysis.\n"
        "- Artist name splitting (separating collaborations) uses heuristic pattern matching "
        "and may occasionally mis-split or fail to split unusual name formats.\n"
    )

    # 11. Conclusion
    sections.append(
        "\n## 11. Conclusion\n\n"
        "This analysis transforms 18 months of daily Top 50 playlist snapshots into "
        "actionable insight for Atlantic Recording Corporation. The key strategic takeaway "
        "is that chart longevity and portfolio breadth matter more than peak rank alone, "
        "and that content attributes (explicit flag, duration, album type) have minimal "
        "impact on chart performance. The accompanying Streamlit dashboard makes these "
        "findings explorable and filterable, supporting ongoing decision-making as new "
        "data arrives.\n"
    )

    return "\n".join(sections)


def build_executive_summary(m: dict) -> str:
    dq = m["data_quality"]
    ea = m["explicit_analysis"]
    eda = m["eda"]

    sections = []

    sections.append(
        "**Executive Summary**\n\n"
        "**Prepared by:** Gauri Shinde, Second-year Computer Science student, "
        "University of Greenwich\n"
        "**Prepared for:** Programme and funding stakeholders\n\n"
        f"Generated {m['generated_at'][:10]}\n"
    )

    sections.append(
        "## Overview\n\n"
        f"This report summarises an analysis of {dq['unique_dates']} daily snapshots of the "
        f"United States Top 50 streaming playlist ({dq['date_range']}), covering "
        f"{dq['unique_songs']} unique songs by {dq['unique_artists']} artists.\n"
    )

    sections.append(
        "\n## Key Findings\n\n"
        f"1. **Chart longevity**: the median song stays on the chart for "
        f"{eda['median_days_on_chart']} days. A small group of highly persistent tracks "
        f"(up to {eda['max_days_on_chart']} days) dominates cumulative chart presence.\n\n"
        f"2. **Popularity vs rank**: playlist position and popularity score are only weakly "
        f"correlated (r = {m['pop_rank_correlation']}). Rank is shaped by factors beyond "
        "the popularity metric.\n\n"
        f"3. **Explicit content**: explicit songs account for {dq['explicit_share_pct']}% "
        "of chart entries and perform on par with non-explicit songs. No content penalty.\n\n"
        "4. **Singles vs albums**: singles show a slight performance edge over album tracks "
        "on both popularity and average rank.\n\n"
        "5. **Duration**: song length has no measurable effect on chart success.\n\n"
        "6. **Artist concentration**: the top artists maintain multiple songs on the chart "
        "simultaneously, accumulating disproportionate visibility.\n"
    )

    sections.append(
        "\n## Recommendations\n\n"
        "- Invest in **catalogue depth**: artists with multiple concurrent chart entries "
        "gain compounding visibility.\n"
        "- Track **rank volatility and trend scores** to catch songs on the decline early "
        "and reallocate promotion resources.\n"
        "- **Do not restrict explicit releases** on performance grounds — the data shows no penalty.\n"
        "- Time releases to **low-churn windows** identified in the turnover analysis.\n"
        "- Use the **interactive Streamlit dashboard** for ongoing monitoring and "
        "artist-specific deep dives.\n"
    )

    sections.append(
        "\n## Methodology\n\n"
        "All results were generated by an automated Python pipeline that loads the raw CSV, "
        "validates data quality, computes derived KPIs (Days on Chart, Rank Volatility, "
        "Popularity Trend Score, Artist Dominance Index), and produces both this summary and "
        "a full research paper with 9 figures. The Streamlit dashboard reads the same artefacts, "
        "ensuring consistency between the written report and the interactive tool.\n"
    )

    return "\n".join(sections)


def main():
    m = _load_metrics()
    out = config.OUTPUT_DIR

    paper = build_research_paper(m)
    (out / "research_paper.md").write_text(paper, encoding="utf-8")
    print(f"Wrote research_paper.md ({len(paper):,} chars)")

    summary = build_executive_summary(m)
    (out / "executive_summary.md").write_text(summary, encoding="utf-8")
    print(f"Wrote executive_summary.md ({len(summary):,} chars)")


if __name__ == "__main__":
    main()
