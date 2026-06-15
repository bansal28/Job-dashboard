"""
Job intake gate.

Scrapers can scan a broad market, but the product should only ask the user to
review jobs that are plausible fits. This module scores raw scrape output,
deduplicates it, and keeps the highest-quality candidates.
"""

from __future__ import annotations

from datetime import datetime
from hashlib import md5
from typing import Callable

try:
    from .match_engine import score_all_jobs
except ImportError:  # pragma: no cover
    from match_engine import score_all_jobs


Scorer = Callable[[list[dict]], list[dict]]


def select_scrape_candidates(
    jobs: list[dict],
    min_match_score: int = 50,
    max_jobs: int = 250,
    scorer: Scorer | None = None,
) -> tuple[list[dict], dict]:
    """
    Return jobs worth inserting into the review queue plus an intake summary.

    `max_jobs <= 0` means no cap. The scorer is injectable so tests can avoid
    loading the full retrieval stack.
    """
    unique_jobs = _dedupe(jobs)
    if scorer is None:
        scorer = score_all_jobs
    if unique_jobs:
        scorer(unique_jobs)

    threshold = max(0, int(min_match_score or 0))
    eligible = [
        job for job in unique_jobs
        if int(job.get("match_score") or 0) >= threshold
    ]
    eligible.sort(key=_ranking_key, reverse=True)

    cap = int(max_jobs or 0)
    selected = eligible[:cap] if cap > 0 else eligible
    selected_ids = {job.get("id") for job in selected}

    return selected, {
        "raw_count": len(jobs),
        "unique_count": len(unique_jobs),
        "eligible_count": len(eligible),
        "selected_count": len(selected),
        "below_threshold_count": len(unique_jobs) - len(eligible),
        "capped_count": max(0, len(eligible) - len(selected)),
        "min_match_score": threshold,
        "max_jobs": cap,
        "selected_ids": [job_id for job_id in selected_ids if job_id],
    }


def dashboard_job_subset(
    jobs: list[dict],
    min_match_score: int = 50,
    max_new_jobs: int = 250,
) -> list[dict]:
    """
    Keep pipeline jobs plus a ranked review queue of new jobs.

    This keeps the dashboard fast and action-oriented while preserving all
    stored jobs in SQLite for analytics and dedupe.
    """
    active = [job for job in jobs if job.get("status") != "New"]
    reviewable = [
        job for job in jobs
        if job.get("status") == "New" and int(job.get("match_score") or 0) >= int(min_match_score or 0)
    ]
    reviewable.sort(key=_ranking_key, reverse=True)
    cap = int(max_new_jobs or 0)
    if cap > 0:
        reviewable = reviewable[:cap]
    active.sort(key=_pipeline_key, reverse=True)
    return reviewable + active


def _dedupe(jobs: list[dict]) -> list[dict]:
    seen = set()
    output = []
    for job in jobs:
        key = job.get("id") or _fallback_key(job)
        if key in seen:
            continue
        seen.add(key)
        output.append(job)
    return output


def _fallback_key(job: dict) -> str:
    parts = [
        str(job.get("title", "")).lower().strip(),
        str(job.get("company", "")).lower().strip(),
        str(job.get("source", "")).lower().strip(),
    ]
    return md5("|".join(parts).encode("utf-8")).hexdigest()


def _ranking_key(job: dict) -> tuple:
    return (
        int(job.get("match_score") or 0),
        int(job.get("legacy_score") or 0),
        1 if job.get("is_uk") == "1" else 0,
        _date_value(job.get("date_posted", "")),
        str(job.get("company", "")),
        str(job.get("title", "")),
    )


def _pipeline_key(job: dict) -> tuple:
    return (
        _status_rank(job.get("status", "")),
        int(job.get("match_score") or 0),
        _date_value(job.get("updated_at") or job.get("added_at") or job.get("date_posted", "")),
    )


def _status_rank(status: str) -> int:
    return {
        "Offer": 5,
        "Interview": 4,
        "Applied": 3,
        "Approved": 2,
        "Saved": 1,
        "Rejected": 0,
    }.get(status, 0)


def _date_value(value: str) -> float:
    if not value:
        return 0.0
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value[:26], fmt).timestamp()
        except ValueError:
            continue
    return 0.0
