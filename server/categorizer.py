"""
Smart job categorizer and location normalizer.
Auto-tags every job with:
  - category: AI/ML, Data Science, Software Engineering, etc.
  - city: Normalized UK city name (or "Remote", "International")
  - is_uk: Boolean for quick UK filtering
"""

import re

# ═══════════════════════════════════════════════════════════
# JOB CATEGORIES
# Order matters — first match wins (most specific first)
# ═══════════════════════════════════════════════════════════

CATEGORIES = {
    "AI / ML": [
        "machine learning", "ml engineer", "ml scientist", "ml research",
        "ml ops", "mlops", "ml platform", "ml infrastructure",
        "artificial intelligence", " ai engineer", "ai research", "ai scientist",
        "ai safety", "ai infrastructure", "ai platform",
        "deep learning", "neural net", "computer vision",
        "nlp", "natural language", "language model", "llm",
        "reinforcement learning", "generative ai", "gen ai",
        "ai product", "ai intern", "ml intern",
        "applied scientist", "research scientist", "research engineer",
        "pytorch", "tensorflow", "model training",
    ],
    "Data Science": [
        "data scientist", "data science", "data analyst",
        "business intelligence", " bi developer", "bi engineer",
        "analytics engineer", "insight analyst", "quantitative analyst",
        "statistician", "decision scientist",
    ],
    "Data Engineering": [
        "data engineer", "data platform", "data infrastructure",
        "etl", "data pipeline", "data warehouse", "dbt ",
        "airflow", "spark engineer", "kafka",
        "database engineer", "database admin",
    ],
    "Backend": [
        "backend", "back-end", "back end",
        "server-side", "api engineer", "api developer",
        "microservices", "distributed systems",
        "golang engineer", "rust engineer", "java engineer",
        "python engineer", "node.js engineer",
    ],
    "Frontend": [
        "frontend", "front-end", "front end",
        "ui engineer", "ui developer",
        "react developer", "react engineer",
        "vue developer", "angular developer",
        "javascript engineer", "typescript engineer",
        "web developer", "web engineer",
    ],
    "Full Stack": [
        "full stack", "fullstack", "full-stack",
    ],
    "Mobile": [
        "mobile engineer", "mobile developer",
        "ios engineer", "ios developer",
        "android engineer", "android developer",
        "react native", "flutter developer",
        "swift developer", "kotlin developer",
    ],
    "DevOps / Cloud / SRE": [
        "devops", "dev ops", "site reliability", "sre ",
        "platform engineer", "infrastructure engineer",
        "cloud engineer", "cloud architect",
        "kubernetes", "docker engineer", "terraform",
        "aws engineer", "azure engineer", "gcp engineer",
        "systems engineer", "linux engineer",
        "release engineer", "build engineer",
    ],
    "Security": [
        "security engineer", "cybersecurity", "cyber security",
        "infosec", "penetration test", "security analyst",
        "appsec", "application security", "soc analyst",
        "threat", "vulnerability",
    ],
    "QA / Testing": [
        "qa engineer", "quality assurance", "test engineer",
        "sdet", "automation test", "test lead",
        "quality engineer",
    ],
    "Embedded / Hardware": [
        "embedded", "firmware", "hardware engineer",
        "fpga", "asic", "chip design",
        "robotics engineer", "control systems",
        "signal processing", "dsp engineer",
    ],
    "Product / Design": [
        "product manager", "product owner",
        "ux engineer", "ux designer", "ui/ux",
        "design engineer", "product designer",
        "technical product",
    ],
    "Software Engineering": [
        # Broadest catch-all for SWE — goes last
        "software engineer", "software developer",
        "senior engineer", "staff engineer", "principal engineer",
        "engineering manager", "tech lead", "technical lead",
        "solutions engineer", "solutions architect",
        "developer", "programmer", "coder",
    ],
}

NON_TECH_TITLE_KEYWORDS = [
    "account executive", "sales", "business development", "partnership",
    "community manager", "advocate", "marketing", "recruiter", "talent",
    "people partner", "legal", "counsel", "finance", "deal desk",
    "customer success", "support manager",
]

TECHNICAL_ROLE_NOUNS = [
    "engineer", "developer", "scientist", "research", "architect",
    "sre", "devops", "programmer", "analyst", "security",
]

# ═══════════════════════════════════════════════════════════
# UK CITIES & LOCATION NORMALIZATION
# ═══════════════════════════════════════════════════════════

UK_CITIES = {
    # London
    "london": "London",
    "city of london": "London",
    "east london": "London",
    "west london": "London",
    "north london": "London",
    "south london": "London",
    "central london": "London",
    "canary wharf": "London",
    "shoreditch": "London",
    "king's cross": "London",
    "kings cross": "London",
    "paddington": "London",
    "westminster": "London",

    # Major cities
    "manchester": "Manchester",
    "birmingham": "Birmingham",
    "leeds": "Leeds",
    "glasgow": "Glasgow",
    "liverpool": "Liverpool",
    "bristol": "Bristol",
    "sheffield": "Sheffield",
    "edinburgh": "Edinburgh",
    "cardiff": "Cardiff",
    "belfast": "Belfast",
    "newcastle": "Newcastle",
    "newcastle upon tyne": "Newcastle",
    "nottingham": "Nottingham",
    "southampton": "Southampton",
    "brighton": "Brighton",
    "brighton and hove": "Brighton",
    "leicester": "Leicester",
    "portsmouth": "Portsmouth",
    "coventry": "Coventry",
    "bath": "Bath",

    # Tech hubs
    "cambridge": "Cambridge",
    "oxford": "Oxford",
    "reading": "Reading",
    "slough": "Slough",
    "guildford": "Guildford",
    "bracknell": "Bracknell",
    "basingstoke": "Basingstoke",
    "milton keynes": "Milton Keynes",
    "swindon": "Swindon",
    "hatfield": "Hatfield",
    "stevenage": "Stevenage",
    "watford": "Watford",
    "st albans": "St Albans",
    "croydon": "Croydon",
    "woking": "Woking",
    "farnborough": "Farnborough",
    "fareham": "Fareham",
    "ipswich": "Ipswich",
    "norwich": "Norwich",
    "exeter": "Exeter",
    "cheltenham": "Cheltenham",
    "warwick": "Warwick",
    "leamington": "Leamington Spa",

    # Scotland
    "aberdeen": "Aberdeen",
    "dundee": "Dundee",
    "stirling": "Stirling",

    # Northern England
    "york": "York",
    "hull": "Hull",
    "bradford": "Bradford",
    "sunderland": "Sunderland",
    "durham": "Durham",
    "middlesbrough": "Middlesbrough",
    "lancaster": "Lancaster",
    "preston": "Preston",
    "chester": "Chester",
    "bolton": "Bolton",

    # Wales
    "swansea": "Swansea",
    "newport": "Newport",
}

UK_INDICATORS = [
    "uk", "u.k.", "united kingdom", "england", "scotland", "wales",
    "northern ireland", "great britain", "britain",
] + list(UK_CITIES.keys())

REMOTE_INDICATORS = ["remote", "work from home", "wfh", "anywhere", "distributed"]


def categorize_job(title: str, description: str = "") -> str:
    """Return the best category for a job based on title and description."""
    title_text = f" {title.lower()} "
    is_technical_title = any(keyword in title_text for keyword in TECHNICAL_ROLE_NOUNS)

    if any(keyword in title_text for keyword in NON_TECH_TITLE_KEYWORDS) and not is_technical_title:
        return "Other"

    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in title_text:
                return category

    if not is_technical_title:
        return "Other"

    text = f"{title_text} {description[:500].lower()} "

    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if kw in text:
                return category

    return "Other"


def extract_city(location: str) -> str:
    """Extract normalized UK city from location string."""
    if not location:
        return ""

    loc = location.lower().strip()

    # Check for remote
    if any(r in loc for r in REMOTE_INDICATORS):
        # Could be "London (Remote)" — check for city too
        for pattern, city in UK_CITIES.items():
            if pattern in loc:
                return f"{city} (Remote)"
        return "Remote"

    # Check for UK cities
    for pattern, city in UK_CITIES.items():
        if pattern in loc:
            return city

    return ""


def is_uk_job(location: str, title: str = "") -> bool:
    """Check if a job is UK-based or remote-friendly."""
    text = f"{location} {title}".lower()

    # Definitely UK
    if any(ind in text for ind in UK_INDICATORS):
        return True

    # Check for international cities that are NOT UK
    non_uk = ["san francisco", "new york", "seattle", "toronto",
              "paris", "berlin", "amsterdam", "dublin", "singapore",
              "sydney", "tokyo", "bangalore", "hyderabad", "mumbai",
              " ca ", " ny ", " wa ", " tx "]
    if any(c in text for c in non_uk):
        return False

    # "Remote" without location could be anywhere
    if any(r in text for r in REMOTE_INDICATORS):
        return True  # Include remote jobs

    return False


def normalize_job_type(job_type: str, title: str = "") -> str:
    """Normalize job type to standard categories."""
    text = f"{job_type} {title}".lower()

    if any(w in text for w in ["intern", "placement", "summer"]):
        return "Internship"
    if any(w in text for w in ["graduate", "grad scheme", "grad programme", "new grad", "entry level", "junior", "trainee"]):
        return "Graduate"
    if any(w in text for w in ["contract", "fixed term", "freelance", "temporary"]):
        return "Contract"
    if any(w in text for w in ["part time", "part-time"]):
        return "Part-time"

    return "Full-time"


def enrich_job(job: dict) -> dict:
    """Add category, city, is_uk, and normalized job_type to a job dict."""
    title = job.get("title", "")
    location = job.get("location", "")
    description = job.get("description_snippet", "")
    job_type = job.get("job_type", "")

    job["category"] = categorize_job(title, description)
    job["city"] = extract_city(location)
    job["is_uk"] = "1" if is_uk_job(location, title) else "0"
    job["job_type"] = normalize_job_type(job_type, title)

    return job
