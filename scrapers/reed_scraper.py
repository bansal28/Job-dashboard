"""
Reed.co.uk Job Scraper
Uses the Reed API (https://www.reed.co.uk/developers/jobseeker)
Free API key gives 5000 requests/day.
"""

import requests
import base64
from datetime import datetime


def scrape_reed(api_key: str, queries: list, locations: list, max_per_query: int = 50) -> list:
    """Fetch jobs from Reed.co.uk API."""

    if not api_key:
        print("[Reed] No API key set — skipping.")
        return []

    base_url = "https://www.reed.co.uk/api/1.0/search"
    # Reed uses basic auth with API key as username, empty password
    auth_header = base64.b64encode(f"{api_key}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}"}

    jobs = []
    seen_ids = set()

    for query in queries:
        for location in locations:
            params = {
                "keywords": query,
                "locationName": location,
                "distancefromlocation": 25,
                "resultsToTake": min(max_per_query, 100),
                "resultsToSkip": 0,
            }

            try:
                resp = requests.get(base_url, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("results", []):
                    job_id = str(item.get("jobId", ""))
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    # Determine job type
                    job_type = "Unknown"
                    if item.get("partTime"):
                        job_type = "Part-time"
                    elif item.get("fullTime"):
                        job_type = "Full-time"
                    elif item.get("contract"):
                        job_type = "Contract"

                    # Salary
                    min_sal = item.get("minimumSalary")
                    max_sal = item.get("maximumSalary")
                    if min_sal and max_sal:
                        salary = f"£{int(min_sal):,} - £{int(max_sal):,}"
                    elif min_sal:
                        salary = f"£{int(min_sal):,}+"
                    else:
                        salary = "Not specified"

                    full_desc = item.get("jobDescription", "")

                    jobs.append({
                        "id": f"reed_{job_id}",
                        "title": item.get("jobTitle", "").strip(),
                        "company": item.get("employerName", "").strip(),
                        "location": item.get("locationName", "").strip(),
                        "job_type": job_type,
                        "salary": salary,
                        "source": "Reed",
                        "url": item.get("jobUrl", ""),
                        "description_snippet": full_desc[:500],
                        "full_description": full_desc,
                        "date_posted": _parse_reed_date(item.get("date", "")),
                        "query_matched": query,
                    })

                print(f"[Reed] '{query}' in {location}: {len(data.get('results', []))} results")

            except requests.RequestException as e:
                print(f"[Reed] Error for '{query}' in {location}: {e}")

    print(f"[Reed] Total unique jobs: {len(jobs)}")
    return jobs


def get_reed_job_details(api_key: str, job_id: str) -> dict:
    """Fetch full job description from Reed (used when applying)."""
    url = f"https://www.reed.co.uk/api/1.0/jobs/{job_id}"
    auth_header = base64.b64encode(f"{api_key}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"[Reed] Error fetching details for {job_id}: {e}")
        return {}


def _parse_reed_date(date_str: str) -> str:
    """Parse Reed date format to YYYY-MM-DD."""
    try:
        # Reed uses format like "17/01/2025"
        dt = datetime.strptime(date_str.split("T")[0] if "T" in date_str else date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return datetime.now().strftime("%Y-%m-%d")