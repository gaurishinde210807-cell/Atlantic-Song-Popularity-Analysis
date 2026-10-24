"""
config.py
=========
Central settings for the Atlantic US Top 50 Playlist analysis.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR     = PROJECT_ROOT / "data"
OUTPUT_DIR   = PROJECT_ROOT / "outputs"
FIGURE_DIR   = OUTPUT_DIR / "figures"
TABLE_DIR    = OUTPUT_DIR / "tables"

CSV_NAME = "Atlantic_United_States.csv"

# Ensure output directories exist on import
for d in (OUTPUT_DIR, FIGURE_DIR, TABLE_DIR):
    d.mkdir(parents=True, exist_ok=True)
