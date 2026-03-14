"""Import existing CSV and re-categorize all jobs."""
import sys, os, csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapers"))

from database import init_db, insert_jobs, recategorize_all
from categorizer import enrich_job

CSV_PATH = str(Path(__file__).resolve().parent.parent / "scrapers" / "output" / "jobs.csv")

def main(path=CSV_PATH):
    init_db()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            jobs = [enrich_job(row) for row in csv.DictReader(f)]
        if jobs:
            total, new = insert_jobs(jobs)
            print(f"CSV: {new} new / {total - new} skipped")

    # Re-categorize everything (in case rules changed)
    recategorize_all()
    print("Done!")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else CSV_PATH)