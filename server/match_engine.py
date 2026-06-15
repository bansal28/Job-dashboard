"""
Match Score Engine
Rates how well a candidate's profile fits each job (0-100%).
Runs locally — no API calls needed. Instant scoring on all jobs.

Scoring breakdown:
  - Skills match (40%): How many JD skills does the candidate have?
  - Experience level (25%): Is the seniority level right?
  - Domain match (20%): Does the job category align with background?
  - Location match (15%): Is the job in preferred locations?
"""

import re

try:
    from .hybrid_retriever import get_retriever, reload_retriever
    from .profile_manager import get_active_resume_path
    from .settings import RETRIEVAL_METHOD
except ImportError:  # pragma: no cover - supports FastAPI's top-level imports
    try:
        from hybrid_retriever import get_retriever, reload_retriever
        from profile_manager import get_active_resume_path
        from settings import RETRIEVAL_METHOD
    except Exception:  # keeps legacy scoring available
        get_retriever = None
        get_active_resume_path = None
        reload_retriever = None
        RETRIEVAL_METHOD = "hybrid"


# ═══════════════════════════════════════════════════════════
# RESUME PROFILE — Extracted from LaTeX resume
# ═══════════════════════════════════════════════════════════

def load_profile() -> dict:
    """Extract candidate profile from resume LaTeX file."""
    try:
        if get_active_resume_path is None:
            return _default_profile()
        with open(get_active_resume_path(), "r", encoding="utf-8") as f:
            content = f.read().lower()
    except FileNotFoundError:
        return _default_profile()

    # Strip LaTeX commands for cleaner matching
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", content)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}\\]", " ", text)
    text = text.lower()

    profile = {
        "skills": _extract_skills(text),
        "years_experience": _estimate_experience(text),
        "education_level": _detect_education(text),
        "domains": _detect_domains(text),
        "preferred_locations": _detect_locations(text),
        "raw_text": text,
    }
    return profile


def _default_profile():
    """Fallback if resume can't be parsed."""
    return {
        "skills": set(),
        "years_experience": 0,
        "education_level": "bachelors",
        "domains": set(),
        "preferred_locations": {"london", "uk", "remote"},
        "raw_text": "",
    }


# ─── Skill extraction ────────────────────────────────────

KNOWN_SKILLS = {
    # Languages
    "python", "java", "kotlin", "javascript", "typescript", "c++", "c#",
    "go", "golang", "rust", "ruby", "php", "swift", "scala", "r",
    "sql", "html", "css", "bash", "shell",

    # ML / AI
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "numpy", "pandas", "matplotlib", "seaborn", "scipy",
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "reinforcement learning", "neural networks",
    "transformers", "llm", "large language model", "generative ai",
    "hugging face", "langchain", "openai", "gpt",
    "classification", "regression", "clustering",
    "feature engineering", "model training", "model deployment",
    "a/b testing", "experimentation",

    # Data
    "data science", "data analysis", "data engineering",
    "data visualization", "tableau", "power bi", "looker",
    "etl", "data pipeline", "data warehouse",
    "spark", "hadoop", "kafka", "airflow", "dbt",
    "bigquery", "redshift", "snowflake",

    # Web / Mobile
    "react", "angular", "vue", "next.js", "node.js", "express",
    "django", "flask", "fastapi", "spring", "spring boot",
    "android", "ios", "react native", "flutter",
    "rest api", "graphql", "websocket",
    "html/css", "tailwind", "bootstrap",

    # Cloud / DevOps
    "aws", "azure", "gcp", "google cloud",
    "docker", "kubernetes", "terraform", "ansible",
    "ci/cd", "jenkins", "github actions", "gitlab ci",
    "linux", "nginx", "redis", "elasticsearch",

    # Databases
    "postgresql", "mysql", "mongodb", "redis", "dynamodb",
    "sqlite", "oracle", "cassandra", "neo4j",

    # Tools & Practices
    "git", "jira", "agile", "scrum",
    "junit", "pytest", "selenium", "cypress",
    "microservices", "distributed systems",
    "rest", "api design", "system design",
    "mvvm", "solid", "design patterns",
    "unit testing", "integration testing",

    # Other
    "adobe target", "medallia", "segment",
}

def _extract_skills(text: str) -> set:
    """Find all known skills mentioned in text."""
    found = set()
    for skill in KNOWN_SKILLS:
        # Word boundary matching (avoid partial matches)
        if re.search(r'\b' + re.escape(skill) + r'\b', text):
            found.add(skill)
    return found


def _estimate_experience(text: str) -> float:
    """Estimate years of experience from resume text."""
    # Look for explicit mentions
    match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s+)?(?:production\s+)?experience', text)
    if match:
        return float(match.group(1))

    # Count work experience duration from dates
    date_ranges = re.findall(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{4})\s*[-–]\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|present)\s*(\d{4})?', text)
    total_months = 0
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
    for start_m, start_y, end_m, end_y in date_ranges:
        sy = int(start_y)
        sm = months.get(start_m, 1)
        if end_m == "present":
            ey, em = 2026, 3  # approximate current date
        else:
            ey = int(end_y) if end_y else sy
            em = months.get(end_m, 12)
        total_months += max(0, (ey * 12 + em) - (sy * 12 + sm))

    return round(total_months / 12, 1)


def _detect_education(text: str) -> str:
    """Detect highest education level."""
    if any(w in text for w in ["ph.d", "phd", "doctorate"]):
        return "phd"
    if any(w in text for w in ["m.sc", "msc", "m.s.", "master", "mtech", "m.tech"]):
        return "masters"
    if any(w in text for w in ["b.tech", "btech", "b.sc", "bsc", "bachelor", "b.eng"]):
        return "bachelors"
    return "unknown"


def _detect_domains(text: str) -> set:
    """Detect candidate's domain expertise."""
    domains = set()
    domain_keywords = {
        "AI / ML": ["machine learning", "deep learning", "neural network", "tensorflow", "pytorch", "nlp", "computer vision", "ai "],
        "Data Science": ["data scien", "data analy", "statistics", "visualization"],
        "Mobile": ["android", "ios", "mobile", "kotlin", "swift", "react native"],
        "Frontend": ["react", "angular", "vue", "frontend", "front-end", "css", "ui/ux"],
        "Backend": ["backend", "back-end", "api", "microservice", "django", "flask", "spring"],
        "Full Stack": ["full stack", "fullstack"],
        "DevOps / Cloud": ["docker", "kubernetes", "aws", "azure", "gcp", "ci/cd", "devops"],
        "Data Engineering": ["data engineer", "etl", "pipeline", "spark", "kafka"],
    }
    for domain, keywords in domain_keywords.items():
        if any(kw in text for kw in keywords):
            domains.add(domain)
    return domains


def _detect_locations(text: str) -> set:
    """Detect preferred locations from resume."""
    locations = set()
    if "london" in text:
        locations.add("london")
    if "uk" in text or "united kingdom" in text:
        locations.add("uk")
    locations.add("remote")  # everyone wants remote
    return locations


# ═══════════════════════════════════════════════════════════
# SCORING ENGINE
# ═══════════════════════════════════════════════════════════

_profile_cache = None

def get_profile() -> dict:
    """Get cached profile (parsed once)."""
    global _profile_cache
    if _profile_cache is None:
        _profile_cache = load_profile()
        print(f"[Match] Profile loaded: {len(_profile_cache['skills'])} skills, "
              f"{_profile_cache['years_experience']}yr exp, "
              f"edu={_profile_cache['education_level']}, "
              f"domains={_profile_cache['domains']}")
    return _profile_cache


def reload_profile():
    """Force reload profile (after resume update)."""
    global _profile_cache
    _profile_cache = None
    if reload_retriever:
        try:
            reload_retriever()
        except Exception as exc:
            print(f"[Match] Retriever reload skipped: {exc}")
    return get_profile()


def score_job(job: dict) -> int:
    """
    Score a single job 0-100 using hybrid resume retrieval.

    Falls back to the original heuristic scorer if retrieval is unavailable.
    """
    query = _job_query(job)
    if get_retriever and query:
        try:
            score, _ = get_retriever().score_query(query, method=RETRIEVAL_METHOD)
            if score > 0:
                return score
        except Exception as exc:
            print(f"[Match] Hybrid scoring failed, using legacy score: {exc}")
    return _legacy_score_job(job)


def _legacy_score_job(job: dict) -> int:
    """
    Score a single job 0-100 based on profile match.
    Returns integer score.
    """
    profile = get_profile()
    title = (job.get("title", "") or "").lower()
    description = (job.get("full_description", "") or job.get("description_snippet", "") or "").lower()
    location = (job.get("location", "") or "").lower()
    job_type = (job.get("job_type", "") or "").lower()
    category = (job.get("category", "") or "")
    text = f"{title} {description}"

    skills_score = _score_skills(text, profile)
    level_score = _score_experience_level(title, job_type, profile)
    domain_score = _score_domain(category, text, profile)
    location_score = _score_location(location, profile)

    # Weighted total
    total = (
        skills_score * 0.40 +
        level_score * 0.25 +
        domain_score * 0.20 +
        location_score * 0.15
    )

    return max(0, min(100, round(total)))


def _score_skills(text: str, profile: dict) -> float:
    """Score 0-100 based on skill overlap."""
    if not profile["skills"]:
        return 50  # neutral if no skills extracted

    # Extract skills mentioned in the JD
    jd_skills = _extract_skills(text)

    if not jd_skills:
        return 50  # can't determine if JD has no recognized skills

    # How many JD skills does the candidate have?
    overlap = profile["skills"] & jd_skills
    match_ratio = len(overlap) / len(jd_skills)

    # Bonus if candidate has extra relevant skills
    extra_relevant = len(profile["skills"] & jd_skills)

    score = match_ratio * 85 + min(15, extra_relevant * 3)
    return min(100, score)


def _score_experience_level(title: str, job_type: str, profile: dict) -> float:
    """Score 0-100 based on experience level fit."""
    years = profile["years_experience"]
    edu = profile["education_level"]

    # Determine what the job expects
    is_intern = any(w in title for w in ["intern", "placement", "summer"])
    is_graduate = any(w in title for w in ["graduate", "junior", "entry", "trainee"]) or job_type == "graduate"
    is_mid = any(w in title for w in ["mid", "ii", " 2", "software engineer"]) and not is_graduate
    is_senior = any(w in title for w in ["senior", "sr.", "iii", " 3", "lead", "principal", "staff"])

    if is_intern:
        # Interns: students or very early career
        if edu in ("masters", "phd") or years <= 2:
            return 90
        return max(30, 90 - years * 15)

    if is_graduate:
        # Graduate roles: 0-2 years ideal
        if years <= 2:
            return 95
        elif years <= 4:
            return 70
        else:
            return max(20, 70 - (years - 4) * 15)

    if is_senior:
        # Senior: 5+ years ideal
        if years >= 5:
            return 90
        elif years >= 3:
            return 60
        else:
            return max(15, years * 15)

    # Mid-level or unspecified
    if years >= 1 and years <= 5:
        return 85
    elif years < 1:
        return 55
    else:
        return 75  # overqualified but still fine


def _score_domain(category: str, text: str, profile: dict) -> float:
    """Score 0-100 based on domain/category alignment."""
    if not profile["domains"]:
        return 50

    # Direct category match
    if category in profile["domains"]:
        return 95

    # Cross-domain relevance (e.g., ML person applying to Data Science)
    related = {
        "AI / ML": {"Data Science", "Data Engineering", "Backend", "Full Stack"},
        "Data Science": {"AI / ML", "Data Engineering", "Backend"},
        "Backend": {"Full Stack", "DevOps / Cloud", "Data Engineering"},
        "Frontend": {"Full Stack", "Mobile"},
        "Full Stack": {"Backend", "Frontend"},
        "Mobile": {"Frontend", "Full Stack"},
        "DevOps / Cloud": {"Backend", "Data Engineering"},
        "Data Engineering": {"Data Science", "AI / ML", "Backend", "DevOps / Cloud"},
    }

    for candidate_domain in profile["domains"]:
        related_cats = related.get(candidate_domain, set())
        if category in related_cats:
            return 70

    # Check text for domain keywords even if category doesn't match
    for domain in profile["domains"]:
        domain_lower = domain.lower()
        if domain_lower.split("/")[0].strip() in text:
            return 60

    return 30  # No domain overlap


def _score_location(location: str, profile: dict) -> float:
    """Score 0-100 based on location preference."""
    prefs = profile["preferred_locations"]

    if not location:
        return 50

    if "remote" in location:
        return 95

    for pref in prefs:
        if pref in location:
            return 95

    # UK locations get partial credit
    uk_cities = ["london", "cambridge", "oxford", "manchester", "edinburgh", "bristol",
                 "birmingham", "leeds", "glasgow", "reading", "cardiff", "belfast"]
    if any(city in location for city in uk_cities):
        return 80

    if "uk" in location or "united kingdom" in location:
        return 85

    # International
    return 25


# ═══════════════════════════════════════════════════════════
# BATCH SCORING
# ═══════════════════════════════════════════════════════════

def score_all_jobs(jobs: list[dict]) -> list[dict]:
    """Score all jobs and add match_score field. Returns jobs with scores."""
    profile = get_profile()  # ensure loaded

    if get_retriever:
        try:
            queries = [_job_query(job) for job in jobs]
            scores = get_retriever().score_queries(queries, method=RETRIEVAL_METHOD)
            for job, (score, _) in zip(jobs, scores):
                job["match_score"] = score or _legacy_score_job(job)
            return jobs
        except Exception as exc:
            print(f"[Match] Batch hybrid scoring failed, using legacy scores: {exc}")

    for job in jobs:
        job["match_score"] = score_job(job)

    return jobs


def get_score_breakdown(job: dict) -> dict:
    """Get detailed score breakdown for a single job."""
    profile = get_profile()
    title = (job.get("title", "") or "").lower()
    description = (job.get("full_description", "") or job.get("description_snippet", "") or "").lower()
    location = (job.get("location", "") or "").lower()
    job_type = (job.get("job_type", "") or "").lower()
    category = (job.get("category", "") or "")
    text = f"{title} {description}"

    jd_skills = _extract_skills(text)
    overlap = profile["skills"] & jd_skills
    missing = jd_skills - profile["skills"]

    retrieval_score = 0
    retrieval_results = []
    retrieval_error = ""
    if get_retriever:
        try:
            retrieval_score, retrieval_results = get_retriever().score_query(_job_query(job), method=RETRIEVAL_METHOD)
        except Exception as exc:
            retrieval_error = str(exc)

    return {
        "total_score": retrieval_score or _legacy_score_job(job),
        "method": RETRIEVAL_METHOD,
        "retrieval_score": retrieval_score,
        "legacy_score": _legacy_score_job(job),
        "retrieval_error": retrieval_error,
        "evidence": [result.as_dict() for result in retrieval_results],
        "skills_score": round(_score_skills(text, profile)),
        "level_score": round(_score_experience_level(title, job_type, profile)),
        "domain_score": round(_score_domain(category, text, profile)),
        "location_score": round(_score_location(location, profile)),
        "matching_skills": sorted(overlap),
        "missing_skills": sorted(missing),
        "your_skills_count": len(profile["skills"]),
        "jd_skills_count": len(jd_skills),
        "your_experience_years": profile["years_experience"],
        "your_domains": sorted(profile["domains"]),
        "job_category": category,
    }


def _job_query(job: dict) -> str:
    parts = [
        job.get("title", ""),
        job.get("company", ""),
        job.get("category", ""),
        job.get("job_type", ""),
        job.get("full_description", ""),
        job.get("description_snippet", ""),
    ]
    return "\n".join(str(part) for part in parts if part)[:4000]
