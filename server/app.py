"""
Job Hunter API Server
"""
import sys, os, threading
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

SERVER_DIR = str(Path(__file__).resolve().parent)
SCRAPERS_DIR = str(Path(__file__).resolve().parent.parent / "scrapers")
if SERVER_DIR not in sys.path: sys.path.insert(0, SERVER_DIR)
if SCRAPERS_DIR not in sys.path: sys.path.insert(0, SCRAPERS_DIR)

from database import (init_db, insert_jobs, get_jobs, update_job, add_manual_job,
    delete_job, get_column_values, get_stats, log_scrape, finish_scrape,
    get_last_scrape, recategorize_all)
from categorizer import enrich_job
from apply_engine import generate_application

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"[API] Server dir: {SERVER_DIR}")
    print(f"[API] Scrapers dir: {SCRAPERS_DIR}")
    yield

app = FastAPI(title="Job Hunter API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
scrape_state = {"running": False, "progress": "", "log_id": None}

class ScrapeRequest(BaseModel):
    sources: list[str] = ["greenhouse", "reed", "adzuna"]

class JobUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None

class ManualJob(BaseModel):
    title: str
    company: str = ""
    url: str = ""
    location: str = ""
    job_type: str = "Full-time"
    salary: str = ""
    description_snippet: str = ""

# ── Scraping ──
@app.post("/api/scrape")
def start_scrape(req: ScrapeRequest):
    if scrape_state["running"]:
        raise HTTPException(400, "Already running")

    def run():
        scrape_state["running"] = True
        scrape_state["progress"] = "Starting..."
        log_id = log_scrape(req.sources)
        total_found = total_new = 0
        try:
            from config import (REED_API_KEY, ADZUNA_APP_ID, ADZUNA_APP_KEY,
                SEARCH_QUERIES, LOCATIONS, GREENHOUSE_BOARDS, MAX_RESULTS_PER_QUERY)

            if "greenhouse" in req.sources:
                scrape_state["progress"] = "Scraping Greenhouse..."
                from greenhouse_scraper import scrape_greenhouse
                jobs = [enrich_job(j) for j in scrape_greenhouse(GREENHOUSE_BOARDS)]
                f, n = insert_jobs(jobs); total_found += f; total_new += n

            if "reed" in req.sources:
                scrape_state["progress"] = "Scraping Reed..."
                from reed_scraper import scrape_reed
                jobs = [enrich_job(j) for j in scrape_reed(REED_API_KEY, SEARCH_QUERIES, LOCATIONS, MAX_RESULTS_PER_QUERY)]
                f, n = insert_jobs(jobs); total_found += f; total_new += n

            if "adzuna" in req.sources:
                scrape_state["progress"] = "Scraping Adzuna..."
                from adzuna_scraper import scrape_adzuna
                jobs = [enrich_job(j) for j in scrape_adzuna(ADZUNA_APP_ID, ADZUNA_APP_KEY, SEARCH_QUERIES, LOCATIONS, MAX_RESULTS_PER_QUERY)]
                f, n = insert_jobs(jobs); total_found += f; total_new += n

            finish_scrape(log_id, total_found, total_new, "done")
            scrape_state["progress"] = f"Done! {total_new} new / {total_found} total"
        except Exception as e:
            finish_scrape(log_id, total_found, total_new, f"error: {e}")
            scrape_state["progress"] = f"Error: {e}"
        finally:
            scrape_state["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return {"message": "Started", "sources": req.sources}

@app.get("/api/scrape/status")
def scrape_status():
    return {"running": scrape_state["running"], "progress": scrape_state["progress"], "last_scrape": get_last_scrape()}

# ── Jobs ──
@app.get("/api/jobs")
def list_jobs(status: str = None, source: str = None, is_uk: str = None, category: str = None, city: str = None):
    return get_jobs(status=status, source=source, is_uk=is_uk, category=category, city=city)

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

# ── Filters ──
@app.get("/api/filters")
def all_filters():
    cols = ["company", "location", "city", "job_type", "category", "source", "status"]
    return {c: get_column_values(c) for c in cols}

@app.get("/api/stats")
def stats():
    return get_stats()

@app.get("/api/config")
def get_config():
    try:
        from config import SEARCH_QUERIES, LOCATIONS, GREENHOUSE_BOARDS, REED_API_KEY, ADZUNA_APP_ID
        return {"queries": SEARCH_QUERIES, "locations": LOCATIONS, "greenhouse_boards": GREENHOUSE_BOARDS,
                "has_reed_key": bool(REED_API_KEY), "has_adzuna_key": bool(ADZUNA_APP_ID)}
    except: return {"queries":[],"locations":[],"greenhouse_boards":[],"has_reed_key":False,"has_adzuna_key":False}

# ── Recategorize existing jobs ──
@app.post("/api/recategorize")
def recategorize():
    count = recategorize_all()
    return {"recategorized": count}

@app.get("/api/health")
def health():
    return {"status": "ok"}

# ── Smart Apply ──
apply_state = {}  # job_id -> {status, result}

@app.post("/api/apply/{job_id}")
def start_apply(job_id: str):
    """Generate tailored resume + cover letter for a job."""
    # Check if already generating
    if job_id in apply_state and apply_state[job_id].get("status") == "generating":
        return {"message": "Already generating", "status": "generating"}

    # Fetch job from DB
    jobs = get_jobs()
    job = next((j for j in jobs if j["id"] == job_id), None)
    if not job:
        raise HTTPException(404, "Job not found")

    # Get API key
    try:
        from config import GROQ_API_KEY
        api_key = GROQ_API_KEY
    except (ImportError, AttributeError):
        api_key = os.environ.get("GROQ_API_KEY", "")

    if not api_key:
        raise HTTPException(400, "No GROQ_API_KEY configured. Add it to scrapers/config.py")

    # Run in background
    apply_state[job_id] = {"status": "generating", "result": None}

    def run():
        try:
            result = generate_application(job, api_key)
            apply_state[job_id] = {"status": "done", "result": result}
        except Exception as e:
            apply_state[job_id] = {"status": "error", "result": {"error": str(e)}}

    threading.Thread(target=run, daemon=True).start()
    return {"message": "Generating...", "status": "generating"}

@app.get("/api/apply/{job_id}")
def get_apply_result(job_id: str):
    """Check status / get result of application generation."""
    if job_id not in apply_state:
        return {"status": "not_started"}
    return apply_state[job_id]

# ── Gmail Tracker ──
email_scan_state = {"running": False, "result": None, "error": None}

@app.post("/api/emails/scan")
def scan_emails(days: int = 30):
    """Scan Gmail for application updates. Runs in background."""
    if email_scan_state["running"]:
        return {"status": "running"}

    try:
        from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, GROQ_API_KEY
    except (ImportError, AttributeError):
        raise HTTPException(400, "Gmail credentials not configured in scrapers/config.py")

    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise HTTPException(400, "GMAIL_ADDRESS and GMAIL_APP_PASSWORD required in scrapers/config.py")

    from gmail_tracker import fetch_emails, classify_emails_batch

    def run():
        email_scan_state["running"] = True
        email_scan_state["error"] = None
        try:
            # Fetch emails
            emails = fetch_emails(GMAIL_ADDRESS, GMAIL_APP_PASSWORD, days=days)
            print(f"[Gmail] Fetched {len(emails)} emails from last {days} days")

            # Classify with LLM
            if emails and GROQ_API_KEY:
                classified = classify_emails_batch(emails, GROQ_API_KEY)
                # Filter to job-related only
                job_emails = [e for e in classified if e.get("is_job_related")]
                print(f"[Gmail] {len(job_emails)} job-related out of {len(classified)} total")
                email_scan_state["result"] = {
                    "total_scanned": len(emails),
                    "job_related": len(job_emails),
                    "emails": job_emails,
                    "scanned_at": datetime.now().isoformat(),
                }
            else:
                email_scan_state["result"] = {
                    "total_scanned": len(emails),
                    "job_related": 0,
                    "emails": [],
                    "scanned_at": datetime.now().isoformat(),
                }
        except Exception as e:
            print(f"[Gmail] Error: {e}")
            email_scan_state["error"] = str(e)
        finally:
            email_scan_state["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return {"status": "started"}

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