"""
Greenhouse Job Board Scraper
Public API — no key needed.

The Greenhouse API is board-scoped, so we fetch configured boards and filter
the returned jobs by selected role categories.
"""

import requests
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    "account executive", "business development", "partnership",
    "community manager", "deal desk",
]

TECHNICAL_ROLE_NOUNS = [
    "engineer", "developer", "scientist", "research", "architect",
    "sre", "devops", "programmer", "analyst", "security",
]

DEFAULT_ROLE_CATEGORIES = ["ai_ml"]

ROLE_CATEGORIES = {
    "ai_ml": {
        "label": "AI / ML",
        "keywords": [
            "machine learning", "ml engineer", "ml scientist", "ml research",
            "ml ops", "mlops", "ml platform", "ml infrastructure",
            "artificial intelligence", " ai engineer", "ai research", "ai scientist",
            "ai safety", "ai infrastructure", "ai platform",
            "deep learning", "neural net", "computer vision",
            "nlp", "natural language", "language model", "llm",
            "reinforcement learning", "generative ai", "gen ai",
            "ai product", "ai intern", "ml intern",
            "applied scientist", "research scientist", "research engineer",
            "pytorch", "tensorflow", "model training", "model deployment",
        ],
    },
    "data_science": {
        "label": "Data Science",
        "keywords": [
            "data scientist", "data science", "data analyst",
            "business intelligence", " bi developer", "bi engineer",
            "analytics engineer", "insight analyst", "quantitative analyst",
            "statistician", "decision scientist",
        ],
    },
    "data_engineering": {
        "label": "Data Engineering",
        "keywords": [
            "data engineer", "data platform", "data infrastructure",
            "etl", "data pipeline", "data warehouse", "dbt ",
            "airflow", "spark engineer", "kafka", "database engineer",
        ],
    },
    "software_engineering": {
        "label": "Software Engineering",
        "keywords": [
            "software engineer", "software developer", "developer",
            "programmer", "coder", "solutions engineer", "solutions architect",
        ],
    },
    "backend": {
        "label": "Backend",
        "keywords": [
            "backend", "back-end", "back end", "server-side",
            "api engineer", "api developer", "microservices",
            "distributed systems", "python engineer", "java engineer",
            "golang engineer", "rust engineer", "node.js engineer",
        ],
    },
    "frontend": {
        "label": "Frontend",
        "keywords": [
            "frontend", "front-end", "front end", "ui engineer",
            "ui developer", "react developer", "react engineer",
            "vue developer", "angular developer", "javascript engineer",
            "typescript engineer", "web developer", "web engineer",
        ],
    },
    "full_stack": {
        "label": "Full Stack",
        "keywords": ["full stack", "fullstack", "full-stack"],
    },
    "mobile": {
        "label": "Mobile",
        "keywords": [
            "mobile engineer", "mobile developer", "ios engineer",
            "ios developer", "android engineer", "android developer",
            "react native", "flutter developer", "swift developer",
            "kotlin developer",
        ],
    },
    "devops_cloud_sre": {
        "label": "DevOps / Cloud / SRE",
        "keywords": [
            "devops", "dev ops", "site reliability", "sre ",
            "platform engineer", "infrastructure engineer", "cloud engineer",
            "cloud architect", "kubernetes", "docker engineer", "terraform",
            "aws engineer", "azure engineer", "gcp engineer",
            "systems engineer", "linux engineer", "release engineer",
        ],
    },
    "security": {
        "label": "Security",
        "keywords": [
            "security engineer", "cybersecurity", "cyber security",
            "infosec", "penetration test", "security analyst",
            "appsec", "application security", "soc analyst",
        ],
    },
    "qa_testing": {
        "label": "QA / Testing",
        "keywords": [
            "qa engineer", "quality assurance", "test engineer",
            "sdet", "automation test", "quality engineer",
        ],
    },
    "product_design": {
        "label": "Product / Design",
        "keywords": [
            "product manager", "product owner", "ux engineer",
            "ux designer", "ui/ux", "design engineer", "product designer",
            "technical product",
        ],
    },
}


def get_role_category_options() -> list[dict]:
    return [
        {"id": category_id, "label": data["label"]}
        for category_id, data in ROLE_CATEGORIES.items()
    ]


def scrape_greenhouse(
    board_tokens: list,
    filter_relevant: bool = True,
    role_categories: list[str] | None = None,
    max_workers: int = 12,
) -> list:
    if not board_tokens:
        return []

    selected_categories = _normalize_role_categories(role_categories)
    board_tokens = _unique_tokens(board_tokens)
    jobs = []
    seen = set()

    workers = max(1, min(int(max_workers or 1), len(board_tokens), 24))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_scrape_board, token, selected_categories, filter_relevant)
            for token in board_tokens
        ]
        for future in as_completed(futures):
            try:
                token, board_jobs, board_count, matched, error = future.result()
            except Exception as exc:
                print(f"[Greenhouse] Error: {exc}")
                continue
            if error:
                if error == "not found":
                    print(f"[Greenhouse] '{token}' not found — skipping")
                else:
                    print(f"[Greenhouse] Error '{token}': {error}")
                continue

            for job in board_jobs:
                if job["id"] in seen:
                    continue
                seen.add(job["id"])
                jobs.append(job)

            role_label = ", ".join(_role_label(category_id) for category_id in selected_categories) or "tech"
            print(f"[Greenhouse] {_prettify(token)}: {matched}/{board_count} {role_label} jobs")

    print(f"[Greenhouse] Total: {len(jobs)}")
    return jobs


def _scrape_board(token: str, selected_categories: list[str], filter_relevant: bool) -> tuple[str, list[dict], int, int, str]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    try:
        resp = requests.get(url, params={"content": "true"}, timeout=15)
        if resp.status_code == 404:
            return token, [], 0, 0, "not found"
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        return token, [], 0, 0, str(exc)

    board_jobs = data.get("jobs", [])
    matched = 0
    jobs = []
    for item in board_jobs:
        job_id = str(item.get("id", ""))
        title = item.get("title", "").strip()
        content = _strip_html(item.get("content", ""))
        matched_roles = _matched_role_categories(title, content, selected_categories)

        if filter_relevant and not matched_roles and not _is_tech(title):
            continue
        if selected_categories and not matched_roles:
            continue

        matched += 1
        location = (item.get("location") or {}).get("name", "Not specified")
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
            "full_description": content,
            "date_posted": _parse_date(item.get("updated_at", "")),
            "query_matched": ", ".join(matched_roles + departments) or "Unknown",
        })
    return token, jobs, len(board_jobs), matched, ""


def _normalize_role_categories(role_categories: list[str] | None) -> list[str]:
    selected = role_categories if role_categories is not None else DEFAULT_ROLE_CATEGORIES
    return [category_id for category_id in selected if category_id in ROLE_CATEGORIES]


def _matched_role_categories(title: str, content: str, selected_categories: list[str]) -> list[str]:
    if not selected_categories:
        return []
    title_text = f" {title.lower()} "
    context_text = f"{title_text} {content[:1200].lower()} "
    if any(kw in title_text for kw in EXCLUDE_KEYWORDS):
        return []
    is_technical_title = any(keyword in title_text for keyword in TECHNICAL_ROLE_NOUNS)
    labels = []
    for category_id in selected_categories:
        keywords = ROLE_CATEGORIES[category_id]["keywords"]
        title_match = any(keyword in title_text for keyword in keywords)
        context_match = is_technical_title and any(keyword in context_text for keyword in keywords)
        if title_match or context_match:
            labels.append(_role_label(category_id))
    return labels


def _role_label(category_id: str) -> str:
    return str(ROLE_CATEGORIES.get(category_id, {}).get("label", category_id))


def _unique_tokens(tokens: list) -> list[str]:
    seen = set()
    output = []
    for token in tokens:
        clean = str(token or "").strip().strip("/").split("/")[-1].lower()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        output.append(clean)
    return output


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
