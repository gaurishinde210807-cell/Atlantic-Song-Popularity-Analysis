# United States Top 50 Playlist Performance and Song Popularity Trend Analysis

**Author:** Gauri Shinde, Second-year Computer Science, University of Greenwich

Historical analytics of the US Top 50 streaming playlist for Atlantic Recording Corporation. Analyses playlist ranking patterns, song longevity, artist dominance, popularity trends, and content attribute performance across 555 daily snapshots (May 2024 — November 2025).

---

## Live dashboard

Deployed on Streamlit Community Cloud from this repository (`app.py`, branch `main`).
When deploying, set Python to 3.12 under Advanced settings so the pinned packages in
`requirements.txt` install cleanly. The app reads the pre-computed artefacts in `outputs/`,
so it does not re-run the pipeline on startup.

## Quick start

```bash
# Python 3.12 recommended
pip install -r requirements.txt

# 1. Run the analysis pipeline
python train.py

# 2. Generate the written deliverables
python generate_report.py

# 3. (Optional) Render them as PDF
python make_pdfs.py

# 4. Launch the dashboard
streamlit run app.py
```

---

## What the pipeline does

This project focuses on **historical playlist analytics, not prediction or recommendation**.
There are no machine-learning models. The pipeline:

1. Loads and validates the raw CSV (27,800 rows, 10 columns).
2. Deduplicates one double-snapshot date, standardises artist names.
3. Computes song-level KPIs: Days on Chart, Average Rank, Best Rank, Rank Volatility Index,
   Popularity Trend Score, Duration in minutes.
4. Computes artist-level KPIs: chart presence, dominance index, unique songs, explicit share.
5. Runs six analysis modules: playlist ranking, song performance, artist dominance,
   popularity analytics, content attributes, and rank-tier breakdowns.
6. Generates 10 EDA figures.
7. Writes everything to `outputs/` for the dashboard and report generator.

---

## Dashboard modules

1. **Overview** — KPIs, popularity timeline, playlist turnover, top songs.
2. **Song Ranking Trends** — select and compare individual song trajectories.
3. **Artist Dominance Leaderboard** — sortable artist performance table.
4. **Popularity vs Rank** — scatter plots and rank-tier analysis.
5. **Explicit vs Non-Explicit** — content attribute performance panels.
6. **Playlist Timeline Explorer** — browse any day's Top 50 snapshot with filters.

### Filters (sidebar)

- Date range selector
- Rank range slider (1–50)
- Album type toggle (single / album / compilation)
- Artist filter (on the timeline page)

---

## File map

| File | Purpose |
|---|---|
| `config.py` | Paths and settings |
| `data_prep.py` | Data loading, cleaning, song/artist/daily aggregation |
| `eda.py` | Figure generation (10 PNGs) |
| `train.py` | Main pipeline — runs everything |
| `generate_report.py` | Writes research paper and executive summary from metrics.json |
| `make_pdfs.py` | Renders Markdown deliverables as styled PDFs |
| `app.py` | Streamlit dashboard (6 modules) |
| `test_app.py` | Headless smoke test for all dashboard pages |

### Artefacts in `outputs/`

| Path | Contents |
|---|---|
| `research_paper.md` / `.pdf` | Full write-up: EDA, insights, recommendations |
| `executive_summary.md` / `.pdf` | Non-technical summary for stakeholders |
| `metrics.json` | All computed statistics and analysis results |
| `playlist_clean.csv` | Cleaned dataset used by the dashboard |
| `tables/song_stats.csv` | One row per song with all KPIs |
| `tables/artist_stats.csv` | One row per artist with all KPIs |
| `tables/daily_summary.csv` | Daily averages, turnover stats |
| `figures/*.png` | EDA charts (10 figures) |

---

## Troubleshooting

**`FileNotFoundError` on startup** — the CSV isn't in `data/`. Check the filename matches
`config.CSV_NAME` or pass the path as an argument to `train.py`.

**Dashboard says no artefacts found** — run `python train.py` first.
