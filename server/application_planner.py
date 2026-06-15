"""
Application plan builder.

This deliberately separates "prepare an application" from "submit an
application". For third-party Greenhouse boards, applicants can read public
job/form metadata, but cannot submit through the API without the hiring
company's Job Board API key.
"""

from __future__ import annotations

import re
from typing import Any

import requests

try:
    from .database import get_jobs
except ImportError:  # pragma: no cover
    from database import get_jobs


def build_application_plan(job_id: str) -> dict:
    job = _get_job(job_id)
    platform = _detect_platform(job)
    plan = {
        "job_id": job_id,
        "job": {
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "url": job.get("url", ""),
            "source": job.get("source", ""),
            "status": job.get("status", ""),
        },
        "platform": platform,
        "approval_required": True,
        "can_auto_submit": False,
        "manual_submit_required": True,
        "recommended_flow": [
            "Approve the job in the pipeline.",
            "Run Grounded Agent to produce a cited cover letter.",
            "Use the application plan to answer required form questions.",
            "Open the listing and submit only after reviewing the final form.",
        ],
        "warnings": [],
        "form": None,
    }

    if platform == "greenhouse":
        plan.update(_greenhouse_plan(job))
    elif platform == "linkedin":
        plan["warnings"].append(
            "LinkedIn does not expose a general applicant-side apply API for this app; use browser-assisted/manual submission."
        )
    else:
        plan["warnings"].append("No supported structured application API detected for this listing.")

    return plan


def _get_job(job_id: str) -> dict:
    job = next((item for item in get_jobs() if item.get("id") == job_id), None)
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    return job


def _detect_platform(job: dict) -> str:
    url = (job.get("url") or "").lower()
    source = (job.get("source") or "").lower()
    if "greenhouse" in source or "greenhouse.io" in url or "boards.greenhouse.io" in url:
        return "greenhouse"
    if "linkedin" in source or "linkedin.com" in url:
        return "linkedin"
    return "external"


def _greenhouse_plan(job: dict) -> dict:
    token, post_id = _greenhouse_parts(job)
    plan = {
        "greenhouse": {"board_token": token, "job_post_id": post_id},
        "warnings": [
            "Greenhouse application submission requires the hiring company's Job Board API key, so this app can prepare fields but cannot safely submit as an applicant."
        ],
    }
    if not token or not post_id:
        plan["warnings"].append("Could not parse Greenhouse board token/job post ID from this listing.")
        return plan

    form = _fetch_greenhouse_form(token, post_id)
    plan["form"] = form
    return plan


def _greenhouse_parts(job: dict) -> tuple[str, str]:
    job_id = str(job.get("id", ""))
    match = re.match(r"gh_(.+)_(\d+)$", job_id)
    if match:
        return match.group(1), match.group(2)

    url = job.get("url", "") or ""
    url_match = re.search(r"boards\.greenhouse\.io/([^/]+)/jobs/(\d+)", url)
    if url_match:
        return url_match.group(1), url_match.group(2)

    query_match = re.search(r"[?&]gh_jid=(\d+)", url)
    if query_match:
        board_match = re.search(r"boards\.greenhouse\.io/([^/?#]+)", url)
        return (board_match.group(1) if board_match else ""), query_match.group(1)

    return "", ""


def _fetch_greenhouse_form(token: str, post_id: str) -> dict:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{post_id}"
    try:
        response = requests.get(url, params={"questions": "true"}, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "required_questions": [],
            "optional_questions": [],
        }

    questions = _flatten_greenhouse_questions(data)
    required = [q for q in questions if q["required"]]
    optional = [q for q in questions if not q["required"]]
    return {
        "available": True,
        "required_questions": required,
        "optional_questions": optional,
        "data_compliance": data.get("data_compliance") or [],
    }


def _flatten_greenhouse_questions(data: dict[str, Any]) -> list[dict]:
    output = []
    for source in ("questions", "location_questions", "compliance"):
        for question in data.get(source) or []:
            fields = question.get("fields") or []
            output.append({
                "source": source,
                "label": question.get("label", ""),
                "required": bool(question.get("required")),
                "fields": [
                    {
                        "name": field.get("name", ""),
                        "type": field.get("type", ""),
                        "values": field.get("values", []),
                    }
                    for field in fields
                ],
            })
    demographic = data.get("demographic_questions") or {}
    for question in demographic.get("questions") or []:
        output.append({
            "source": "demographic_questions",
            "label": question.get("label", ""),
            "required": bool(question.get("required")),
            "fields": [{
                "name": f"demographic_question_{question.get('id', '')}",
                "type": question.get("type", ""),
                "values": question.get("answer_options", []),
            }],
        })
    return output
