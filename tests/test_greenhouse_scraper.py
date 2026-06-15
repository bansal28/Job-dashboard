import sys
from pathlib import Path


SCRAPERS_DIR = Path(__file__).resolve().parent.parent / "scrapers"
if str(SCRAPERS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRAPERS_DIR))

from greenhouse_scraper import _matched_role_categories, get_role_category_options  # noqa: E402


def test_greenhouse_role_filter_matches_ai_ml_content():
    labels = _matched_role_categories(
        "Research Engineer",
        "Build LLM evaluation systems for machine learning models.",
        ["ai_ml"],
    )

    assert labels == ["AI / ML"]


def test_greenhouse_role_filter_rejects_unselected_category():
    labels = _matched_role_categories(
        "Backend Engineer",
        "Build distributed APIs in Python.",
        ["ai_ml"],
    )

    assert labels == []


def test_greenhouse_role_category_options_are_ui_ready():
    options = get_role_category_options()

    assert {"id": "ai_ml", "label": "AI / ML"} in options
