"""
SQLite database for Job Hunter.
Handles storage, deduplication, and querying.
"""

import sqlite3
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "jobs.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_db():
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                dedup_hash TEXT UNIQUE,
                title TEXT NOT NULL,
                company TEXT NOT NULL DEFAULT '',
                location TEXT DEFAULT '',
                city TEXT DEFAULT '',
                is_uk TEXT DEFAULT '0',
                job_type TEXT DEFAULT '',
                category TEXT DEFAULT '',
                salary TEXT DEFAULT '',
                source TEXT DEFAULT '',
                url TEXT DEFAULT '',
                description_snippet TEXT DEFAULT '',
                full_description TEXT DEFAULT '',
                date_posted TEXT DEFAULT '',
                query_matched TEXT DEFAULT '',
                status TEXT DEFAULT 'New',
                notes TEXT DEFAULT '',
                added_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS scrape_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT, finished_at TEXT, sources TEXT,
                total_found INTEGER DEFAULT 0, new_added INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running'
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS job_scores (
                job_id TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                resume_hash TEXT NOT NULL,
                retrieval_method TEXT NOT NULL,
                score INTEGER NOT NULL,
                retrieval_score INTEGER DEFAULT 0,
                legacy_score INTEGER DEFAULT 0,
                role_cap INTEGER DEFAULT 100,
                updated_at TEXT DEFAULT '',
                PRIMARY KEY (job_id, content_hash, resume_hash, retrieval_method)
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_hash)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(category)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_is_uk ON jobs(is_uk)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city)")

        # Tasks table — tracks assignments, tests, follow-ups per job
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT DEFAULT '',
                company TEXT DEFAULT '',
                task_type TEXT DEFAULT '',
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                source_email_subject TEXT DEFAULT '',
                created_at TEXT DEFAULT '',
                completed_at TEXT DEFAULT '',
                due_date TEXT DEFAULT ''
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_company ON tasks(company)")

        # Migration: add new columns to existing tables
        _migrate(db)


def _migrate(db):
    """Add columns if they don't exist (for existing databases)."""
    existing = {row[1] for row in db.execute("PRAGMA table_info(jobs)").fetchall()}
    migrations = {
        "category": "TEXT DEFAULT ''",
        "city": "TEXT DEFAULT ''",
        "is_uk": "TEXT DEFAULT '0'",
        "deadline": "TEXT DEFAULT ''",
        "follow_up_date": "TEXT DEFAULT ''",
        "tier": "TEXT DEFAULT ''",
        "visa_status": "TEXT DEFAULT ''",
        "company_tier": "TEXT DEFAULT ''",
    }
    for col, typedef in migrations.items():
        if col not in existing:
            db.execute(f"ALTER TABLE jobs ADD COLUMN {col} {typedef}")
            print(f"[DB] Added column: {col}")


def _dedup_hash(title: str, company: str, source: str) -> str:
    key = f"{title.lower().strip()}|{company.lower().strip()}|{source.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


def insert_jobs(jobs: list[dict]) -> tuple[int, int]:
    """Insert jobs, skipping duplicates. Jobs should already be enriched."""
    now = datetime.now().isoformat()
    new_count = 0

    with get_db() as db:
        for j in jobs:
            dhash = _dedup_hash(j.get("title", ""), j.get("company", ""), j.get("source", ""))
            try:
                db.execute("""
                    INSERT INTO jobs (id, dedup_hash, title, company, location, city, is_uk,
                                     job_type, category, salary, source, url,
                                     description_snippet, full_description, date_posted,
                                     deadline, tier, visa_status, company_tier,
                                     query_matched, status, added_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', ?, ?)
                """, (
                    j.get("id", dhash), dhash,
                    j.get("title", ""), j.get("company", ""),
                    j.get("location", ""), j.get("city", ""), j.get("is_uk", "0"),
                    j.get("job_type", ""), j.get("category", ""),
                    j.get("salary", ""), j.get("source", ""),
                    j.get("url", ""), j.get("description_snippet", ""),
                    j.get("full_description", ""),
                    j.get("date_posted", ""), j.get("deadline", ""),
                    j.get("tier", ""), j.get("visa_status", ""),
                    j.get("company_tier", ""),
                    j.get("query_matched", ""),
                    now, now,
                ))
                new_count += 1
            except sqlite3.IntegrityError:
                pass  # Duplicate — skip

    return len(jobs), new_count


def get_jobs(status=None, source=None, is_uk=None, category=None, city=None):
    with get_db() as db:
        query = "SELECT * FROM jobs WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"; params.append(status)
        if source:
            query += " AND source = ?"; params.append(source)
        if is_uk:
            query += " AND is_uk = ?"; params.append(is_uk)
        if category:
            query += " AND category = ?"; params.append(category)
        if city:
            query += " AND city = ?"; params.append(city)
        query += " ORDER BY date_posted DESC, added_at DESC"
        return [dict(r) for r in db.execute(query, params).fetchall()]


def update_job(job_id: str, updates: dict) -> bool:
    allowed = {"status", "notes", "category", "city", "is_uk", "job_type", "deadline", "follow_up_date"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False
    fields["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    with get_db() as db:
        return db.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values).rowcount > 0


def add_manual_job(job: dict) -> str:
    now = datetime.now().isoformat()
    job_id = f"manual_{int(datetime.now().timestamp())}_{os.urandom(3).hex()}"
    dhash = _dedup_hash(job.get("title", ""), job.get("company", ""), "Manual")
    with get_db() as db:
        try:
            db.execute("""
                INSERT INTO jobs (id, dedup_hash, title, company, location, city, is_uk,
                                  job_type, category, salary, source, url,
                                  description_snippet, status, date_posted, added_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Manual', ?, ?, 'Saved', ?, ?, ?)
            """, (
                job_id, dhash,
                job.get("title", ""), job.get("company", ""),
                job.get("location", ""), job.get("city", ""), job.get("is_uk", "0"),
                job.get("job_type", "Full-time"), job.get("category", ""),
                job.get("salary", ""), job.get("url", ""),
                job.get("description_snippet", ""),
                now.split("T")[0], now, now,
            ))
            return job_id
        except sqlite3.IntegrityError:
            return ""


def delete_job(job_id: str) -> bool:
    with get_db() as db:
        return db.execute("DELETE FROM jobs WHERE id = ?", (job_id,)).rowcount > 0


def get_column_values(column: str) -> list[str]:
    allowed = {"title", "company", "location", "city", "job_type", "category", "salary", "source", "status", "is_uk", "tier"}
    if column not in allowed:
        return []
    with get_db() as db:
        rows = db.execute(f"SELECT DISTINCT {column} FROM jobs WHERE {column} != '' ORDER BY {column}").fetchall()
        return [r[0] for r in rows]


def get_stats() -> dict:
    with get_db() as db:
        rows = db.execute("SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status").fetchall()
        stats = {r["status"]: r["cnt"] for r in rows}
        stats["total"] = sum(stats.values())
        cat_rows = db.execute("SELECT category, COUNT(*) as cnt FROM jobs WHERE category != '' GROUP BY category ORDER BY cnt DESC").fetchall()
        stats["categories"] = {r["category"]: r["cnt"] for r in cat_rows}
        uk_row = db.execute("SELECT COUNT(*) as cnt FROM jobs WHERE is_uk = '1'").fetchone()
        stats["uk_count"] = uk_row["cnt"] if uk_row else 0
        return stats


def get_analytics() -> dict:
    """Comprehensive analytics for the dashboard."""
    with get_db() as db:
        result = {}

        # ─── Status funnel ───
        status_rows = db.execute("SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status").fetchall()
        result["status_counts"] = {r["status"]: r["cnt"] for r in status_rows}
        result["total_jobs"] = sum(r["cnt"] for r in status_rows)

        # ─── Category breakdown (for applied+ jobs) ───
        cat_rows = db.execute("""
            SELECT category, COUNT(*) as cnt FROM jobs
            WHERE category != '' GROUP BY category ORDER BY cnt DESC
        """).fetchall()
        result["categories"] = {r["category"]: r["cnt"] for r in cat_rows}

        # Applied by category
        applied_cat = db.execute("""
            SELECT category, COUNT(*) as cnt FROM jobs
            WHERE status IN ('Applied', 'Interview', 'Offer', 'Rejected') AND category != ''
            GROUP BY category ORDER BY cnt DESC
        """).fetchall()
        result["applied_by_category"] = {r["category"]: r["cnt"] for r in applied_cat}

        # ─── Location breakdown ───
        city_rows = db.execute("""
            SELECT city, COUNT(*) as cnt FROM jobs
            WHERE city != '' GROUP BY city ORDER BY cnt DESC LIMIT 15
        """).fetchall()
        result["top_cities"] = {r["city"]: r["cnt"] for r in city_rows}

        applied_city = db.execute("""
            SELECT city, COUNT(*) as cnt FROM jobs
            WHERE status IN ('Applied', 'Interview', 'Offer', 'Rejected') AND city != ''
            GROUP BY city ORDER BY cnt DESC LIMIT 10
        """).fetchall()
        result["applied_by_city"] = {r["city"]: r["cnt"] for r in applied_city}

        # ─── Source breakdown ───
        source_rows = db.execute("SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source ORDER BY cnt DESC").fetchall()
        result["sources"] = {r["source"]: r["cnt"] for r in source_rows}

        # ─── Conversion funnel ───
        total_applied = db.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status IN ('Applied', 'Interview', 'Offer', 'Rejected')").fetchone()["cnt"]
        total_interview = db.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status IN ('Interview', 'Offer')").fetchone()["cnt"]
        total_offer = db.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status = 'Offer'").fetchone()["cnt"]
        total_rejected = db.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status = 'Rejected'").fetchone()["cnt"]

        result["funnel"] = {
            "applied": total_applied,
            "interview": total_interview,
            "offer": total_offer,
            "rejected": total_rejected,
            "interview_rate": round(total_interview / total_applied * 100, 1) if total_applied else 0,
            "offer_rate": round(total_offer / total_applied * 100, 1) if total_applied else 0,
            "rejection_rate": round(total_rejected / total_applied * 100, 1) if total_applied else 0,
        }

        # ─── Applications over time (by week) ───
        timeline = db.execute("""
            SELECT strftime('%Y-%W', updated_at) as week, status, COUNT(*) as cnt
            FROM jobs WHERE status != 'New'
            GROUP BY week, status ORDER BY week
        """).fetchall()
        weeks = {}
        for r in timeline:
            w = r["week"]
            if w not in weeks:
                weeks[w] = {}
            weeks[w][r["status"]] = r["cnt"]
        result["timeline"] = weeks

        # ─── Top companies applied to ───
        company_rows = db.execute("""
            SELECT company, COUNT(*) as cnt FROM jobs
            WHERE status IN ('Applied', 'Interview', 'Offer', 'Rejected') AND company != ''
            GROUP BY company ORDER BY cnt DESC LIMIT 10
        """).fetchall()
        result["top_companies"] = {r["company"]: r["cnt"] for r in company_rows}

        # ─── Average match score by status ───
        # Match scores aren't stored in DB (computed at runtime), so skip this

        # ─── Deadlines ───
        deadline_rows = db.execute("""
            SELECT id, title, company, deadline, status FROM jobs
            WHERE deadline != '' AND deadline IS NOT NULL
            ORDER BY deadline ASC
        """).fetchall()
        result["deadlines"] = [dict(r) for r in deadline_rows]

        follow_up_rows = db.execute("""
            SELECT id, title, company, follow_up_date, status FROM jobs
            WHERE follow_up_date != '' AND follow_up_date IS NOT NULL
            ORDER BY follow_up_date ASC
        """).fetchall()
        result["follow_ups"] = [dict(r) for r in follow_up_rows]

        # ─── Job type breakdown ───
        type_rows = db.execute("""
            SELECT job_type, COUNT(*) as cnt FROM jobs
            WHERE job_type != '' GROUP BY job_type ORDER BY cnt DESC
        """).fetchall()
        result["job_types"] = {r["job_type"]: r["cnt"] for r in type_rows}

        return result


def recategorize_all():
    """Re-run categorizer on all existing jobs. Call after updating categorizer rules."""
    from categorizer import enrich_job
    with get_db() as db:
        rows = db.execute("SELECT id, title, location, description_snippet, job_type FROM jobs").fetchall()
        count = 0
        for r in rows:
            job = dict(r)
            enriched = enrich_job(job)
            db.execute(
                "UPDATE jobs SET category = ?, city = ?, is_uk = ?, job_type = ? WHERE id = ?",
                (enriched["category"], enriched["city"], enriched["is_uk"], enriched["job_type"], r["id"])
            )
            count += 1
        print(f"[DB] Re-categorized {count} jobs")
    return count


def log_scrape(sources):
    with get_db() as db:
        return db.execute("INSERT INTO scrape_log (started_at, sources, status) VALUES (?, ?, 'running')",
                          (datetime.now().isoformat(), json.dumps(sources))).lastrowid

def finish_scrape(log_id, total, new, status="done"):
    with get_db() as db:
        db.execute("UPDATE scrape_log SET finished_at=?, total_found=?, new_added=?, status=? WHERE id=?",
                   (datetime.now().isoformat(), total, new, status, log_id))

def get_last_scrape():
    with get_db() as db:
        row = db.execute("SELECT * FROM scrape_log ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None


def get_cached_job_scores(
    content_hashes: dict[str, str],
    resume_hash: str,
    retrieval_method: str,
) -> dict[str, dict]:
    if not content_hashes:
        return {}

    cached: dict[str, dict] = {}
    job_ids = list(content_hashes)
    with get_db() as db:
        for start in range(0, len(job_ids), 500):
            batch = job_ids[start:start + 500]
            placeholders = ",".join("?" for _ in batch)
            rows = db.execute(
                f"""
                SELECT * FROM job_scores
                WHERE job_id IN ({placeholders})
                  AND resume_hash = ?
                  AND retrieval_method = ?
                """,
                [*batch, resume_hash, retrieval_method],
            ).fetchall()
            for row in rows:
                data = dict(row)
                if data.get("content_hash") == content_hashes.get(data.get("job_id", "")):
                    cached[data["job_id"]] = data
    return cached


def save_job_scores(rows: list[dict]) -> None:
    if not rows:
        return

    now = datetime.now().isoformat()
    with get_db() as db:
        db.executemany(
            """
            INSERT OR REPLACE INTO job_scores
                (job_id, content_hash, resume_hash, retrieval_method,
                 score, retrieval_score, legacy_score, role_cap, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.get("job_id", ""),
                    row.get("content_hash", ""),
                    row.get("resume_hash", ""),
                    row.get("retrieval_method", ""),
                    int(row.get("score", 0)),
                    int(row.get("retrieval_score", 0)),
                    int(row.get("legacy_score", 0)),
                    int(row.get("role_cap", 100)),
                    now,
                )
                for row in rows
                if row.get("job_id") and row.get("content_hash")
            ],
        )


# ═══════════════════════════════════════════════════════════
# TASKS — Assignments, tests, follow-ups per company/job
# ═══════════════════════════════════════════════════════════

def add_task(task: dict) -> int:
    """Add a new task. Returns task ID."""
    now = datetime.now().isoformat()
    with get_db() as db:
        # Check for duplicate (same company + similar title)
        existing = db.execute(
            "SELECT id FROM tasks WHERE company = ? AND title = ? AND status = 'pending'",
            (task.get("company", ""), task.get("title", ""))
        ).fetchone()
        if existing:
            return existing["id"]

        cursor = db.execute("""
            INSERT INTO tasks (job_id, company, task_type, title, description,
                             status, source_email_subject, created_at, due_date)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        """, (
            task.get("job_id", ""),
            task.get("company", ""),
            task.get("task_type", "assignment"),
            task.get("title", ""),
            task.get("description", ""),
            task.get("source_email_subject", ""),
            now,
            task.get("due_date", ""),
        ))
        return cursor.lastrowid


def complete_task_by_company(company: str) -> int:
    """Mark all pending tasks for a company as completed."""
    now = datetime.now().isoformat()
    with get_db() as db:
        # Fuzzy match — check multiple variations
        count = 0
        rows = db.execute("SELECT id, company FROM tasks WHERE status = 'pending'").fetchall()
        for row in rows:
            if _fuzzy_company_match(company, row["company"]):
                db.execute("UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?", (now, row["id"]))
                count += 1
        return count


def get_tasks(status: str = None) -> list[dict]:
    """Get all tasks, optionally filtered by status."""
    with get_db() as db:
        if status:
            rows = db.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def update_task(task_id: int, updates: dict) -> bool:
    """Update a task's status or other fields."""
    allowed = {"status", "completed_at", "due_date", "description"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [task_id]
    with get_db() as db:
        return db.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values).rowcount > 0


def get_tasks_summary() -> dict:
    """Get task counts by status and by company."""
    with get_db() as db:
        pending = db.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status = 'pending'").fetchone()["cnt"]
        completed = db.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status = 'completed'").fetchone()["cnt"]

        # By company
        company_rows = db.execute("""
            SELECT company, status, COUNT(*) as cnt FROM tasks
            GROUP BY company, status ORDER BY company
        """).fetchall()
        companies = {}
        for r in company_rows:
            c = r["company"]
            if c not in companies:
                companies[c] = {"pending": 0, "completed": 0}
            companies[c][r["status"]] = r["cnt"]

        return {"pending": pending, "completed": completed, "total": pending + completed, "by_company": companies}


def _fuzzy_company_match(a: str, b: str) -> bool:
    """Simple fuzzy match for company names."""
    a, b = a.lower().strip(), b.lower().strip()
    if a == b or a in b or b in a:
        return True
    for suffix in [" ltd", " limited", " inc", " plc", " corp", " group", " uk"]:
        a = a.replace(suffix, "").strip()
        b = b.replace(suffix, "").strip()
    return a == b or a in b or b in a
