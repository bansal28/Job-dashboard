"""
Reed.co.uk Job Scraper
Aggressive filtering: removes training courses, senior roles, spam, recruitment ads.
Only returns jobs genuinely suitable for an MSc AI graduate with 2yr SWE experience.
"""

import requests
import base64
from datetime import datetime

# ─── BLACKLISTS ──────────────────────────────────────────────

TITLE_BLACKLIST = [
    # Senior roles
    "senior", "sr.", "lead", "principal", "staff", "head of",
    "director", "vp ", "vice president", "chief", "architect",
    "manager", "team lead", "engineering manager",
    # Way too experienced
    "10+", "8+", "7+", "6+", "5+ years",
    # Training / courses
    "training", "course", "bootcamp", "apprentice level 3",
    "qualification", "certified", "certificate in",
    "learn to code", "become a", "career change",
    "no experience needed", "no experience required",
    # Non-tech
    "sales", "marketing", "recruiter", "recruitment consultant",
    "hr ", "human resource", "accountant", "finance manager",
    "legal", "customer service", "support analyst",
    "teacher", "lecturer", "tutor",
]

COMPANY_BLACKLIST = [
    # Training companies disguised as employers
    "qa consulting", "qa limited", "qa ltd",
    "learning people", "just it training",
    "futurelearn", "coursera", "edx", "udacity",
    "general assembly", "makers academy", "le wagon",
    "northcoders", "digital skills", "multiverse",
    "sparta global", "bright network", "revolent",
    "fdm group",  # Training scheme, not real engineering
    "accenture bootcamp",
    # Recruitment agencies that post fake/duplicate listings
    "reed specialist", "reed technology",
]

DESCRIPTION_BLACKLIST = [
    # Training programs in disguise
    "no experience necessary",
    "no prior experience",
    "we will train you from scratch",
    "fully funded training",
    "our training programme",
    "12-week bootcamp",
    "guaranteed job placement",
    "earn while you learn",
    "get qualified in",
]


def scrape_reed(api_key: str, queries: list, locations: list, max_per_query: int = 30) -> list:
    """Fetch jobs from Reed API with aggressive quality filtering."""

    if not api_key:
        print("[Reed] No API key — skipping.")
        return []

    base_url = "https://www.reed.co.uk/api/1.0/search"
    auth_header = base64.b64encode(f"{api_key}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}"}

    jobs = []
    seen_ids = set()
    stats = {"total_raw": 0, "spam": 0, "senior": 0, "low_salary": 0, "kept": 0}

    for query in queries:
        for location in locations:
            params = {
                "keywords": query,
                "locationName": location,
                "distancefromlocation": 15,
                "resultsToTake": max_per_query,
                "graduate": True if "graduate" in query.lower() else None,
            }
            # Remove None params
            params = {k: v for k, v in params.items() if v is not None}

            try:
                resp = requests.get(base_url, headers=headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("results", []):
                    job_id = str(item.get("jobId", ""))
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    stats["total_raw"] += 1

                    title = item.get("jobTitle", "").strip()
                    company = item.get("employerName", "").strip()
                    full_desc = item.get("jobDescription", "")
                    min_sal = item.get("minimumSalary")
                    max_sal = item.get("maximumSalary")

                    # ─── FILTER 1: Title blacklist ─────
                    if _title_blocked(title):
                        stats["senior"] += 1
                        continue

                    # ─── FILTER 2: Company blacklist ───
                    if _company_blocked(company):
                        stats["spam"] += 1
                        continue

                    # ─── FILTER 3: Description spam ────
                    if _desc_spam(full_desc):
                        stats["spam"] += 1
                        continue

                    # ─── FILTER 4: Salary sanity ───────
                    # If salary listed and < £20k annual, it's probably a training "stipend"
                    if max_sal and max_sal < 20000 and max_sal > 500:
                        # Likely annual salary below minimum — skip
                        stats["low_salary"] += 1
                        continue

                    # ─── Build job dict ────────────────
                    job_type = "Full-time"
                    if item.get("partTime"): job_type = "Part-time"
                    elif item.get("contractType") == "contract": job_type = "Contract"

                    salary = "Not specified"
                    if min_sal and max_sal:
                        salary = f"\u00a3{int(min_sal):,} - \u00a3{int(max_sal):,}"
                    elif min_sal:
                        salary = f"\u00a3{int(min_sal):,}+"

                    stats["kept"] += 1
                    jobs.append({
                        "id": f"reed_{job_id}",
                        "title": title,
                        "company": company,
                        "location": item.get("locationName", "").strip(),
                        "job_type": job_type,
                        "salary": salary,
                        "source": "Reed",
                        "url": item.get("jobUrl", ""),
                        "description_snippet": full_desc[:500],
                        "full_description": full_desc,
                        "date_posted": _parse_reed_date(item.get("date", "")),
                        "deadline": _parse_reed_date(item.get("expirationDate", "")),
                        "query_matched": query,
                    })

                print(f"[Reed] '{query}' in {location}: {len(data.get('results', []))} raw")

            except requests.RequestException as e:
                print(f"[Reed] Error for '{query}' in {location}: {e}")

    print(f"[Reed] Results: {stats['kept']} kept / {stats['total_raw']} raw "
          f"(filtered: {stats['spam']} spam, {stats['senior']} senior, {stats['low_salary']} low-salary)")
    return jobs


def _title_blocked(title: str) -> bool:
    t = title.lower()
    return any(b in t for b in TITLE_BLACKLIST)


def _company_blocked(company: str) -> bool:
    c = company.lower()
    return any(b in c for b in COMPANY_BLACKLIST)


def _desc_spam(desc: str) -> bool:
    d = desc[:500].lower()
    return any(b in d for b in DESCRIPTION_BLACKLIST)


def _parse_reed_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str.split("T")[0] if "T" in date_str else date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except Exception:
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except Exception:
            return ""