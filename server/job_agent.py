"""
LangGraph application agent.

The graph fetches the JD, extracts requirements, retrieves resume evidence,
drafts a grounded cover letter, and filters unsupported claims before returning
citations.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, TypedDict

try:
    from .agent_tools import (
        check_application_status,
        fetch_job_description_tool,
        retrieve_resume_evidence,
        score_match,
    )
    from .grounding import enforce_grounding
    from .settings import GROQ_API_KEY, GROQ_MODEL, RETRIEVAL_K
except ImportError:  # pragma: no cover
    from agent_tools import (
        check_application_status,
        fetch_job_description_tool,
        retrieve_resume_evidence,
        score_match,
    )
    from grounding import enforce_grounding
    from settings import GROQ_API_KEY, GROQ_MODEL, RETRIEVAL_K


class ApplyAgentState(TypedDict, total=False):
    job_id: str
    job: dict
    job_description: str
    requirements: list[str]
    evidence: list[dict]
    match: dict
    application_status: dict
    draft: str
    grounded_letter: str
    citations: list[dict]
    unsupported_claims: list[str]
    grounding_passed: bool
    faithfulness_score: float
    attempts: int
    errors: list[str]


def run_apply_agent(job_id: str) -> dict:
    initial: ApplyAgentState = {"job_id": job_id, "attempts": 0, "errors": []}
    graph = _build_graph()
    if graph:
        state = graph.invoke(initial)
    else:
        state = _run_sequential(initial)
    return _format_response(state)


def _build_graph():
    try:
        from langgraph.graph import END, StateGraph  # type: ignore
    except Exception:
        return None

    workflow = StateGraph(ApplyAgentState)
    workflow.add_node("fetch_job_description", _fetch_job_description_node)
    workflow.add_node("extract_requirements", _extract_requirements_node)
    workflow.add_node("retrieve_resume_evidence", _retrieve_evidence_node)
    workflow.add_node("score_match", _score_match_node)
    workflow.add_node("check_application_status", _check_status_node)
    workflow.add_node("draft_cover_letter", _draft_cover_letter_node)
    workflow.add_node("grounding_guard", _grounding_guard_node)

    workflow.set_entry_point("fetch_job_description")
    workflow.add_edge("fetch_job_description", "extract_requirements")
    workflow.add_edge("extract_requirements", "retrieve_resume_evidence")
    workflow.add_edge("retrieve_resume_evidence", "score_match")
    workflow.add_edge("score_match", "check_application_status")
    workflow.add_edge("check_application_status", "draft_cover_letter")
    workflow.add_edge("draft_cover_letter", "grounding_guard")
    workflow.add_conditional_edges(
        "grounding_guard",
        _guard_route,
        {"retry": "draft_cover_letter", "done": END},
    )
    return workflow.compile()


def _run_sequential(state: ApplyAgentState) -> ApplyAgentState:
    for node in (
        _fetch_job_description_node,
        _extract_requirements_node,
        _retrieve_evidence_node,
        _score_match_node,
        _check_status_node,
        _draft_cover_letter_node,
        _grounding_guard_node,
    ):
        state = node(state)
        if _guard_route(state) == "retry":
            state = _draft_cover_letter_node(state)
            state = _grounding_guard_node(state)
    return state


def _fetch_job_description_node(state: ApplyAgentState) -> ApplyAgentState:
    data = fetch_job_description_tool(state["job_id"])
    return {**state, "job": data["job"], "job_description": data["job_description"]}


def _extract_requirements_node(state: ApplyAgentState) -> ApplyAgentState:
    jd = state.get("job_description", "")
    title = state.get("job", {}).get("title", "")
    requirements = _extract_requirements(jd, title)
    return {**state, "requirements": requirements}


def _retrieve_evidence_node(state: ApplyAgentState) -> ApplyAgentState:
    evidence_by_id: dict[str, dict] = {}
    requirements = state.get("requirements", [])
    if not requirements:
        requirements = [state.get("job_description", "")]

    for requirement in requirements[:8]:
        for hit in retrieve_resume_evidence(requirement, k=min(RETRIEVAL_K, 6)):
            hit = {**hit, "requirement": requirement}
            evidence_by_id.setdefault(hit["id"], hit)

    return {**state, "evidence": list(evidence_by_id.values())[:12]}


def _score_match_node(state: ApplyAgentState) -> ApplyAgentState:
    try:
        match = score_match(state["job_id"])
    except Exception as exc:
        match = {"error": str(exc)}
    return {**state, "match": match}


def _check_status_node(state: ApplyAgentState) -> ApplyAgentState:
    company = state.get("job", {}).get("company", "")
    if not company:
        return {**state, "application_status": {"matches": []}}
    return {**state, "application_status": check_application_status(company)}


def _draft_cover_letter_node(state: ApplyAgentState) -> ApplyAgentState:
    attempts = int(state.get("attempts", 0)) + 1
    draft = _draft_grounded_letter(
        job=state.get("job", {}),
        job_description=state.get("job_description", ""),
        requirements=state.get("requirements", []),
        evidence=state.get("evidence", []),
        unsupported_claims=state.get("unsupported_claims", []),
    )
    return {**state, "draft": draft, "attempts": attempts}


def _grounding_guard_node(state: ApplyAgentState) -> ApplyAgentState:
    evidence = state.get("evidence", [])
    evidence_texts = [item.get("text", "") for item in evidence]
    report = enforce_grounding(state.get("draft", ""), evidence_texts)
    citations = _citations_for_letter(report.grounded_letter, evidence)
    return {
        **state,
        "grounded_letter": report.grounded_letter,
        "unsupported_claims": report.unsupported_claims,
        "grounding_passed": report.passed,
        "faithfulness_score": report.faithfulness_score,
        "citations": citations,
    }


def _guard_route(state: ApplyAgentState) -> str:
    if not state.get("grounding_passed", False) and int(state.get("attempts", 0)) < 2:
        return "retry"
    return "done"


def _extract_requirements(jd: str, title: str) -> list[str]:
    api_key = GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
    if api_key:
        system = "Extract concise job requirements. Return only a JSON array of strings."
        prompt = f"Job title: {title}\n\nJob description:\n{jd[:5000]}\n\nReturn 5-8 key requirements as JSON strings."
        try:
            raw = _call_model(system, prompt, api_key, max_tokens=900)
            parsed = _parse_json_array(raw)
            if parsed:
                return parsed[:8]
        except Exception:
            pass
    return _extract_requirements_locally(jd, title)


def _extract_requirements_locally(jd: str, title: str) -> list[str]:
    text = re.sub(r"\s+", " ", jd)
    candidates = re.split(r"(?<=[.!?])\s+|;|\n", text)
    scored = []
    keywords = {
        "experience", "build", "develop", "python", "java", "react", "api",
        "machine learning", "data", "cloud", "test", "deploy", "design",
        "requirements", "responsibilities", "skills",
    }
    for sentence in candidates:
        clean = sentence.strip(" -")
        if len(clean) < 30 or len(clean) > 260:
            continue
        score = sum(1 for keyword in keywords if keyword in clean.lower())
        if score:
            scored.append((score, clean))
    scored.sort(key=lambda item: item[0], reverse=True)
    requirements = [item[1] for item in scored[:8]]
    if not requirements and title:
        requirements = [title]
    return requirements


def _draft_grounded_letter(
    job: dict,
    job_description: str,
    requirements: list[str],
    evidence: list[dict],
    unsupported_claims: list[str] | None = None,
) -> str:
    api_key = GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return _template_letter(job, requirements, evidence)

    evidence_block = "\n".join(
        f"[{idx}] {item.get('text', '')}"
        for idx, item in enumerate(evidence, start=1)
    )
    retry_note = ""
    if unsupported_claims:
        retry_note = "\nAvoid these previously unsupported claims:\n" + "\n".join(f"- {claim}" for claim in unsupported_claims)

    system = """You write concise cover letters grounded only in provided resume evidence.
Rules:
- Use only facts present in the evidence block.
- Do not infer extra technologies, metrics, employers, education, awards, or dates.
- If evidence is missing for a JD requirement, say you are interested in growing in that area instead of claiming experience.
- Return plain text only, 3 short paragraphs, no markdown."""
    prompt = f"""Role: {job.get('title', '')}
Company: {job.get('company', '')}

Key JD requirements:
{json.dumps(requirements[:8], indent=2)}

Resume evidence:
{evidence_block}
{retry_note}

Write the grounded cover letter."""

    try:
        return _call_model(system, prompt, api_key, max_tokens=1400).strip()
    except Exception:
        return _template_letter(job, requirements, evidence)


def _call_model(system_prompt: str, user_prompt: str, api_key: str, max_tokens: int = 1400) -> str:
    try:
        from langchain_groq import ChatGroq  # type: ignore
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore

        llm = ChatGroq(
            groq_api_key=api_key,
            model=GROQ_MODEL,
            temperature=0.2,
            max_tokens=max_tokens,
        )
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        return str(response.content)
    except Exception:
        return _call_groq_http(system_prompt, user_prompt, api_key, max_tokens=max_tokens)


def _call_groq_http(system_prompt: str, user_prompt: str, api_key: str, max_tokens: int = 1400) -> str:
    import requests

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _template_letter(job: dict, requirements: list[str], evidence: list[dict]) -> str:
    title = job.get("title", "this role")
    company = job.get("company", "your team")
    snippets = [item.get("text", "") for item in evidence[:4]]
    evidence_sentence = " ".join(snippets[:2])
    if not evidence_sentence:
        evidence_sentence = "My resume evidence is limited for this role."
    return (
        f"Dear Hiring Team, I am writing to apply for the {title} role at {company}. "
        f"I am interested in the role because it aligns with the requirements around {', '.join(requirements[:3])}."
        f" {evidence_sentence} "
        "I would welcome the opportunity to discuss how this background can contribute to your team. "
        "Thank you for your time and consideration."
    )


def _citations_for_letter(letter: str, evidence: list[dict]) -> list[dict]:
    letter_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}", letter.lower()))
    citations = []
    for item in evidence:
        evidence_tokens = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}", item.get("text", "").lower()))
        if len(letter_tokens & evidence_tokens) >= 2:
            citations.append(item)
    return citations[:8]


def _parse_json_array(raw: str) -> list[str]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    parsed: Any = json.loads(text.strip())
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _format_response(state: ApplyAgentState) -> dict:
    return {
        "job_id": state.get("job_id"),
        "job": {
            "title": state.get("job", {}).get("title", ""),
            "company": state.get("job", {}).get("company", ""),
            "url": state.get("job", {}).get("url", ""),
        },
        "requirements": state.get("requirements", []),
        "cover_letter": state.get("grounded_letter") or state.get("draft", ""),
        "citations": state.get("citations", []),
        "evidence": state.get("evidence", []),
        "unsupported_claims_removed": state.get("unsupported_claims", []),
        "grounding_passed": state.get("grounding_passed", False),
        "faithfulness_score": round(float(state.get("faithfulness_score", 0.0)), 4),
        "match": state.get("match", {}),
        "application_status": state.get("application_status", {}),
        "attempts": state.get("attempts", 0),
        "errors": state.get("errors", []),
    }
