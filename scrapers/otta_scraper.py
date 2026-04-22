"""
Otta / Welcome to the Jungle Scraper
Scrapes curated tech/startup jobs in London.
Otta rebranded to Welcome to the Jungle — same great curation.
Uses their public search pages with structured HTML.
"""

import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

# Search URLs for relevant roles
OTTA_SEARCHES = [
    "https://app.welcometothejungle.com/jobs?query=graduate+software+engineer&aroundQuery=London&refinementList%5Boffices.country_code%5D%5B0%5D=GB",
    "https://app.welcometothejungle.com/jobs?query=junior+machine+learning&aroundQuery=London&refinementList%5Boffices.country_code%5D%5B0%5D=GB",
    "https://app.welcometothejungle.com/jobs?query=junior+data+scientist&aroundQuery=London&refinementList%5Boffices.country_code%5D%5B0%5D=GB",
    "https://app.welcometothejungle.com/jobs?query=junior+python+developer&aroundQuery=London&refinementList%5Boffices.country_code%5D%5B0%5D=GB",
    "https://app.welcometothejungle.com/jobs?query=graduate+AI+engineer&aroundQuery=London&refinementList%5Boffices.country_code%5D%5B0%5D=GB",
]

# Also try their API endpoint (discovered from network traffic)
WTTJ_API = "https://www.welcometothejungle.com/api/v1/jobs"


def scrape_otta() -> list:
    """Scrape graduate/junior tech jobs from Welcome to the Jungle (formerly Otta)."""
    jobs = []
    seen = set()

    # Method 1: Try WTTJ API
    api_jobs = _try_api(seen)
    if api_jobs:
        jobs.extend(api_jobs)
        print(f"[Otta/WTTJ] API returned {len(api_jobs)} jobs")

    # Method 2: Scrape search result pages
    for url in OTTA_SEARCHES:
        try:
            page_jobs = _scrape_search_page(url, seen)
            jobs.extend(page_jobs)
        except Exception as e:
            print(f"[Otta/WTTJ] Error: {e}")

    print(f"[Otta/WTTJ] Total: {len(jobs)} curated jobs")
    return jobs


def _try_api(seen: set) -> list:
    """Try Welcome to the Jungle's API for London tech jobs."""
    jobs = []
    queries = [
        "graduate software engineer",
        "junior machine learning engineer",
        "junior data scientist",
        "graduate AI",
        "junior python",
    ]

    for query in queries:
        try:
            params = {
                "query": query,
                "page": 1,
                "per_page": 30,
                "aroundQuery": "London, UK",
                "aroundRadius": 30000,  # 30km
            }
            resp = requests.get(WTTJ_API, params=params, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            data = resp.json()
            results = data if isinstance(data, list) else data.get("jobs", data.get("results", []))

            for item in results:
                if isinstance(item, dict):
                    title = item.get("name", item.get("title", ""))
                    company = ""
                    if "company" in item:
                        c = item["company"]
                        company = c.get("name", "") if isinstance(c, dict) else str(c)
                    elif "organization" in item:
                        company = item["organization"].get("name", "")

                    dedup = f"{title}_{company}".lower()
                    if dedup in seen:
                        continue
                    seen.add(dedup)

                    location = "London"
                    if "office" in item:
                        location = item["office"].get("city", "London")

                    salary = ""
                    if item.get("salary_min") and item.get("salary_max"):
                        salary = f"£{item['salary_min']:,} - £{item['salary_max']:,}"

                    desc = item.get("description", item.get("body", ""))[:500]

                    slug = item.get("slug", item.get("id", ""))
                    url = f"https://app.welcometothejungle.com/jobs/{slug}" if slug else ""

                    jobs.append({
                        "id": f"otta_{hash(dedup) % 100000:05d}",
                        "title": title,
                        "company": company,
                        "location": location,
                        "job_type": "Graduate" if "graduate" in title.lower() else "Full-time",
                        "salary": salary or "Not specified",
                        "source": "Otta",
                        "url": url,
                        "description_snippet": desc,
                        "full_description": desc,
                        "date_posted": item.get("published_at", datetime.now().strftime("%Y-%m-%d"))[:10],
                        "deadline": "",
                        "query_matched": query,
                    })

            print(f"[Otta/WTTJ] '{query}': {len(results)} results")

        except Exception as e:
            print(f"[Otta/WTTJ] API error for '{query}': {e}")

    return jobs


def _scrape_search_page(url: str, seen: set) -> list:
    """Scrape a WTTJ search results page (HTML fallback)."""
    jobs = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for job cards — WTTJ uses structured div elements
        cards = soup.select("[data-testid='search-results-list-item'], div[class*='job-card'], article, li[class*='result']")

        for card in cards:
            try:
                title_el = card.select_one("h3, h4, [class*='title'] a, a[class*='job']")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                link = title_el.get("href", "")
                if link and not link.startswith("http"):
                    link = "https://app.welcometothejungle.com" + link

                dedup = f"{title}_{link}".lower()
                if dedup in seen:
                    continue
                seen.add(dedup)

                company = ""
                company_el = card.select_one("[class*='company'], span[class*='name']")
                if company_el:
                    company = company_el.get_text(strip=True)

                location = "London"
                loc_el = card.select_one("[class*='location'], [class*='city']")
                if loc_el:
                    location = loc_el.get_text(strip=True)

                jobs.append({
                    "id": f"otta_{hash(dedup) % 100000:05d}",
                    "title": title,
                    "company": company,
                    "location": location,
                    "job_type": "Full-time",
                    "salary": "Not specified",
                    "source": "Otta",
                    "url": link,
                    "description_snippet": "",
                    "full_description": "",
                    "date_posted": datetime.now().strftime("%Y-%m-%d"),
                    "deadline": "",
                    "query_matched": "otta_search",
                })

            except Exception:
                continue

    except Exception as e:
        print(f"[Otta/WTTJ] Page scrape error: {e}")

    return jobs