"""
Job Hunter — Main Scraper
Runs all configured scrapers and outputs a unified CSV.

Usage:
    python main.py                  # Run Greenhouse only
    python main.py --all            # Run all scrapers
    python main.py --role-category ai_ml --role-category data_science
    python main.py --greenhouse     # Run only Greenhouse (no API key needed!)
    python main.py --reed           # Run only Reed
    python main.py --adzuna         # Run only Adzuna
"""

import csv
import os
import sys
import argparse
from datetime import datetime

import config as local_config
from config import (
    REED_API_KEY, ADZUNA_APP_ID, ADZUNA_APP_KEY,
    SEARCH_QUERIES, LOCATIONS,
    OUTPUT_DIR, OUTPUT_CSV, MAX_RESULTS_PER_QUERY,
)
from reed_scraper import scrape_reed
from adzuna_scraper import scrape_adzuna
from greenhouse_board_registry import resolve_greenhouse_boards
from greenhouse_scraper import DEFAULT_ROLE_CATEGORIES, ROLE_CATEGORIES, scrape_greenhouse


GREENHOUSE_BOARDS = resolve_greenhouse_boards(
    getattr(local_config, "GREENHOUSE_BOARDS", []),
    getattr(local_config, "GREENHOUSE_BOARD_PRESETS", None),
)
GREENHOUSE_MAX_WORKERS = int(getattr(local_config, "GREENHOUSE_MAX_WORKERS", 12) or 12)


CSV_COLUMNS = [
    "id", "title", "company", "location", "job_type",
    "salary", "source", "url", "description_snippet",
    "date_posted", "query_matched", "status",
]


def run_scrapers(
    sources: list[str] | None = None,
    greenhouse_role_categories: list[str] | None = None,
) -> list[dict]:
    """Run selected scrapers and return combined results."""
    all_jobs = []
    run_all = sources is None

    if run_all or "greenhouse" in sources:
        print(f"\n🌱 Scraping Greenhouse boards ({len(GREENHOUSE_BOARDS)} candidates)...")
        gh_jobs = scrape_greenhouse(
            GREENHOUSE_BOARDS,
            role_categories=greenhouse_role_categories,
            max_workers=GREENHOUSE_MAX_WORKERS,
        )
        all_jobs.extend(gh_jobs)

    if run_all or "reed" in sources:
        print("\n📋 Scraping Reed.co.uk...")
        reed_jobs = scrape_reed(REED_API_KEY, SEARCH_QUERIES, LOCATIONS, MAX_RESULTS_PER_QUERY)
        all_jobs.extend(reed_jobs)

    if run_all or "adzuna" in sources:
        print("\n🔍 Scraping Adzuna...")
        adzuna_jobs = scrape_adzuna(ADZUNA_APP_ID, ADZUNA_APP_KEY, SEARCH_QUERIES, LOCATIONS, MAX_RESULTS_PER_QUERY)
        all_jobs.extend(adzuna_jobs)

    # Add default status
    for job in all_jobs:
        job.setdefault("status", "New")

    return all_jobs


def deduplicate(jobs: list[dict]) -> list[dict]:
    """Remove duplicate jobs based on title + company similarity."""
    seen = set()
    unique = []
    for job in jobs:
        key = f"{job['title'].lower().strip()}|{job['company'].lower().strip()}"
        if key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def save_csv(jobs: list[dict], filepath: str, append: bool = False):
    """Save jobs to CSV. If append=True, merge with existing file."""
    existing_ids = set()

    if append and os.path.exists(filepath):
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)
            existing_ids = {row.get("id", "") for row in existing_rows}
    else:
        existing_rows = []

    # Only add new jobs
    new_jobs = [j for j in jobs if j["id"] not in existing_ids]
    all_rows = existing_rows + new_jobs

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n✅ Saved {len(all_rows)} jobs to {filepath} ({len(new_jobs)} new)")
    return len(new_jobs)


def main():
    parser = argparse.ArgumentParser(description="Job Hunter Scraper")
    parser.add_argument("--all", action="store_true", help="Run all configured scrapers")
    parser.add_argument("--greenhouse", action="store_true", help="Scrape Greenhouse only")
    parser.add_argument("--reed", action="store_true", help="Scrape Reed only")
    parser.add_argument("--adzuna", action="store_true", help="Scrape Adzuna only")
    parser.add_argument(
        "--role-category",
        action="append",
        choices=sorted(ROLE_CATEGORIES),
        default=None,
        help="Greenhouse role category filter. Repeat for multiple categories.",
    )
    parser.add_argument("--append", action="store_true", help="Append to existing CSV instead of overwriting")
    args = parser.parse_args()

    # Figure out which sources to run
    sources = []
    if args.greenhouse:
        sources.append("greenhouse")
    if args.reed:
        sources.append("reed")
    if args.adzuna:
        sources.append("adzuna")

    if args.all:
        sources = None  # run all
    elif not sources:
        sources = ["greenhouse"]

    print("=" * 60)
    print(f"  Job Hunter Scraper — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    role_categories = args.role_category or DEFAULT_ROLE_CATEGORIES
    jobs = run_scrapers(sources, greenhouse_role_categories=role_categories)
    jobs = deduplicate(jobs)

    # Sort by date (newest first)
    jobs.sort(key=lambda j: j.get("date_posted", ""), reverse=True)

    new_count = save_csv(jobs, OUTPUT_CSV, append=args.append)

    # Print summary
    print("\n📊 Summary:")
    sources_found = {}
    for j in jobs:
        src = j["source"]
        sources_found[src] = sources_found.get(src, 0) + 1
    for src, count in sorted(sources_found.items()):
        print(f"   {src}: {count} jobs")
    print(f"   Total: {len(jobs)} unique jobs")


if __name__ == "__main__":
    main()
