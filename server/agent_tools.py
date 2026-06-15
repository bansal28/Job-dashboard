"""
Tool functions used by the application agent.
"""

from __future__ import annotations

from datetime import datetime

try:
    from .database import get_jobs
    from .gmail_tracker import classify_emails_batch, fetch_emails
    from .hybrid_retriever import get_retriever
    from .llm_client import has_llm_key
    from .match_engine import get_score_breakdown
except ImportError:  # pragma: no cover
    from database import get_jobs
    from gmail_tracker import classify_emails_batch, fetch_emails
    from hybrid_retriever import get_retriever
    from llm_client import has_llm_key
    from match_engine import get_score_breakdown


def get_job(job_id: str) -> dict:
    jobs = get_jobs()
    job = next((item for item in jobs if item.get("id") == job_id), None)
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    return job


def fetch_job_description_tool(job_id: str) -> dict:
    job = get_job(job_id)
    description = job.get("full_description") or ""
    if not description and job.get("url"):
        try:
            from .apply_engine import fetch_job_description
        except ImportError:  # pragma: no cover
            from apply_engine import fetch_job_description
        description = fetch_job_description(job.get("url", ""))
    if not description:
        description = job.get("description_snippet", "")
    return {
        "job": job,
        "job_description": description,
        "fetched_at": datetime.now().isoformat(),
    }


def retrieve_resume_evidence(query: str, k: int = 6) -> list[dict]:
    return [result.as_dict() for result in get_retriever().retrieve(query, k=k, method="hybrid")]


def score_match(job_id: str) -> dict:
    return get_score_breakdown(get_job(job_id))


def check_application_status(company_or_email: str, days: int = 30) -> dict:
    try:
        from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD  # type: ignore
    except Exception:
        return {"configured": False, "matches": [], "error": "Gmail credentials are not configured"}

    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return {"configured": False, "matches": [], "error": "Gmail credentials are not configured"}

    emails = fetch_emails(GMAIL_ADDRESS, GMAIL_APP_PASSWORD, days=days)
    if has_llm_key():
        emails = classify_emails_batch(emails)

    needle = company_or_email.lower().strip()
    matches = [
        email for email in emails
        if needle
        and (
            needle in (email.get("company", "") or "").lower()
            or needle in (email.get("sender_email", "") or "").lower()
            or needle in (email.get("subject", "") or "").lower()
        )
    ]
    return {"configured": True, "matches": matches[:10], "total_matches": len(matches)}


def draft_cover_letter(job_id: str) -> dict:
    data = fetch_job_description_tool(job_id)
    job = data["job"]
    jd = data["job_description"]
    evidence = retrieve_resume_evidence(f"{job.get('title', '')}\n{jd}", k=6)
    return {
        "job": job,
        "job_description": jd,
        "evidence": evidence,
    }
