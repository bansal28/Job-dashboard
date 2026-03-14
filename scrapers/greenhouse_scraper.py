"""
Greenhouse Job Board Scraper
Public API — no key needed. Scrapes all tech roles.
Categorization happens later in server/categorizer.py.
"""

import requests
import re
from datetime import datetime
from html import unescape


# ─── TECH ROLE FILTER ────────────────────────────────────────
# Broad: any engineering, data, science, or tech role
# Non-tech (HR, marketing, sales, legal, finance) is excluded

TECH_TITLE_KEYWORDS = [
    # Engineering
    "engineer", "developer", "programmer", "architect", "sre",
    # Data & Science
    "data scien", "data analy", "data engineer", "machine learning",
    "research", "scientist", "analyst",
    # Specific tech
    "devops", "mlops", "sysadmin", "dba", "security",
    "ios", "android", "mobile", "frontend", "backend",
    "full stack", "fullstack", "platform", "infrastructure",
    # Levels
    "intern", "graduate", "junior", "senior", "staff", "principal",
    "lead", "head of engineering", "vp engineering", "cto",
    # AI specific
    "ai ", "ml ", "nlp", "llm", "deep learning", "computer vision",
]

# Exclude these even if they match above
EXCLUDE_KEYWORDS = [
    "sales engineer", "sales", "marketing", "recruiter", "recruiting",
    "human resource", "hr ", "people ops", "talent acquisition",
    "legal", "counsel", "attorney", "lawyer",
    "accountant", "accounting", "finance manager",
    "office manager", "executive assistant", "admin ",
    "customer success", "customer support",
    "content writer", "copywriter", "social media",
]


def scrape_greenhouse(board_tokens: list, filter_relevant: bool = True) -> list:
    if not board_tokens:
        return []

    jobs = []
    seen = set()

    for token in board_tokens:
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        try:
            resp = requests.get(url, params={"content": "true"}, timeout=15)
            if resp.status_code == 404:
                print(f"[Greenhouse] '{token}' not found — skipping")
                continue
            resp.raise_for_status()
            data = resp.json()
            board_jobs = data.get("jobs", [])
            matched = 0

            for item in board_jobs:
                job_id = str(item.get("id", ""))
                if job_id in seen:
                    continue

                title = item.get("title", "").strip()
                content = _strip_html(item.get("content", ""))

                if filter_relevant and not _is_tech(title):
                    continue

                seen.add(job_id)
                matched += 1

                location = item.get("location", {}).get("name", "Not specified")
                departments = [d.get("name", "") for d in item.get("departments", [])]

                jobs.append({
                    "id": f"gh_{token}_{job_id}",
                    "title": title,
                    "company": _prettify(token),
                    "location": location,
                    "job_type": _guess_type(title, content),
                    "salary": "Not specified",
                    "source": "Greenhouse",
                    "url": item.get("absolute_url", f"https://boards.greenhouse.io/{token}/jobs/{job_id}"),
                    "description_snippet": content[:500],
                    "date_posted": _parse_date(item.get("updated_at", "")),
                    "query_matched": ", ".join(departments) or "Unknown",
                })

            print(f"[Greenhouse] {_prettify(token)}: {matched}/{len(board_jobs)} tech jobs")

        except requests.RequestException as e:
            print(f"[Greenhouse] Error '{token}': {e}")

    print(f"[Greenhouse] Total: {len(jobs)}")
    return jobs


def _is_tech(title: str) -> bool:
    t = title.lower()
    if any(kw in t for kw in EXCLUDE_KEYWORDS):
        return False
    return any(kw in t for kw in TECH_TITLE_KEYWORDS)


def _guess_type(title, desc):
    text = f"{title} {desc}".lower()
    if "intern" in text: return "Internship"
    if any(w in text for w in ["graduate", "entry level", "new grad"]): return "Graduate"
    if any(w in text for w in ["contract", "fixed term"]): return "Contract"
    if "part time" in text or "part-time" in text: return "Part-time"
    return "Full-time"


def _prettify(token):
    known = {"anthropic":"Anthropic","deepmind":"Google DeepMind","scaleai":"Scale AI",
             "snorkelai":"Snorkel AI","databricks":"Databricks","thinkingmachines":"Thinking Machines Lab",
             "wayve":"Wayve","stripe":"Stripe"}
    return known.get(token, token.replace("-", " ").title())


def _strip_html(s):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def _parse_date(s):
    try: return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except: return datetime.now().strftime("%Y-%m-%d")