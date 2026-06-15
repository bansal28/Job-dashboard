from __future__ import annotations

import json
import re
from pathlib import Path

from server.llm_client import call_llm
from server.resume_chunks import load_resume_chunks
from server.settings import get_setting

from .schema import RetrievalExample


JUDGE_RUBRIC = """You are a strict factuality judge for job application cover letters.
Rubric:
- Extract candidate-specific factual claims from the letter.
- A claim is grounded only if it is directly supported by the resume evidence.
- Do not give credit for plausible but unstated facts.
- Report unsupported or hallucinated claims verbatim.
- Score faithfulness as grounded_claims / total_claims.
- Score JD relevance from 0 to 1 based on how well the letter addresses the listed job requirements.
Return only valid JSON with keys: claims, unsupported_claims, faithfulness_score, jd_relevance_score, rationale."""


def evaluate_generation(examples: list[RetrievalExample], limit: int = 5, backend: str = "llm") -> list[dict]:
    labelled = examples[:limit]
    results = []
    resume_text = "\n".join(chunk.text for chunk in load_resume_chunks())

    from server import job_agent

    original_status_tool = job_agent.check_application_status
    job_agent.check_application_status = lambda company: {"matches": [], "skipped": "eval harness disables Gmail"}  # type: ignore[assignment]
    try:
        for example in labelled:
            try:
                result = job_agent.run_apply_agent(example.job_id)
                letter = result.get("cover_letter", "")
                requirements = result.get("requirements", [example.query])
                judge = judge_cover_letter(
                    letter=letter,
                    resume_text=resume_text,
                    requirements=requirements,
                    backend=backend,
                )
                results.append({
                    "example_id": example.id,
                    "job_id": example.job_id,
                    "letter": letter,
                    "citations": result.get("citations", []),
                    "agent_faithfulness_score": result.get("faithfulness_score", 0),
                    **judge,
                })
            except Exception as exc:
                results.append({
                    "example_id": example.id,
                    "job_id": example.job_id,
                    "error": str(exc),
                    "claims": [],
                    "unsupported_claims": [],
                    "faithfulness_score": 0.0,
                    "jd_relevance_score": 0.0,
                })
    finally:
        job_agent.check_application_status = original_status_tool  # type: ignore[assignment]

    return results


def judge_cover_letter(letter: str, resume_text: str, requirements: list[str], backend: str = "llm") -> dict:
    if backend == "ragas":
        ragas_result = _try_ragas(letter, resume_text, requirements)
        if ragas_result:
            return ragas_result

    provider = None if backend == "llm" else backend
    try:
        return _judge_with_llm(letter, resume_text, requirements, provider=provider)
    except Exception as exc:
        heuristic = _judge_heuristically(letter, resume_text, requirements)
        heuristic["judge_error"] = str(exc)
        return heuristic


def write_generation_results(results: list[dict], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "generation_faithfulness.json"
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return path


def _judge_with_llm(letter: str, resume_text: str, requirements: list[str], provider: str | None = None) -> dict:
    judge_model = get_setting("JUDGE_MODEL", "") or None
    prompt = f"""Resume evidence:
{resume_text[:7000]}

JD requirements:
{json.dumps(requirements[:8], indent=2)}

Cover letter:
{letter}

Apply the rubric and return JSON only."""
    raw = call_llm(
        JUDGE_RUBRIC,
        prompt,
        max_tokens=1800,
        temperature=0,
        model=judge_model,
        provider=provider,
    ).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    parsed = json.loads(raw.strip())
    parsed["judge_backend"] = provider or "llm"
    parsed["judge_model"] = judge_model or "provider-default"
    return parsed


def _judge_heuristically(letter: str, resume_text: str, requirements: list[str]) -> dict:
    claims = _extract_claims(letter)
    resume_tokens = _tokens(resume_text)
    unsupported = []
    grounded = []
    for claim in claims:
        claim_tokens = _tokens(claim)
        threshold = 3 if re.search(r"\d", claim) else 2
        if len(claim_tokens & resume_tokens) >= threshold:
            grounded.append(claim)
        else:
            unsupported.append(claim)

    requirement_tokens = [_tokens(req) for req in requirements if req]
    letter_tokens = _tokens(letter)
    relevance_hits = sum(1 for tokens in requirement_tokens if len(tokens & letter_tokens) >= 2)
    relevance = relevance_hits / len(requirement_tokens) if requirement_tokens else 0.0
    total = len(claims)
    faithfulness = len(grounded) / total if total else 1.0
    return {
        "claims": claims,
        "unsupported_claims": unsupported,
        "faithfulness_score": round(faithfulness, 4),
        "jd_relevance_score": round(relevance, 4),
        "judge_backend": "heuristic",
        "rationale": "Lexical overlap fallback; configure OPENAI_API_KEY or GROQ_API_KEY for LLM-as-judge.",
    }


def _try_ragas(letter: str, resume_text: str, requirements: list[str]) -> dict | None:
    try:
        import ragas  # type: ignore  # noqa: F401
    except Exception:
        return None
    return {
        "claims": _extract_claims(letter),
        "unsupported_claims": [],
        "faithfulness_score": 0.0,
        "jd_relevance_score": 0.0,
        "judge_backend": "ragas",
        "rationale": "RAGAS is installed, but this lightweight hook needs project-specific dataset adaptation.",
    }


def _extract_claims(letter: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", letter) if part.strip()]
    return [
        sentence for sentence in sentences
        if re.search(r"\b(I|my|me|built|developed|trained|deployed|architected|implemented|created|engineered)\b", sentence, re.I)
    ]


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}", text)
        if token.lower() not in {"the", "and", "for", "with", "that", "this", "you", "your", "from"}
    }
