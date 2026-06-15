import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
sys.path.insert(0, str(SERVER_DIR))

from intake import dashboard_job_subset, select_scrape_candidates  # noqa: E402


def test_select_scrape_candidates_keeps_top_scored_jobs():
    jobs = [
        {"id": "1", "title": "Bad fit", "company": "A", "match_score": 20},
        {"id": "2", "title": "Good fit", "company": "B", "match_score": 75},
        {"id": "3", "title": "Best fit", "company": "C", "match_score": 90},
    ]

    selected, summary = select_scrape_candidates(
        jobs,
        min_match_score=50,
        max_jobs=1,
        scorer=lambda rows: rows,
    )

    assert [job["id"] for job in selected] == ["3"]
    assert summary["raw_count"] == 3
    assert summary["eligible_count"] == 2
    assert summary["capped_count"] == 1


def test_dashboard_subset_keeps_pipeline_jobs_and_caps_new_jobs():
    jobs = [
        {"id": "new-low", "status": "New", "match_score": 20},
        {"id": "new-good", "status": "New", "match_score": 70},
        {"id": "new-best", "status": "New", "match_score": 90},
        {"id": "approved", "status": "Approved", "match_score": 10},
    ]

    subset = dashboard_job_subset(jobs, min_match_score=50, max_new_jobs=1)

    assert [job["id"] for job in subset] == ["new-best", "approved"]
