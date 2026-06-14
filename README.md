# Job Hunter

Job Hunter is a local-first application tracker that now combines scraping, Gmail status sync, hybrid resume retrieval, and a grounded LangGraph apply agent. It keeps the existing FastAPI backend, React dashboard, SQLite database, Groq-powered generation, and Gmail parsing, while adding agentic RAG and a reproducible evaluation harness.

## What It Does

- Scrapes jobs from Reed, Adzuna, Greenhouse, Gradcracker, and Otta/WTTJ into SQLite.
- Scores jobs against the resume with hybrid retrieval: dense Chroma vectors plus a from-scratch TF-IDF sparse retriever fused by RRF.
- Runs an apply agent that extracts JD requirements, retrieves resume evidence, drafts a cover letter, and returns exact cited resume chunks.
- Tracks application replies from Gmail and updates pipeline status.
- Evaluates retrieval and generation faithfulness with `python -m evals.run`.

## Architecture

```mermaid
flowchart TD
    Scrapers[Job scrapers] --> DB[(SQLite jobs.db)]
    Gmail[Gmail IMAP + Groq classifier] --> DB
    Resume[resume_base.tex] --> Chunker[Resume chunker]
    Chunker --> Sparse[TF-IDF sparse retriever]
    Chunker --> Dense[SentenceTransformers embeddings]
    Dense --> Chroma[(Local Chroma store)]
    Sparse --> RRF[RRF hybrid retrieval]
    Chroma --> RRF
    DB --> FastAPI[FastAPI routes]
    RRF --> FastAPI
    FastAPI --> React[React dashboard]
    FastAPI --> Agent[LangGraph apply agent]
    Agent --> Tools[JD fetch, retrieval, scoring, Gmail status]
    Tools --> Agent
    Agent --> Guard[Grounding guard]
    Guard --> React
    RRF --> Evals[Retrieval evals]
    Agent --> GenEvals[Faithfulness evals]
```

## Key Paths

| Area | Files |
|---|---|
| FastAPI routes | `server/app.py` |
| SQLite access | `server/database.py` |
| Hybrid retrieval | `server/hybrid_retriever.py`, `server/tfidf_retriever.py`, `server/vector_store.py` |
| Resume chunking | `server/resume_chunks.py` |
| Legacy + hybrid match scoring | `server/match_engine.py` |
| Groq Smart Apply | `server/apply_engine.py` |
| LangGraph apply agent | `server/job_agent.py`, `server/agent_tools.py`, `server/grounding.py` |
| Gmail sync | `server/gmail_tracker.py` |
| React dashboard | `dashboard/src/App.jsx`, `dashboard/src/components/JobRow.jsx`, `dashboard/src/components/AgentApplyPanel.jsx` |
| Evals | `evals/` |

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp scrapers/config.example.py scrapers/config.py
# Add keys in scrapers/config.py as needed:
# GROQ_API_KEY, REED_API_KEY, ADZUNA_APP_ID, ADZUNA_APP_KEY, Gmail credentials

cd dashboard
npm install
cd ..

./run.sh
```

Dashboard: `http://localhost:5173`
API docs: `http://localhost:8000/docs`

## Configuration

Environment variables override `scrapers/config.py`.

| Variable | Default |
|---|---|
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| `JUDGE_MODEL` | `llama-3.3-70b-versatile` |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| `EMBEDDING_FALLBACK_MODEL` | `all-MiniLM-L6-v2` |
| `VECTOR_STORE_PATH` | `data/chroma` |
| `VECTOR_COLLECTION` | `resume_chunks` |
| `RETRIEVAL_METHOD` | `hybrid` |
| `RETRIEVAL_K` | `6` |
| `RRF_K` | `60` |
| `RRF_DENSE_WEIGHT` | `1.0` |
| `RRF_SPARSE_WEIGHT` | `1.0` |

## Agent Endpoint

```bash
curl -X POST http://localhost:8000/agent/apply/{job_id}
```

The response includes:

- `cover_letter`
- `requirements`
- `citations`
- `evidence`
- `unsupported_claims_removed`
- `faithfulness_score`
- `match`

The dashboard exposes this in each expanded DB-backed job row as **Agent Apply**.

## Evals

Run the full harness:

```bash
python -m evals.run
```

Outputs are written to `evals/results/<timestamp>/`:

- `retrieval_results.md`
- `retrieval_results.csv`
- `generation_faithfulness.json`
- `summary.md`
- `summary.json`

Seed labels live in `evals/dataset.jsonl`. The file includes 30 examples: 15 labelled and 15 explicit TODOs for adding ground-truth relevance labels.

Baseline local run with Groq disabled and the local dense embedding model available:

| Method | Queries | Precision@k | Recall@k | MRR | nDCG |
|---|---:|---:|---:|---:|---:|
| dense | 15 | 0.3733 | 0.7667 | 0.8889 | 0.7403 |
| sparse | 15 | 0.3867 | 0.7778 | 0.9000 | 0.7804 |
| hybrid | 15 | 0.4133 | 0.8444 | 0.9667 | 0.8174 |

Generation baseline from the same deterministic local run:

| Examples | Average Faithfulness | Average JD Relevance |
|---:|---:|---:|
| 2 | 0.6667 | 1.0000 |

The hybrid row improves because RRF combines dense semantic matches with the exact TF-IDF lexical matches.

## Tests

```bash
pytest
python -m evals.run --generation-limit 2
```

The focused unit tests cover RRF fusion and the grounding guard. The eval command validates the end-to-end retrieval/generation harness.
