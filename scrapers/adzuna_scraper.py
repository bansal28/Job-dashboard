"""
Adzuna Job Scraper
Uses the Adzuna API (https://developer.adzuna.com/)
Free tier: 250 requests/day.
"""

import requests
from datetime import datetime


def scrape_adzuna(app_id: str, app_key: str, queries: list, locations: list, max_per_query: int = 50) -> list:
    """Fetch jobs from Adzuna API (UK)."""

    if not app_id or not app_key:
        print("[Adzuna] No API credentials set — skipping.")
        return []

    base_url = "https://api.adzuna.com/v1/api/jobs/gb/search"
    jobs = []
    seen_ids = set()

    # Adzuna location mapping (uses 'where' param with place names)
    for query in queries:
        for location in locations:
            page = 1
            collected = 0

            while collected < max_per_query:
                params = {
                    "app_id": app_id,
                    "app_key": app_key,
                    "results_per_page": min(50, max_per_query - collected),
                    "what": query,
                    "where": location,
                    "content-type": "application/json",
                    "sort_by": "date",
                    "page": page,
                }

                try:
                    resp = requests.get(f"{base_url}/{page}", params=params, timeout=15)
                    resp.raise_for_status()
                    data = resp.json()

                    results = data.get("results", [])
                    if not results:
                        break

                    for item in results:
                        job_id = item.get("id", "")
                        if str(job_id) in seen_ids:
                            continue
                        seen_ids.add(str(job_id))

                        # Parse salary
                        min_sal = item.get("salary_min")
                        max_sal = item.get("salary_max")
                        if min_sal and max_sal:
                            salary = f"£{int(min_sal):,} - £{int(max_sal):,}"
                        elif min_sal:
                            salary = f"£{int(min_sal):,}+"
                        else:
                            salary = "Not specified"

                        # Job type from contract fields
                        contract_type = item.get("contract_type", "")
                        contract_time = item.get("contract_time", "")
                        if contract_time == "full_time":
                            job_type = "Full-time"
                        elif contract_time == "part_time":
                            job_type = "Part-time"
                        elif contract_type == "contract":
                            job_type = "Contract"
                        elif contract_type == "permanent":
                            job_type = "Permanent"
                        else:
                            job_type = "Unknown"

                        # Location
                        loc_area = item.get("location", {}).get("area", [])
                        loc_display = item.get("location", {}).get("display_name", location)

                        jobs.append({
                            "id": f"adzuna_{job_id}",
                            "title": item.get("title", "").strip(),
                            "company": item.get("company", {}).get("display_name", "").strip(),
                            "location": loc_display,
                            "job_type": job_type,
                            "salary": salary,
                            "source": "Adzuna",
                            "url": item.get("redirect_url", ""),
                            "description_snippet": item.get("description", "")[:300],
                            "date_posted": _parse_adzuna_date(item.get("created", "")),
                            "query_matched": query,
                        })

                    collected += len(results)
                    page += 1

                    if len(results) < 50:
                        break

                except requests.RequestException as e:
                    print(f"[Adzuna] Error for '{query}' in {location}: {e}")
                    break

            print(f"[Adzuna] '{query}' in {location}: {collected} results")

    print(f"[Adzuna] Total unique jobs: {len(jobs)}")
    return jobs


def _parse_adzuna_date(date_str: str) -> str:
    """Parse Adzuna date to YYYY-MM-DD."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return datetime.now().strftime("%Y-%m-%d")
