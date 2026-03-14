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

# ─── GREENHOUSE COMPANIES ───────────────────────────────────
GREENHOUSE_BOARDS = [
    "anthropic",
    "deepmind",
    "scaleai",
    "snorkelai",
    "databricks",
    "thinkingmachines",
    "wayve",
    "stripe",
]

# ─── OUTPUT ─────────────────────────────────────────────────
OUTPUT_DIR = "output"
OUTPUT_CSV = "output/jobs.csv"
MAX_RESULTS_PER_QUERY = 50

# ─── GROQ API (Smart Apply — FREE) ─────────────────────────
# Get free key from https://console.groq.com/keys
GROQ_API_KEY = ""

# ─── GMAIL (Email Tracker) ─────────────────────────────────
# Enable IMAP in Gmail settings, then generate App Password:
# https://myaccount.google.com/apppasswords (requires 2FA)
GMAIL_ADDRESS = ""
GMAIL_APP_PASSWORD = ""