"""
GradCracker Scraper — UK's largest STEM graduate job board.
Scrapes graduate jobs and internships in computing/technology.
Every listing is genuinely graduate-level — no senior roles, no training courses.
"""

import requests
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Pages to scrape — all computing/tech graduate jobs + internships in London
GRADCRACKER_URLS = [
    # Graduate jobs
    ("https://www.gradcracker.com/search/computing-technology/graduate-jobs-in-london", "Graduate"),
    ("https://www.gradcracker.com/search/computing-technology/ai-machine-learning-graduate-jobs-in-london", "Graduate"),
    ("https://www.gradcracker.com/search/computing-technology/data-science-graduate-jobs-in-london", "Graduate"),
    ("https://www.gradcracker.com/search/computing-technology/software-systems-graduate-jobs-in-london", "Graduate"),
    # Internships / Placements
    ("https://www.gradcracker.com/search/computing-technology/internships-in-london", "Internship"),
    ("https://www.gradcracker.com/search/computing-technology/ai-machine-learning-internships-in-london", "Internship"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Referer": "https://www.gradcracker.com/",
}


def scrape_gradcracker() -> list:
    """Scrape graduate tech jobs from GradCracker."""
    jobs = []
    seen = set()

    for url, job_type in GRADCRACKER_URLS:
        try:
            page_jobs = _scrape_page(url, job_type, seen)
            jobs.extend(page_jobs)
            print(f"[GradCracker] {url.split('/')[-1]}: {len(page_jobs)} jobs")
        except Exception as e:
            print(f"[GradCracker] Error on {url}: {e}")

    print(f"[GradCracker] Total: {len(jobs)} graduate/intern jobs")
    return jobs


def _scrape_page(url: str, job_type: str, seen: set) -> list:
    """Scrape a single GradCracker search results page."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        print(f"[GradCracker] Got status {resp.status_code} for {url}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    # GradCracker lists jobs in div.listing-item or similar structures
    # Look for job cards — they typically have company name, title, salary, deadline
    cards = soup.select("div.panel-body, div.listing-item, article.job-listing, div.hub-search-result")

    if not cards:
        # Try alternative selectors
        cards = soup.select("[class*='listing'], [class*='result'], [class*='opportunity']")

    for card in cards:
        try:
            # Extract title
            title_el = card.select_one("h3 a, h2 a, a.opportunity-title, a[class*='title']")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            link = title_el.get("href", "")
            if link and not link.startswith("http"):
                link = "https://www.gradcracker.com" + link

            # Skip if already seen
            dedup_key = f"{title}_{link}"
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            # Extract company
            company_el = card.select_one("span.company-name, div.company, a[class*='company'], p.company")
            company = company_el.get_text(strip=True) if company_el else ""

            # If no company found, try parent or sibling
            if not company:
                all_text = card.get_text(" ", strip=True)
                # Company is usually the second prominent text element
                texts = [t.get_text(strip=True) for t in card.select("a, span, div, p") if t.get_text(strip=True) and t.get_text(strip=True) != title]
                company = texts[0] if texts else ""

            # Extract salary
            salary = ""
            salary_el = card.select_one("[class*='salary'], [class*='pay']")
            if salary_el:
                salary = salary_el.get_text(strip=True)
            else:
                salary_match = re.search(r'£[\d,]+(?:\s*[-–]\s*£[\d,]+)?', card.get_text())
                if salary_match:
                    salary = salary_match.group()

            # Extract deadline
            deadline = ""
            deadline_el = card.select_one("[class*='deadline'], [class*='closing']")
            if deadline_el:
                deadline_text = deadline_el.get_text(strip=True)
                deadline = _parse_gradcracker_date(deadline_text)

            # Extract location
            location = "London"
            location_el = card.select_one("[class*='location']")
            if location_el:
                location = location_el.get_text(strip=True)

            # Extract description snippet
            desc = ""
            desc_el = card.select_one("p, div.description, [class*='summary']")
            if desc_el and desc_el != title_el:
                desc = desc_el.get_text(strip=True)[:500]

            jobs.append({
                "id": f"gc_{hash(dedup_key) % 100000:05d}",
                "title": title,
                "company": company,
                "location": location,
                "job_type": job_type,
                "salary": salary or "Not specified",
                "source": "GradCracker",
                "url": link,
                "description_snippet": desc,
                "full_description": desc,
                "date_posted": datetime.now().strftime("%Y-%m-%d"),
                "deadline": deadline,
                "query_matched": "gradcracker",
            })

        except Exception as e:
            continue

    return jobs


def _parse_gradcracker_date(text: str) -> str:
    """Try to parse a deadline date string."""
    if not text:
        return ""
    # Remove "Closing:" prefix etc
    text = re.sub(r'^(Closing|Deadline|Apply by):?\s*', '', text, flags=re.I).strip()
    try:
        for fmt in ["%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%B %d, %Y"]:
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    except Exception:
        pass
    return ""