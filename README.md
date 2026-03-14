# 🔷 Job Hunter — Automated Job Application Pipeline

A 3-step system for automating your job search: **Scrape → Apply → Track**

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  STEP 1: SCRAPE                                      │
│  ┌───────────┐ ┌──────────┐ ┌─────────────┐         │
│  │ Reed API  │ │ Adzuna   │ │ Greenhouse  │         │
│  │ (UK jobs) │ │ (global) │ │ (direct ATS)│         │
│  └─────┬─────┘ └────┬─────┘ └──────┬──────┘         │
│        └─────────────┼──────────────┘                │
│                      ▼                               │
│              ┌──────────────┐                        │
│              │   jobs.csv   │                        │
│              └──────┬───────┘                        │
│                     ▼                                │
│          ┌───────────────────┐                       │
│          │  Dashboard UI     │ ← filters, sort,     │
│          │  (React/Browser)  │   search, status      │
│          └────────┬──────────┘                       │
└───────────────────┼──────────────────────────────────┘
                    ▼
┌──────────────────────────────────────────────────────┐
│  STEP 2: SMART APPLY (coming next)                   │
│  Click APPLY → extract keywords from JD →            │
│  generate tailored CV + cover letter (via Claude)    │
└──────────────────────────────────────────────────────┘
                    ▼
┌──────────────────────────────────────────────────────┐
│  STEP 3: EMAIL TRACKER                               │
│  Gmail IMAP → classify emails →                      │
│  track: ack / assignment / interview / rejection     │
└──────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install dependencies

```bash
cd job-hunter
pip install -r requirements.txt
```

### 2. Get API keys

| Source | How to get | Free tier |
|--------|-----------|-----------|
| **Greenhouse** | No key needed! | Unlimited (public API) |
| **Reed.co.uk** | https://www.reed.co.uk/developers | 5,000 req/day |
| **Adzuna** | https://developer.adzuna.com/ | 250 req/day |

### 3. Configure

Edit `scrapers/config.py`:
- Add your API keys for Reed and Adzuna
- Customize `SEARCH_QUERIES` and `LOCATIONS`
- Add/remove companies in `GREENHOUSE_BOARDS`

### 4. Run scrapers

```bash
cd scrapers

# Run everything (Greenhouse works without API keys!)
python main.py

# Or run specific sources
python main.py --greenhouse   # No API key needed
python main.py --reed
python main.py --adzuna

# Append to existing CSV (preserves old data)
python main.py --append
```

Output: `output/jobs.csv`

### 5. View in Dashboard

Open the React dashboard (`job-hunter-dashboard.jsx`) in Claude.ai or copy to your local React project. Click **Import CSV** to load your scraped `jobs.csv`.

### 6. Track emails (Step 3)

```bash
# Set Gmail credentials in config.py first
python email_tracker.py
```

## Adding Greenhouse Companies

Find a company's Greenhouse board token from their careers page URL:
- `https://boards.greenhouse.io/anthropic` → token = `anthropic`
- `https://boards.greenhouse.io/deepmind` → token = `deepmind`

Add to `GREENHOUSE_BOARDS` in `config.py`.

## File Structure

```
job-hunter/
├── scrapers/
│   ├── config.py              # API keys & search preferences
│   ├── main.py                # Orchestrator — runs all scrapers
│   ├── reed_scraper.py        # Reed.co.uk API
│   ├── adzuna_scraper.py      # Adzuna API
│   ├── greenhouse_scraper.py  # Greenhouse boards (free!)
│   └── email_tracker.py       # Gmail IMAP scanner
├── output/
│   ├── jobs.csv               # Scraped jobs (auto-generated)
│   └── email_tracker.csv      # Email classifications
├── templates/                 # (Step 2) CV/cover letter templates
├── requirements.txt
└── README.md
```

## What's Next

- **Step 2**: Smart Apply — Claude API extracts JD keywords, generates tailored CV + cover letter
- **Step 3 upgrade**: Replace keyword classification with Claude API for better email parsing
- **Scheduling**: Cron job to auto-scrape daily
- **More sources**: Indeed (RSS), LinkedIn (manual), company career pages
