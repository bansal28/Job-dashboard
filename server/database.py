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
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_hash)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(category)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_is_uk ON jobs(is_uk)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_city ON jobs(city)")

        # Migration: add new columns to existing tables
        _migrate(db)


def _migrate(db):
    """Add columns if they don't exist (for existing databases)."""
    existing = {row[1] for row in db.execute("PRAGMA table_info(jobs)").fetchall()}
    migrations = {
        "category": "TEXT DEFAULT ''",
        "city": "TEXT DEFAULT ''",
        "is_uk": "TEXT DEFAULT '0'",
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
                                     query_matched, status, added_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', ?, ?)
                """, (
                    j.get("id", dhash), dhash,
                    j.get("title", ""), j.get("company", ""),
                    j.get("location", ""), j.get("city", ""), j.get("is_uk", "0"),
                    j.get("job_type", ""), j.get("category", ""),
                    j.get("salary", ""), j.get("source", ""),
                    j.get("url", ""), j.get("description_snippet", ""),
                    j.get("full_description", ""),
                    j.get("date_posted", ""), j.get("query_matched", ""),
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
    allowed = {"status", "notes", "category", "city", "is_uk", "job_type"}
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
        return db.execute("DELETE FROM jobs WHERE id = ? AND source = 'Manual'", (job_id,)).rowcount > 0


def get_column_values(column: str) -> list[str]:
    allowed = {"title", "company", "location", "city", "job_type", "category", "salary", "source", "status", "is_uk"}
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
        # Add category breakdown
        cat_rows = db.execute("SELECT category, COUNT(*) as cnt FROM jobs WHERE category != '' GROUP BY category ORDER BY cnt DESC").fetchall()
        stats["categories"] = {r["category"]: r["cnt"] for r in cat_rows}
        # UK count
        uk_row = db.execute("SELECT COUNT(*) as cnt FROM jobs WHERE is_uk = '1'").fetchone()
        stats["uk_count"] = uk_row["cnt"] if uk_row else 0
        return stats


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