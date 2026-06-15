"""
Job Hunter API Server
"""
import importlib.util
import sys, threading
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

SERVER_DIR = str(Path(__file__).resolve().parent)
SCRAPERS_DIR = str(Path(__file__).resolve().parent.parent / "scrapers")
if SERVER_DIR not in sys.path: sys.path.insert(0, SERVER_DIR)
if SCRAPERS_DIR not in sys.path: sys.path.insert(0, SCRAPERS_DIR)

from database import (init_db, insert_jobs, get_jobs, update_job, add_manual_job,
    delete_job, get_column_values, get_stats, get_analytics, log_scrape, finish_scrape,
    get_last_scrape, recategorize_all,
    add_task, get_tasks, update_task, complete_task_by_company, get_tasks_summary)
from categorizer import enrich_job
from intake import dashboard_job_subset, select_scrape_candidates
from apply_engine import generate_application
from llm_client import configured_llm_label, has_llm_key
from match_engine import score_all_jobs, get_score_breakdown, get_profile, reload_profile
from profile_manager import get_resume_profile, save_resume_profile
from resume_chunks import load_resume_chunks
from settings import (
    DASHBOARD_MAX_NEW_JOBS,
    DASHBOARD_MIN_MATCH_SCORE,
    SCRAPE_MAX_JOBS,
    SCRAPE_MIN_MATCH_SCORE,
    get_setting,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"[API] Server dir: {SERVER_DIR}")
    print(f"[API] Scrapers dir: {SCRAPERS_DIR}")
    yield

app = FastAPI(title="Job Hunter API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
scrape_state = {"running": False, "progress": "", "log_id": None, "intake": None}

class ScrapeRequest(BaseModel):
    sources: list[str] = ["greenhouse"]
    role_categories: list[str] = ["ai_ml"]
    min_match_score: int = SCRAPE_MIN_MATCH_SCORE
    max_jobs: int = SCRAPE_MAX_JOBS

class JobUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    deadline: str | None = None
    follow_up_date: str | None = None

class ManualJob(BaseModel):
    title: str
    company: str = ""
    url: str = ""
    location: str = ""
    job_type: str = "Full-time"
    salary: str = ""
    description_snippet: str = ""

class RetrievalRequest(BaseModel):
    query: str
    k: int = 6
    method: str = "hybrid"

class ResumeProfileUpload(BaseModel):
    latex_filename: str = ""
    latex_content: str = ""
    resume_filename: str = ""
    resume_content_base64: str = ""

# ── Scraping ──
@app.post("/api/scrape")
def start_scrape(req: ScrapeRequest):
    if scrape_state["running"]:
        raise HTTPException(400, "Already running")

    def run():
        scrape_state["running"] = True
        scrape_state["progress"] = "Starting..."
        scrape_state["intake"] = None
        log_id = log_scrape(req.sources)
        total_found = total_new = 0
        raw_jobs = []
        try:
            import config as local_config
            from greenhouse_board_registry import resolve_greenhouse_boards

            REED_API_KEY = getattr(local_config, "REED_API_KEY", "")
            ADZUNA_APP_ID = getattr(local_config, "ADZUNA_APP_ID", "")
            ADZUNA_APP_KEY = getattr(local_config, "ADZUNA_APP_KEY", "")
            SEARCH_QUERIES = getattr(local_config, "SEARCH_QUERIES", [])
            LOCATIONS = getattr(local_config, "LOCATIONS", [])
            MAX_RESULTS_PER_QUERY = getattr(local_config, "MAX_RESULTS_PER_QUERY", 50)
            GREENHOUSE_BOARDS = resolve_greenhouse_boards(
                getattr(local_config, "GREENHOUSE_BOARDS", []),
                getattr(local_config, "GREENHOUSE_BOARD_PRESETS", None),
            )
            GREENHOUSE_MAX_WORKERS = int(getattr(local_config, "GREENHOUSE_MAX_WORKERS", 12) or 12)

            if "greenhouse" in req.sources:
                scrape_state["progress"] = f"Scraping Greenhouse ({len(GREENHOUSE_BOARDS)} boards)..."
                from greenhouse_scraper import scrape_greenhouse
                raw = scrape_greenhouse(
                    GREENHOUSE_BOARDS,
                    role_categories=req.role_categories,
                    max_workers=GREENHOUSE_MAX_WORKERS,
                )
                raw_jobs.extend(enrich_job(j) for j in raw)

            if "reed" in req.sources:
                scrape_state["progress"] = "Scraping Reed..."
                from reed_scraper import scrape_reed
                raw = scrape_reed(REED_API_KEY, SEARCH_QUERIES, LOCATIONS, MAX_RESULTS_PER_QUERY)
                raw_jobs.extend(enrich_job(j) for j in raw)

            if "adzuna" in req.sources:
                scrape_state["progress"] = "Scraping Adzuna..."
                from adzuna_scraper import scrape_adzuna
                raw = scrape_adzuna(ADZUNA_APP_ID, ADZUNA_APP_KEY, SEARCH_QUERIES, LOCATIONS, MAX_RESULTS_PER_QUERY)
                raw_jobs.extend(enrich_job(j) for j in raw)

            if "gradcracker" in req.sources:
                if not _module_available("bs4"):
                    print("[GradCracker] beautifulsoup4 not installed — skipping")
                else:
                    scrape_state["progress"] = "Scraping GradCracker..."
                    from gradcracker_scraper import scrape_gradcracker
                    raw = scrape_gradcracker()
                    raw_jobs.extend(enrich_job(j) for j in raw)

            if "otta" in req.sources:
                if not _module_available("bs4"):
                    print("[Otta/WTTJ] beautifulsoup4 not installed — skipping")
                else:
                    scrape_state["progress"] = "Scraping Otta / WTTJ..."
                    from otta_scraper import scrape_otta
                    raw = scrape_otta()
                    raw_jobs.extend(enrich_job(j) for j in raw)

            total_found = len(raw_jobs)
            scrape_state["progress"] = f"Scoring {total_found} jobs for review queue..."
            selected_jobs, intake = select_scrape_candidates(
                raw_jobs,
                min_match_score=req.min_match_score,
                max_jobs=req.max_jobs,
            )
            scrape_state["intake"] = intake
            f, n = insert_jobs(selected_jobs)
            total_new += n

            finish_scrape(log_id, total_found, total_new, "done")
            scrape_state["progress"] = (
                f"Done. Kept {intake['selected_count']} of {intake['unique_count']} unique jobs "
                f"({total_new} new inserted)."
            )
        except Exception as e:
            finish_scrape(log_id, total_found, total_new, f"error: {e}")
            scrape_state["progress"] = f"Error: {e}"
        finally:
            scrape_state["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return {"message": "Started", "sources": req.sources}

@app.get("/api/scrape/status")
def scrape_status():
    return {
        "running": scrape_state["running"],
        "progress": scrape_state["progress"],
        "last_scrape": get_last_scrape(),
        "intake": scrape_state.get("intake"),
    }

# ── Jobs ──
@app.get("/api/jobs")
def list_jobs(
    status: str = None,
    source: str = None,
    is_uk: str = None,
    category: str = None,
    city: str = None,
    min_score: int = 0,
    limit: int = 0,
    dashboard: bool = False,
):
    jobs = get_jobs(status=status, source=source, is_uk=is_uk, category=category, city=city)
    score_all_jobs(jobs)
    if dashboard:
        jobs = dashboard_job_subset(
            jobs,
            min_match_score=min_score or DASHBOARD_MIN_MATCH_SCORE,
            max_new_jobs=limit or DASHBOARD_MAX_NEW_JOBS,
        )
    else:
        if min_score:
            jobs = [job for job in jobs if int(job.get("match_score") or 0) >= min_score]
        if limit:
            jobs = jobs[:limit]
    return jobs

@app.get("/api/picks")
def smart_picks():
    """
    Smart Picks: top 10 jobs you should apply to TODAY.
    Ranked by: match score + freshness + not yet applied.
    """
    from datetime import datetime, timedelta
    jobs = get_jobs()
    score_all_jobs(jobs)

    # Only new/saved jobs (not already applied)
    candidates = [j for j in jobs if j.get("status") in ("New", "Saved")]

    # Score: match_score (0-100) + freshness bonus (0-20) + UK bonus (0-10)
    now = datetime.now()
    for j in candidates:
        score = j.get("match_score", 0)

        # Freshness: posted in last 7 days = +20, last 14 = +10, else 0
        try:
            posted = datetime.strptime(j.get("date_posted", ""), "%Y-%m-%d")
            days_old = (now - posted).days
            if days_old <= 3: score += 20
            elif days_old <= 7: score += 15
            elif days_old <= 14: score += 10
        except: pass

        # UK/Remote bonus
        if j.get("is_uk") == "1": score += 5

        # Has deadline soon = urgency bonus
        try:
            dl = datetime.strptime(j.get("deadline", ""), "%Y-%m-%d")
            days_left = (dl - now).days
            if 0 <= days_left <= 7: score += 10
        except: pass

        j["pick_score"] = score

    # Sort by pick_score, take top 10
    candidates.sort(key=lambda j: j.get("pick_score", 0), reverse=True)
    top = candidates[:10]

    return {
        "picks": top,
        "total_candidates": len(candidates),
        "generated_at": now.isoformat(),
    }

@app.patch("/api/jobs/{job_id}")
def patch_job(job_id: str, updates: JobUpdate):
    data = updates.model_dump(exclude_none=True)
    if not data: raise HTTPException(400, "Nothing to update")
    if not update_job(job_id, data): raise HTTPException(404, "Not found")
    return {"ok": True}

@app.post("/api/jobs")
def create_job(job: ManualJob):
    enriched = enrich_job(job.model_dump())
    job_id = add_manual_job(enriched)
    if not job_id: raise HTTPException(409, "Already exists")
    return {"id": job_id}

@app.delete("/api/jobs/{job_id}")
def remove_job(job_id: str):
    if not delete_job(job_id): raise HTTPException(404, "Not found")
    return {"ok": True}

# ── Match Score ──
@app.get("/api/match/{job_id}")
def match_breakdown(job_id: str):
    """Get detailed match score breakdown for a job."""
    jobs = get_jobs()
    job = next((j for j in jobs if j["id"] == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")
    return get_score_breakdown(job)

@app.post("/api/match/reload")
def reload_match_profile():
    """Reload the candidate profile (after resume update)."""
    profile = reload_profile()
    return {
        "skills_count": len(profile["skills"]),
        "experience_years": profile["years_experience"],
        "education": profile["education_level"],
        "domains": sorted(profile["domains"]),
    }

@app.post("/api/retrieve")
def retrieve_resume(body: RetrievalRequest):
    """Retrieve resume evidence with dense, sparse, or hybrid retrieval."""
    if body.method not in {"dense", "sparse", "hybrid"}:
        raise HTTPException(400, "method must be one of: dense, sparse, hybrid")
    from hybrid_retriever import retrieve
    return {
        "query": body.query,
        "method": body.method,
        "results": retrieve(body.query, k=body.k, method=body.method),
    }

# ── User Profile / Resume Source ──
@app.get("/api/profile/resume")
def profile_resume():
    """Return active resume profile metadata without exposing file contents."""
    return _resume_profile_payload()

@app.post("/api/profile/resume")
def upload_profile_resume(body: ResumeProfileUpload):
    """Upload user resume files and make the LaTeX source active for RAG."""
    try:
        save_resume_profile(
            latex_filename=body.latex_filename,
            latex_content=body.latex_content,
            resume_filename=body.resume_filename,
            resume_content_base64=body.resume_content_base64,
        )
        reload_profile()
        return _resume_profile_payload()
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def _resume_profile_payload() -> dict:
    profile = get_resume_profile()
    chunks = load_resume_chunks()
    parsed = get_profile()
    return {
        **profile,
        "chunk_count": len(chunks),
        "skills_count": len(parsed.get("skills", [])),
        "experience_years": parsed.get("years_experience", 0),
        "education": parsed.get("education_level", "unknown"),
        "domains": sorted(parsed.get("domains", [])),
    }

# ── Deadline tracking ──
@app.patch("/api/jobs/{job_id}/deadline")
def set_deadline(job_id: str, body: dict):
    """Set application deadline for a job."""
    deadline = body.get("deadline", "")
    if not update_job(job_id, {"deadline": deadline}):
        raise HTTPException(404, "Not found")
    return {"ok": True}

# ── Filters ──
@app.get("/api/filters")
def all_filters():
    cols = ["company", "location", "city", "job_type", "category", "source", "status"]
    return {c: get_column_values(c) for c in cols}

@app.get("/api/stats")
def stats():
    return get_stats()

@app.get("/api/analytics")
def analytics():
    """Full analytics data for the analytics dashboard."""
    return get_analytics()

@app.get("/api/deadlines/upcoming")
def upcoming_deadlines():
    """Get jobs with deadlines and follow-ups in the next 7 days."""
    data = get_analytics()
    deadlines = data.get("deadlines", [])
    follow_ups = data.get("follow_ups", [])
    # Only show deadlines for jobs the user cares about
    active_statuses = {"Saved", "Approved", "Applied", "Interview"}
    deadlines = [d for d in deadlines if d.get("status") in active_statuses]
    follow_ups = [f for f in follow_ups if f.get("status") in active_statuses]
    today = datetime.now().strftime("%Y-%m-%d")
    week_later = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    upcoming = [d for d in deadlines if today <= d.get("deadline", "") <= week_later]
    overdue = [d for d in deadlines if d.get("deadline", "") < today]
    follow_up_due = [f for f in follow_ups if today <= f.get("follow_up_date", "") <= week_later]
    follow_up_overdue = [f for f in follow_ups if f.get("follow_up_date", "") < today]
    return {
        "upcoming": upcoming[:20],
        "overdue": overdue[:20],
        "follow_up_due": follow_up_due[:20],
        "follow_up_overdue": follow_up_overdue[:20],
    }

@app.get("/api/config")
def get_config():
    try:
        import config as local_config
        from greenhouse_board_registry import resolve_greenhouse_boards
        from greenhouse_scraper import get_role_category_options
        greenhouse_boards = resolve_greenhouse_boards(
            getattr(local_config, "GREENHOUSE_BOARDS", []),
            getattr(local_config, "GREENHOUSE_BOARD_PRESETS", None),
        )
        return {"queries": getattr(local_config, "SEARCH_QUERIES", []),
                "locations": getattr(local_config, "LOCATIONS", []),
                "greenhouse_boards": greenhouse_boards,
                "greenhouse_board_count": len(greenhouse_boards),
                "greenhouse_board_presets": getattr(local_config, "GREENHOUSE_BOARD_PRESETS", ["europe_tech"]),
                "greenhouse_role_categories": get_role_category_options(),
                "default_greenhouse_role_categories": ["ai_ml"],
                "scrape_defaults": {
                    "min_match_score": SCRAPE_MIN_MATCH_SCORE,
                    "max_jobs": SCRAPE_MAX_JOBS,
                    "dashboard_min_match_score": DASHBOARD_MIN_MATCH_SCORE,
                    "dashboard_max_new_jobs": DASHBOARD_MAX_NEW_JOBS,
                },
                "optional_sources": _optional_source_status(),
                "has_reed_key": bool(get_setting("REED_API_KEY", "")),
                "has_adzuna_key": bool(get_setting("ADZUNA_APP_ID", "")),
                "has_groq_key": bool(get_setting("GROQ_API_KEY", "")),
                "has_openai_key": bool(get_setting("OPENAI_API_KEY", "")),
                "llm": configured_llm_label()}
    except:
        return {"queries": [], "locations": [], "greenhouse_boards": [],
                "greenhouse_board_count": 0,
                "greenhouse_board_presets": ["europe_tech"],
                "greenhouse_role_categories": [],
                "default_greenhouse_role_categories": ["ai_ml"],
                "scrape_defaults": {
                    "min_match_score": SCRAPE_MIN_MATCH_SCORE,
                    "max_jobs": SCRAPE_MAX_JOBS,
                    "dashboard_min_match_score": DASHBOARD_MIN_MATCH_SCORE,
                    "dashboard_max_new_jobs": DASHBOARD_MAX_NEW_JOBS,
                },
                "optional_sources": _optional_source_status(),
                "has_reed_key": False, "has_adzuna_key": False,
                "has_groq_key": False, "has_openai_key": False,
                "llm": configured_llm_label()}

# ── Recategorize existing jobs ──
@app.post("/api/recategorize")
def recategorize():
    count = recategorize_all()
    return {"recategorized": count}


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _optional_source_status() -> dict:
    has_html_parser = _module_available("bs4")
    parser_reason = "Install beautifulsoup4 to enable this HTML scraper."
    return {
        "gradcracker": {"available": has_html_parser, "reason": "" if has_html_parser else parser_reason},
        "otta": {"available": has_html_parser, "reason": "" if has_html_parser else parser_reason},
    }

# ── Tasks (Assignments, Coding Challenges) ──
@app.get("/api/tasks")
def list_tasks(status: str = None):
    """Get all tasks, optionally filtered by status (pending/completed)."""
    return get_tasks(status=status)

@app.get("/api/tasks/summary")
def tasks_summary():
    """Get task counts: pending, completed, by company."""
    return get_tasks_summary()

@app.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: int):
    """Manually mark a task as completed."""
    now = datetime.now().isoformat()
    if not update_task(task_id, {"status": "completed", "completed_at": now}):
        raise HTTPException(404, "Task not found")
    return {"ok": True}

@app.post("/api/tasks/{task_id}/reopen")
def reopen_task(task_id: int):
    """Mark a completed task as pending again."""
    if not update_task(task_id, {"status": "pending", "completed_at": ""}):
        raise HTTPException(404, "Task not found")
    return {"ok": True}

@app.get("/api/health")
def health():
    return {"status": "ok"}

# ── Batch Match Scoring (for CSV jobs) ──
@app.post("/api/match/batch")
def batch_score(body: list[dict]):
    """Score a list of arbitrary jobs (not in DB). Used by CSV upload."""
    score_all_jobs(body)
    # Return just id->score mapping to keep response small
    return [{"id": j.get("id", ""), "match_score": j.get("match_score", 0)} for j in body]

# ── Smart Apply ──
apply_state = {}  # key -> {status, result}

@app.post("/api/apply/{job_id}")
def start_apply(job_id: str):
    """Generate tailored resume + cover letter for a job in the DB."""
    if job_id in apply_state and apply_state[job_id].get("status") == "generating":
        return {"message": "Already generating", "status": "generating"}

    # Fetch job from DB
    jobs = get_jobs()
    job = next((j for j in jobs if j["id"] == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")

    return _run_apply(job_id, job)

@app.post("/api/apply-direct")
def start_apply_direct(job: dict):
    """Generate tailored resume + cover letter for an arbitrary job (CSV upload etc)."""
    key = job.get("id", f"direct_{hash(job.get('title',''))}")
    if key in apply_state and apply_state[key].get("status") == "generating":
        return {"message": "Already generating", "status": "generating", "key": key}
    return _run_apply(key, job)

def _run_apply(key: str, job: dict):
    """Shared apply logic for both DB and direct jobs."""
    if not has_llm_key():
        raise HTTPException(400, "No LLM API key configured. Add OPENAI_API_KEY or GROQ_API_KEY to scrapers/config.py")

    apply_state[key] = {"status": "generating", "result": None}

    def run():
        try:
            result = generate_application(job)
            apply_state[key] = {"status": "done", "result": result}
        except Exception as e:
            apply_state[key] = {"status": "error", "result": {"error": str(e)}}

    threading.Thread(target=run, daemon=True).start()
    return {"message": "Generating...", "status": "generating", "key": key}

@app.get("/api/apply/{job_id}")
def get_apply_result(job_id: str):
    """Check status / get result of application generation."""
    if job_id not in apply_state:
        return {"status": "not_started"}
    return apply_state[job_id]

# ── Agentic Apply ──
@app.post("/agent/apply/{job_id}")
@app.post("/api/agent/apply/{job_id}")
def agent_apply(job_id: str):
    """Run the LangGraph RAG agent for a grounded cover-letter draft."""
    try:
        from job_agent import run_apply_agent
        return run_apply_agent(job_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.get("/api/application-plan/{job_id}")
def application_plan(job_id: str):
    """Return platform capabilities and form metadata for an approved application."""
    try:
        from application_planner import build_application_plan
        return build_application_plan(job_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except Exception as exc:
        raise HTTPException(500, str(exc))

# ── Gmail Tracker + Pipeline Sync ──
email_scan_state = {"running": False, "result": None, "error": None}

@app.post("/api/emails/scan")
def scan_emails(days: int = 30):
    """Scan Gmail, classify emails, and cross-reference with job pipeline."""
    if email_scan_state["running"]:
        return {"status": "running"}

    try:
        from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD
    except (ImportError, AttributeError):
        raise HTTPException(400, "Gmail credentials not configured in scrapers/config.py")

    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise HTTPException(400, "GMAIL_ADDRESS and GMAIL_APP_PASSWORD required in scrapers/config.py")

    from gmail_tracker import fetch_emails, classify_emails_batch

    def run():
        email_scan_state["running"] = True
        email_scan_state["error"] = None
        try:
            emails = fetch_emails(GMAIL_ADDRESS, GMAIL_APP_PASSWORD, days=days)
            print(f"[Gmail] Fetched {len(emails)} emails from last {days} days")

            if emails and has_llm_key():
                classified = classify_emails_batch(emails)
                job_emails = [e for e in classified if e.get("is_job_related")]
                print(f"[Gmail] {len(job_emails)} job-related out of {len(classified)} total")

                # Cross-reference with pipeline
                all_jobs = get_jobs()
                company_map = _build_company_map(all_jobs)
                company_timeline = _build_company_timeline(job_emails, company_map)

                # Auto-sync statuses
                synced = _auto_sync_statuses(job_emails, company_map)

                # Auto-create/complete tasks from emails
                tasks_created, tasks_completed = _process_tasks_from_emails(job_emails, company_map)

                email_scan_state["result"] = {
                    "total_scanned": len(emails),
                    "job_related": len(job_emails),
                    "emails": job_emails,
                    "company_timeline": company_timeline,
                    "synced_count": synced,
                    "tasks_created": tasks_created,
                    "tasks_completed": tasks_completed,
                    "scanned_at": datetime.now().isoformat(),
                }
            else:
                email_scan_state["result"] = {
                    "total_scanned": len(emails),
                    "job_related": 0, "emails": [],
                    "company_timeline": {},
                    "synced_count": 0,
                    "scanned_at": datetime.now().isoformat(),
                }
        except Exception as e:
            print(f"[Gmail] Error: {e}")
            email_scan_state["error"] = str(e)
        finally:
            email_scan_state["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return {"status": "started"}


def _build_company_map(jobs: list[dict]) -> dict:
    """Map company names (lowercase) to job records."""
    cmap = {}
    for j in jobs:
        name = (j.get("company", "") or "").lower().strip()
        if name:
            if name not in cmap:
                cmap[name] = []
            cmap[name].append(j)
    return cmap


def _build_company_timeline(emails: list[dict], company_map: dict) -> dict:
    """
    Build per-company timeline: group emails by company,
    cross-reference with pipeline jobs.
    """
    companies = {}

    for email in emails:
        company = (email.get("company", "") or "").strip()
        if not company:
            continue

        key = company.lower()
        if key not in companies:
            # Find matching jobs
            matched_jobs = []
            for cname, jobs in company_map.items():
                if _fuzzy_match(key, cname):
                    matched_jobs.extend(jobs)

            companies[key] = {
                "name": company,
                "emails": [],
                "jobs": [{"id": j["id"], "title": j["title"], "status": j["status"]} for j in matched_jobs],
                "latest_category": None,
                "email_count": 0,
            }

        companies[key]["emails"].append({
            "subject": email.get("subject", ""),
            "category": email.get("category", ""),
            "date": email.get("date", ""),
            "summary": email.get("ai_summary", ""),
            "sender": email.get("sender_name", ""),
        })
        companies[key]["email_count"] += 1
        companies[key]["latest_category"] = email.get("category", "")

    # Sort emails by date within each company
    for c in companies.values():
        c["emails"].sort(key=lambda e: e.get("date", ""), reverse=True)

    return companies


def _fuzzy_match(a: str, b: str) -> bool:
    """Simple fuzzy match — checks if company names are similar."""
    a, b = a.lower().strip(), b.lower().strip()
    if a == b: return True
    if a in b or b in a: return True
    # Remove common suffixes
    for suffix in [" ltd", " limited", " inc", " plc", " corp", " group", " uk", " solutions", " recruitment", " consulting"]:
        a = a.replace(suffix, "").strip()
        b = b.replace(suffix, "").strip()
    if a == b: return True
    if a in b or b in a: return True
    return False


def _auto_sync_statuses(emails: list[dict], company_map: dict) -> int:
    """
    Auto-update job statuses based on email classifications.
    e.g., rejection email → mark job as Rejected.
    """
    synced = 0
    status_mapping = {
        "interview": "Interview",
        "offer": "Offer",
        "rejection": "Rejected",
        "assignment": "Interview",  # coding challenge = interview stage
        "acknowledgement": "Applied",
    }

    for email in emails:
        company = (email.get("company", "") or "").lower().strip()
        category = email.get("category", "")
        new_status = status_mapping.get(category)

        if not company or not new_status:
            continue

        # Find matching jobs
        for cname, jobs in company_map.items():
            if _fuzzy_match(company, cname):
                for job in jobs:
                    current = job.get("status", "New")
                    # Only upgrade status, never downgrade
                    # Priority: New < Applied < Interview < Offer
                    # Rejected is special — always apply
                    priority = {"New": 0, "Saved": 1, "Applied": 2, "Interview": 3, "Offer": 4, "Rejected": -1}
                    cur_p = priority.get(current, 0)
                    new_p = priority.get(new_status, 0)

                    if new_status == "Rejected" or new_p > cur_p:
                        update_job(job["id"], {"status": new_status})
                        synced += 1

    return synced


def _process_tasks_from_emails(emails: list[dict], company_map: dict) -> tuple[int, int]:
    """
    Auto-create tasks from assignment emails, auto-complete from completion emails.
    Returns (tasks_created, tasks_completed).
    """
    created = 0
    completed = 0

    # Keywords that indicate a task/assignment
    assignment_keywords = ["assignment", "coding challenge", "technical test", "take-home",
                          "coding test", "assessment", "online test", "hackerrank",
                          "codility", "codesignal", "complete the", "please complete"]
    # Keywords that indicate task completion/submission confirmation
    completion_keywords = ["submission received", "submission confirmed", "thank you for completing",
                          "received your submission", "test completed", "assessment completed",
                          "results of your", "thank you for submitting", "successfully completed",
                          "we have received your"]

    for email in emails:
        company = (email.get("company", "") or "").strip()
        category = email.get("category", "")
        subject = (email.get("subject", "") or "").lower()
        summary = (email.get("ai_summary", "") or "").lower()
        text = f"{subject} {summary}"

        if not company:
            continue

        # Find matching job_id
        job_id = ""
        for cname, jobs in company_map.items():
            if _fuzzy_match(company.lower(), cname) and jobs:
                job_id = jobs[0]["id"]
                break

        # Check for assignment / new task
        if category == "assignment" or any(kw in text for kw in assignment_keywords):
            task_id = add_task({
                "job_id": job_id,
                "company": company,
                "task_type": "assignment",
                "title": email.get("subject", "Assignment"),
                "description": email.get("ai_summary", ""),
                "source_email_subject": email.get("subject", ""),
            })
            if task_id:
                created += 1

        # Check for completion confirmation
        if any(kw in text for kw in completion_keywords):
            count = complete_task_by_company(company)
            completed += count

    print(f"[Tasks] Created {created} tasks, completed {completed}")
    return created, completed


@app.get("/api/emails/status")
def email_status():
    """Check email scan status and get results."""
    return {
        "running": email_scan_state["running"],
        "result": email_scan_state["result"],
        "error": email_scan_state["error"],
    }

@app.get("/api/emails/config")
def email_config():
    """Check if Gmail is configured."""
    try:
        from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD
        return {
            "configured": bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD),
            "email": GMAIL_ADDRESS[:3] + "***" if GMAIL_ADDRESS else "",
        }
    except:
        return {"configured": False, "email": ""}
