# Job Hunter 🎯

An AI-powered job application automation system that scrapes jobs from multiple boards, scores them against your resume using TF-IDF cosine similarity, generates tailored resumes & cover letters, tracks application emails, and syncs everything into one dashboard.

Built with **React + FastAPI + SQLite + Groq (Llama 3.3 70B)**.

---

## What Makes This Different

Most job boards show you listings. This tool **actively helps you get hired**:

- **ML-Powered Match Scoring** — Every job is scored 0-100% against your resume using TF-IDF vectorization and cosine similarity. Not keyword matching — real NLP document comparison.
- **Smart Apply** — One click generates a tailored LaTeX resume + cover letter using your base templates + the full JD, powered by Llama 3.3 70B via Groq (free API).
- **Gmail Pipeline Sync** — Scans your email, classifies responses (interview/rejection/offer), and auto-updates job statuses. Get a rejection email? The job is automatically marked as Rejected.
- **Intelligent Filtering** — Scraper-level spam detection removes training courses, recruitment ads, and senior roles. You see 200 relevant jobs instead of 2000 noise.
- **Today's Top Picks** — Daily curated top 10 recommendations ranked by match score + freshness + deadline urgency.

---

## Features

### 1. Multi-Source Job Scraping
- **Greenhouse** — Public API scraping (Anthropic, DeepMind, Scale AI, Stripe, Wayve, etc.)
- **Reed.co.uk** — UK job search API with location filtering
- **Adzuna** — Additional UK job coverage
- Aggressive spam filtering: blocks training courses, recruitment ads, senior roles, low-salary listings
- Auto-categorization: AI/ML, Data Science, Backend, Frontend, Mobile, DevOps, etc.
- Auto-deduplication across sources

### 2. ML Match Scoring (0-100%)
Every job is scored against your resume — **no API calls, runs instantly**:

| Component | Weight | Method |
|-----------|--------|--------|
| Document Similarity | 35% | TF-IDF cosine similarity (built from scratch) |
| Skill Overlap | 30% | Named skill extraction + set intersection |
| Experience Level | 15% | Seniority detection vs. your years of experience |
| Location Fit | 10% | UK/Remote preference matching |
| Domain Alignment | 10% | Category matching (AI/ML, Web, Data, etc.) |

Click any score to see a **detailed breakdown**: matching skills (green), missing skills (red), per-component scores with visual bars.

### 3. Smart Dashboard
- Excel-style column filters with search, checkboxes, select/deselect all
- UK Only toggle — one click to filter to UK + remote jobs
- Sort by any column including match score and deadline
- Delete irrelevant jobs directly
- Deadline column with color-coded urgency
- Pagination (30 per page)
- Global text search across all fields

### 4. Today's Top Picks
Curated daily recommendations at the top of the Discover page:
- Ranked by: match score + freshness (newer = higher) + deadline urgency
- Shows score ring, company, salary, freshness tag, and direct "Apply →" link
- Collapsible panel

### 5. Smart Apply (AI-Powered)
Click "Smart Apply" on any job:
1. **Fetches the full job description** from the listing URL (Greenhouse API / HTML scraping)
2. **Extracts ATS keywords** — must-have skills, tools, action verbs
3. **Generates tailored resume LaTeX** — rewords bullet points to match JD keywords
4. **Generates tailored cover letter LaTeX** — specific to company, role, and your experience

Uses **Groq API (free tier)** with Llama 3.3 70B. ~10 seconds per application.

### 6. Application Pipeline (Kanban)
Track jobs through stages: **Saved → Applied → Interview → Offer**
- Notes per job
- Follow-up dates per job, with overdue / due-this-week reminders
- Collapsed rejected section with restore
- Status syncs automatically from email scanning

### 7. CSV Upload & Browse
Upload any job CSV (LinkedIn export, recruiter list, university board) and browse with:
- Same match scoring, filters, and Smart Apply as the main Discover tab
- Multiple CSV support with localStorage persistence
- Auto-detects common column names (Title, Company, Location, etc.)

### 8. Gmail Email Tracker + Pipeline Sync
Connects to Gmail via IMAP, scans emails, classifies with AI:

| Category | Auto-Action |
|----------|-------------|
| ✅ Acknowledgement | Job marked as "Applied" |
| 📝 Assignment / Coding Challenge | Job marked as "Interview" |
| 📅 Interview Invitation | Job marked as "Interview" |
| ❌ Rejection | Job marked as "Rejected" |
| 🎉 Offer | Job marked as "Offer" |

**Company View**: All emails grouped by company with a vertical timeline showing progression (Acknowledged → Assignment → Interview → Rejection). Fuzzy company name matching handles variations like "Anthropic" vs "Anthropic Ltd".

### 9. Analytics Dashboard
- **Application funnel**: Discovered → Saved → Applied → Interview → Offer with conversion rates
- **AI Insights**: Auto-generated observations ("12% interview rate", "60% of apps are AI/ML roles", "15 jobs saved but not applied")
- **Category / city / source breakdowns** with bar charts
- **Top companies** applied to
- **Deadline list** with urgency indicators

### 10. Deadline Tracking
- Auto-extracted from Reed API expiry dates
- Manual deadline picker on any job
- Color-coded: red (today/overdue), yellow (3 days), cyan (this week)
- Sortable deadline column in the table

### 11. Follow-Up Reminders
- Add a follow-up date to saved/applied/interview jobs
- See overdue and due-this-week follow-ups in Discover and Pipeline
- Pipeline cards show compact follow-up badges so pending outreach is hard to miss

---

## Architecture

```
jobbot-claude/
├── server/                     # FastAPI backend
│   ├── app.py                  # 20+ API endpoints
│   ├── database.py             # SQLite with dedup + migrations
│   ├── match_engine.py         # TF-IDF scoring + skill gap analysis
│   ├── apply_engine.py         # Smart Apply (Groq + JD fetching)
│   ├── gmail_tracker.py        # IMAP + AI email classification
│   ├── categorizer.py          # Auto-categorization + UK detection
│   └── import_csv.py           # CSV → DB migration
├── scrapers/                   # Job board scrapers
│   ├── greenhouse_scraper.py   # Public Greenhouse boards API
│   ├── reed_scraper.py         # Reed API + spam filtering
│   ├── adzuna_scraper.py       # Adzuna API
│   ├── config.example.py       # Template (copy to config.py)
│   └── main.py                 # CLI orchestrator
├── dashboard/                  # React frontend (Vite)
│   └── src/
│       ├── App.jsx             # Root: sidebar + routing
│       ├── api.js              # Safe fetch wrappers
│       ├── theme.jsx           # Design system (glass aesthetic)
│       ├── components/
│       │   ├── JobTable.jsx    # Filterable / sortable table
│       │   ├── JobRow.jsx      # Expandable row + score + apply
│       │   ├── ColumnFilter.jsx # Excel-style dropdown filter
│       │   ├── ApplyPanel.jsx  # Smart Apply UI
│       │   ├── SmartPicks.jsx  # Daily top 10 recommendations
│       │   ├── ScrapePanel.jsx # Scrape controls
│       │   └── FormField.jsx   # Reusable form input
│       └── views/
│           ├── DiscoverView.jsx     # Scrape + picks + job table
│           ├── PipelineView.jsx     # Kanban board
│           ├── AnalyticsView.jsx    # Charts + insights
│           ├── AddJobView.jsx       # Manual job entry
│           ├── CsvUploadView.jsx    # CSV upload + browse
│           └── EmailTrackerView.jsx # Gmail scanner + company timeline
├── templates/                  # Your LaTeX templates (gitignored)
│   ├── resume_base.tex
│   └── cover_letter_base.tex
└── data/                       # SQLite database (gitignored)
    └── jobs.db
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 7, Plus Jakarta Sans + JetBrains Mono |
| Backend | FastAPI, SQLite, Python 3 |
| ML / NLP | TF-IDF (built from scratch), cosine similarity, skill taxonomy |
| AI Generation | Groq API — Llama 3.3 70B (free tier) |
| Scraping | Greenhouse API, Reed API, Adzuna API |
| Email | Gmail IMAP + LLM classification |

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- [Groq API key](https://console.groq.com/keys) (free — for Smart Apply + Email classification)
- [Reed API key](https://www.reed.co.uk/developers) (free — for UK job scraping)

### Installation

```bash
git clone https://github.com/bansal28/Job-dashboard.git
cd Job-dashboard

# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Node
cd dashboard && npm install && cd ..

# Config
cp scrapers/config.example.py scrapers/config.py
# Edit scrapers/config.py — add your API keys
```

### Resume Templates

```bash
mkdir -p templates
# Add your resume_base.tex and cover_letter_base.tex
# The resume is parsed for match scoring
# The cover letter template uses <<PLACEHOLDER>> syntax
```

### Configuration

Edit `scrapers/config.py`:

```python
GROQ_API_KEY = "gsk_..."           # Free from console.groq.com/keys
REED_API_KEY = "..."               # Free from reed.co.uk/developers

# Optional — email tracking
GMAIL_ADDRESS = "your@gmail.com"
GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"  # From myaccount.google.com/apppasswords
```

### Run

```bash
# Terminal 1 — Backend
source .venv/bin/activate
uvicorn server.app:app --port 8000

# Terminal 2 — Frontend
cd dashboard && npm run dev
```

Open **http://localhost:5173**

---

## ML Implementation Details

### TF-IDF Engine (Built from Scratch)

The match scoring uses a custom TF-IDF implementation (~100 lines, no sklearn dependency):

1. **Tokenization** — Strips LaTeX commands, removes 200+ stopwords including job-posting fluff ("responsibilities", "qualifications", "excellent")
2. **IDF Computation** — `log((N+1) / (df+1)) + 1` with Laplace smoothing
3. **Sparse Vector Representation** — Dictionary-based for memory efficiency
4. **Cosine Similarity** — `dot(a,b) / (|a| × |b|)`

### Skill Gap Analysis

When you click a match score, the engine:
- Extracts recognized skills from both resume and JD (150+ skills in taxonomy across 8 categories)
- Groups missing skills by category (Languages, ML Frameworks, Cloud/DevOps, Databases, etc.)
- Identifies **emphasis gaps** — JD terms with high TF-IDF weight but low weight in your resume
- Shows matching skills (green tags) and missing skills (red tags)

### Scoring Pipeline

```
Resume (.tex) ──→ Clean + Tokenize ──→ TF-IDF Vector ─┐
                                                        ├─→ Cosine Similarity (35%)
Job Description ──→ Clean + Tokenize ──→ TF-IDF Vector ┘
                     │
                     ├──→ Skill Extraction ──→ Overlap Score (30%)
                     ├──→ Title Parsing ──→ Level Match (15%)
                     ├──→ Location Parse ──→ Location Score (10%)
                     └──→ Category Map ──→ Domain Score (10%)
                                              │
                                              ▼
                                    Weighted Sum = Final Score (0-100%)
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/jobs` | List all jobs with match scores |
| `GET` | `/api/picks` | Today's top 10 recommendations |
| `POST` | `/api/scrape` | Start scraping |
| `GET` | `/api/scrape/status` | Scrape progress |
| `PATCH` | `/api/jobs/{id}` | Update status / notes / deadline |
| `POST` | `/api/jobs` | Add manual job |
| `DELETE` | `/api/jobs/{id}` | Delete job |
| `GET` | `/api/match/{id}` | Match score breakdown |
| `POST` | `/api/match/batch` | Score arbitrary jobs (CSV) |
| `POST` | `/api/match/reload` | Reload resume profile |
| `POST` | `/api/apply/{id}` | Generate application (DB job) |
| `POST` | `/api/apply-direct` | Generate application (any job) |
| `GET` | `/api/apply/{id}` | Get generation result |
| `POST` | `/api/emails/scan` | Scan Gmail + classify + sync pipeline |
| `GET` | `/api/emails/status` | Email scan results |
| `GET` | `/api/analytics` | Full analytics data |
| `GET` | `/api/deadlines/upcoming` | Upcoming deadlines |
| `GET` | `/api/filters` | Unique filter values |
| `GET` | `/api/stats` | Job count stats |

---

## License

MIT
