"""
Configuration for Job Hunter scrapers and services.
Copy this file to config.py and fill in your API keys:
    cp config.example.py config.py
"""

# ─── API KEYS ────────────────────────────────────────────────
REED_API_KEY = ""          # Free from https://www.reed.co.uk/developers
ADZUNA_APP_ID = ""         # Free from https://developer.adzuna.com/
ADZUNA_APP_KEY = ""

# ─── SEARCH QUERIES (for Reed & Adzuna) ─────────────────────
SEARCH_QUERIES = [
    "machine learning engineer",
    "AI engineer",
    "data scientist",
    "NLP engineer",
    "deep learning",
    "computer vision engineer",
    "software engineer",
    "software developer",
    "backend engineer",
    "frontend engineer",
    "full stack developer",
    "data engineer",
    "data analyst",
    "DevOps engineer",
    "cloud engineer",
    "SRE engineer",
    "mobile developer",
    "iOS developer",
    "android developer",
    "graduate software engineer",
    "graduate data scientist",
    "technology graduate scheme",
    "software internship",
    "data science internship",
]

# ─── LOCATIONS ───────────────────────────────────────────────
LOCATIONS = [
    "London",
    "Manchester",
    "Birmingham",
    "Edinburgh",
    "Cambridge",
    "Bristol",
    "Leeds",
    "Glasgow",
    "Oxford",
    "Remote",
]
DISTANCE_MILES = 25

# ─── GREENHOUSE BOARDS ──────────────────────────────────────
# Greenhouse's public API is board-scoped. Presets provide the large candidate
# universe; GREENHOUSE_BOARDS is for custom additions.
GREENHOUSE_BOARD_PRESETS = ["europe_tech"]
GREENHOUSE_MAX_WORKERS = 12
GREENHOUSE_BOARDS = [
    # Add extra board tokens here, e.g. "my-favourite-startup".
]

# ─── INTAKE GATE ────────────────────────────────────────────
# Scrapers can scan a large market, but only jobs above this score are inserted
# into the review queue. Set SCRAPE_MAX_JOBS=0 if you deliberately want no cap.
SCRAPE_MIN_MATCH_SCORE = "50"
SCRAPE_MAX_JOBS = "250"
DASHBOARD_MIN_MATCH_SCORE = "50"
DASHBOARD_MAX_NEW_JOBS = "250"

# ─── OUTPUT ─────────────────────────────────────────────────
OUTPUT_DIR = "output"
OUTPUT_CSV = "output/jobs.csv"
MAX_RESULTS_PER_QUERY = 50

# ─── LLM API (Smart Apply / Agent / Evals) ─────────────────
# Use either OpenAI or Groq. LLM_PROVIDER="auto" prefers OpenAI when both keys exist.
OPENAI_API_KEY = ""
GROQ_API_KEY = ""
LLM_PROVIDER = "auto"  # auto | openai | groq

# ─── RAG / AGENT SETTINGS (optional; env vars override these) ───────────────
OPENAI_MODEL = "gpt-5.4-mini"
GROQ_MODEL = "llama-3.3-70b-versatile"
JUDGE_MODEL = ""  # empty uses the active provider's default model
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_FALLBACK_MODEL = "all-MiniLM-L6-v2"
VECTOR_STORE_PATH = "data/chroma"
VECTOR_COLLECTION = "resume_chunks"
RETRIEVAL_METHOD = "hybrid"
RETRIEVAL_K = "6"
RRF_K = "60"
RRF_DENSE_WEIGHT = "1.0"
RRF_SPARSE_WEIGHT = "1.0"

# ─── GMAIL (Email Tracker) ─────────────────────────────────
# Enable IMAP in Gmail settings, then generate App Password:
# https://myaccount.google.com/apppasswords (requires 2FA)
GMAIL_ADDRESS = ""
GMAIL_APP_PASSWORD = ""
