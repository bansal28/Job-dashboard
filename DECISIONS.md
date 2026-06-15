# Decisions

## Chroma vs Qdrant/Pinecone

Chroma is local and persistent, so it fits this repo's SQLite/local-dashboard posture without requiring a separate server or paid hosted API. Qdrant is stronger for production vector operations and Pinecone is simpler to operate at scale, but both add deployment or account overhead that is unnecessary for a personal job-hunting tool.

## bge-small vs Larger Embedding Models

`BAAI/bge-small-en-v1.5` is a strong default because it is small enough for local CPU use while still being purpose-built for retrieval. Larger embedding models may improve ranking quality, but they increase install size, first-run model download time, and local latency; `all-MiniLM-L6-v2` remains the fallback for compatibility.

## RRF for Fusion

Reciprocal Rank Fusion keeps dense and sparse retrievers independent and combines their rankings without needing score calibration. The tradeoff is that it ignores absolute score magnitude, so a weak rank-one hit can still matter; this is acceptable here because the sparse and dense lists are both over the same small, high-signal resume chunks.

## LangGraph

LangGraph makes the apply flow explicit as fetch, extract, retrieve, score, draft, and guard nodes, with a retry edge if grounding fails. A simpler function pipeline would be easier to read, but the graph gives a clean place to add future tool calls, approval gates, and evaluation traces.

## Resume Chunk Size

The chunker uses one resume bullet, skill line, education line, or project bullet per chunk, with metadata for section, role, and company. This keeps citations exact and auditable, but it may split context across adjacent bullets; RRF retrieval with `k=6` offsets that by returning multiple chunks per requirement.

## Judge Model

The judge uses the same configurable LLM provider path as generation: OpenAI when `OPENAI_API_KEY` is configured, otherwise Groq when `GROQ_API_KEY` is configured. The tradeoff is possible judge/model correlation with the generator; the harness isolates the judge prompt and `JUDGE_MODEL` so a different evaluator can be forced for independent scoring.

## Intake Gate vs Showing Every Job

The scraper can scan a large market, but the dashboard now works from a ranked review queue instead of presenting every raw hit. The tradeoff is that low-scoring jobs are less visible by default, but this matches the actual job-search workflow: review a small set of plausible applications and keep the full database only for dedupe and analytics.

## Approval Queue vs Blind Auto-Apply

The app uses an `Approved` status as the explicit human gate before any application work. This avoids accidental submissions and keeps generated materials tied to a reviewed job, while still leaving room for browser-assisted workflows later where the user has provided complete profile answers and reviewed each target.

## Application Plans vs Direct Submission

For Greenhouse, public API reads can retrieve job posts and application questions, but API submission requires the hiring company's Job Board API key. Because this app is used by an applicant, not by the hiring company, the safe default is to prepare the application package and form answers, then open the listing for final review/submission.
