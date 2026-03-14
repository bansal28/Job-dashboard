# Job Hunter 🎯

An AI-powered job application automation system. Scrape jobs from multiple boards, filter with smart matching, generate tailored resumes & cover letters, and track application updates from your email — all from one dashboard.

Built with React, FastAPI, SQLite, and Groq (Llama 3.3 70B).

## Features

### 1. Multi-Source Job Scraping
- **Greenhouse** — Scrapes public job boards (Anthropic, DeepMind, Scale AI, Stripe, etc.)
- **Reed.co.uk** — UK job search API with location filtering
- **Adzuna** — Additional UK job coverage
- Auto-deduplication across sources
- Auto-categorization into AI/ML, Backend, Frontend, Mobile, DevOps, Data Science, etc.

### 2. Smart Dashboard with Excel-Style Filters
- Column filters with search, checkboxes, Select All — like Excel's auto-filter
- UK Only toggle — one click to filter to UK + remote jobs
- Sort by any column including match score
- Global text search across all fields
- Pagination (30 per page)

### 3. AI Match Scoring (0-100%)
Every job is scored against your resume — no API calls, runs instantly:
- **Skills match (40%)** — Compares your skills vs JD requirements
- **Experience level (25%)** — Graduate role + 2yr experience = high score
- **Domain alignment (20%)** — ML job + ML background = match
- **Location fit (15%)** — UK/Remote preference

Click any score to see a detailed breakdown with matching and missing skills.

### 4. Smart Apply (AI-Powered)
Click "Smart Apply" on any job to:
1. **Fetch the full job description** from the listing URL
2. **Extract ATS keywords** — must-have skills, tools, action verbs
3. **Generate tailored resume LaTeX** — rewords your bullets to match the JD
4. **Generate tailored cover letter LaTeX** — specific to company/role

Uses Groq API (free tier) with Llama 3.3 70B. Each application takes ~10 seconds.

### 5. Application Pipeline (Kanban)
Track jobs through stages: **Saved → Applied → Interview → Offer**
- Drag between columns
- Add notes per job
- Collapsed rejected section with restore

### 6. CSV Upload & Browse
Upload any job CSV (from LinkedIn, recruiters, university boards) and browse it with the same filters, match scoring, and Smart Apply. Persists across sessions via localStorage.

### 7. Gmail Email Tracker
Connects to your Gmail via IMAP, scans for application emails, and classifies them with AI:
- ✅ Acknowledgement
- 📝 Assignment / coding challenge
- 📅 Interview invitation
- ❌ Rejection
- 🎉 Offer

### 8. Deadline Tracking
Set application deadlines on any job. Color-coded warnings: red for "due today", yellow for "3 days left".

## Architecture

```
jobbot-claude/
├── server/                 # FastAPI backend
│   ├── app.py              # API endpoints
│   ├── database.py         # SQLite with dedup
│   ├── categorizer.py      # Auto-categorization & UK detection
│   ├── match_engine.py     # Resume-based match scoring
│   ├── apply_engine.py     # Smart Apply (Groq + JD fetching)
│   ├── gmail_tracker.py    # IMAP + AI classification
│   └── import_csv.py       # CSV → DB migration
├── scrapers/               # Job board scrapers
│   ├── greenhouse_scraper.py
│   ├── reed_scraper.py
│   ├── adzuna_scraper.py
│   ├── config.example.py   # Template (copy to config.py)
│   └── main.py             # CLI orchestrator
├── dashboard/              # React frontend (Vite)
│   └── src/
│       ├── App.jsx         # Root: sidebar + routing
│       ├── api.js          # Safe fetch wrappers
│       ├── theme.jsx       # Colors, icons, utilities
│       ├── components/     # Reusable UI
│       │   ├── JobTable.jsx
│       │   ├── JobRow.jsx
│       │   ├── ColumnFilter.jsx
│       │   ├── ApplyPanel.jsx
│       │   ├── ScrapePanel.jsx
│       │   └── FormField.jsx
│       └── views/          # Screens
│           ├── DiscoverView.jsx
│           ├── PipelineView.jsx
│           ├── AddJobView.jsx
│           ├── CsvUploadView.jsx
│           └── EmailTrackerView.jsx
├── templates/              # Your LaTeX templates (gitignored)
│   ├── resume_base.tex
│   └── cover_letter_base.tex
└── data/                   # SQLite database (gitignored)
    └── jobs.db
```

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- A [Groq API key](https://console.groq.com/keys) (free)
- A [Reed API key](https://www.reed.co.uk/developers) (free, optional)

### Installation

```bash
# Clone
git clone https://github.com/bansal28/Job-dashboard.git
cd Job-dashboard

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node dependencies
cd dashboard
npm install
cd ..

# Configuration
cp scrapers/config.example.py scrapers/config.py
# Edit scrapers/config.py and add your API keys
```

### Add Your Resume Templates

Create a `templates/` folder and add your LaTeX resume and cover letter:

```bash
mkdir templates
# Add your resume_base.tex and cover_letter_base.tex
```

The cover letter template should use `<<PLACEHOLDER>>` syntax for fields the AI will fill in.

### Configuration

Edit `scrapers/config.py`:

```python
# Required for Smart Apply
GROQ_API_KEY = "gsk_..."          # Free from console.groq.com/keys

# Optional — job scraping
REED_API_KEY = "..."              # Free from reed.co.uk/developers
ADZUNA_APP_ID = ""                # From developer.adzuna.com
ADZUNA_APP_KEY = ""

# Optional — email tracking
GMAIL_ADDRESS = ""                # Your job application email
GMAIL_APP_PASSWORD = ""           # From myaccount.google.com/apppasswords
```

### Run

```bash
# Terminal 1 — Backend
source .venv/bin/activate
uvicorn server.app:app --port 8000

# Terminal 2 — Frontend
cd dashboard
npm run dev
```

Or use the combined script:
```bash
./run.sh
```

Open [http://localhost:5173](http://localhost:5173)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List all jobs (with match scores) |
| POST | `/api/scrape` | Start scraping |
| GET | `/api/scrape/status` | Scrape progress |
| PATCH | `/api/jobs/{id}` | Update status/notes/deadline |
| POST | `/api/jobs` | Add manual job |
| DELETE | `/api/jobs/{id}` | Delete manual job |
| GET | `/api/match/{id}` | Match score breakdown |
| POST | `/api/match/batch` | Score arbitrary jobs |
| POST | `/api/apply/{id}` | Generate application (DB job) |
| POST | `/api/apply-direct` | Generate application (any job) |
| GET | `/api/apply/{id}` | Get generation result |
| POST | `/api/emails/scan` | Scan Gmail |
| GET | `/api/emails/status` | Email scan results |
| GET | `/api/filters` | Unique filter values |
| GET | `/api/stats` | Job count stats |

## Tech Stack

- **Frontend**: React 19, Vite 7, inline styles (no CSS framework)
- **Backend**: FastAPI, SQLite, Python 3
- **AI**: Groq API (Llama 3.3 70B) — free tier
- **Scraping**: Greenhouse API, Reed API, Adzuna API
- **Email**: Gmail IMAP + AI classification

## License

MIT