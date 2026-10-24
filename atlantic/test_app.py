"""
test_app.py
===========
Headless smoke test for every dashboard page.

    python test_app.py
"""

from streamlit.testing.v1 import AppTest

PAGES = [
    "Overview",
    "Song Ranking Trends",
    "Artist Dominance",
    "Popularity vs Rank",
    "Explicit vs Non-Explicit",
    "Playlist Timeline Explorer",
]


def test_all_pages():
    at = AppTest.from_file("app.py")
    at.run(timeout=30)
    assert not at.exception, f"Load failed: {at.exception}"
    print("PASS: initial load")

    for page in PAGES:
        at.sidebar.radio[0].set_value(page).run(timeout=30)
        assert not at.exception, f"FAIL: {page} — {at.exception}"
        print(f"PASS: {page}")

    print("All pages passed.")


if __name__ == "__main__":
    test_all_pages()
