"""
Resume chunking for retrieval.

The chunker intentionally keeps chunks small and attributable: bullets are their
own chunks, roles/projects become metadata, and section text is preserved.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

try:
    from .settings import RESUME_PATH
except ImportError:  # pragma: no cover - supports direct module imports
    from settings import RESUME_PATH


@dataclass(frozen=True)
class ResumeChunk:
    id: str
    text: str
    section: str = ""
    role: str = ""
    company: str = ""
    kind: str = "text"

    @property
    def metadata(self) -> dict:
        data = asdict(self)
        data.pop("text", None)
        return data


def load_resume_chunks(path: Path | str = RESUME_PATH) -> list[ResumeChunk]:
    path = Path(path)
    if not path.exists():
        return []
    return chunk_resume_latex(path.read_text(encoding="utf-8"))


def resume_fingerprint(path: Path | str = RESUME_PATH) -> str:
    path = Path(path)
    if not path.exists():
        return "missing"
    return hashlib.sha1(path.read_bytes()).hexdigest()


def chunk_resume_latex(content: str) -> list[ResumeChunk]:
    chunks: list[ResumeChunk] = []
    section = "Summary"
    company = ""
    role = ""
    project = ""
    before_first_section: list[str] = []
    in_header = False
    in_itemize = False

    lines = content.splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("%"):
            continue

        if line.startswith(r"\begin{center}"):
            in_header = True
            continue
        if line.startswith(r"\end{center}"):
            in_header = False
            continue
        if in_header:
            continue
        if line.startswith(r"\begin{itemize}"):
            in_itemize = True
            continue
        if line.startswith(r"\end{itemize}"):
            in_itemize = False
            continue
        if line.startswith(r"\documentclass") or line.startswith(r"\usepackage"):
            continue
        if line.startswith("\\") and not line.startswith((r"\section", r"\textbf", r"\textit", r"\item")):
            continue

        section_match = re.match(r"\\section\*\{(.+?)\}", line)
        if section_match:
            if before_first_section:
                text = _clean_text(" ".join(before_first_section))
                if text:
                    chunks.append(_make_chunk(text, "Summary", "", "", "summary"))
                before_first_section = []
            section = _clean_text(section_match.group(1))
            company = ""
            role = ""
            project = ""
            continue

        if section == "Summary":
            before_first_section.append(line)
            continue

        if line.startswith(r"\item"):
            text = _clean_text(re.sub(r"^\\item\s*", "", line))
            if text:
                chunks.append(_make_chunk(text, section, role or project, company, "bullet"))
            continue

        if section == "Experience":
            company_match = re.match(r"\\textbf\{(.+?)\}", line)
            role_match = re.match(r"\\textit\{(.+?)\}", line)
            if company_match and not in_itemize:
                company = _clean_text(company_match.group(1))
                role = ""
                continue
            if role_match and not in_itemize:
                role = _clean_text(role_match.group(1))
                continue

        if section == "Projects":
            project_match = re.match(r"\\textbf\{(.+?)\}", line)
            if project_match and not in_itemize:
                project = _clean_text(project_match.group(1))
                role = project
                company = ""
                continue

        text = _clean_text(line)
        if text and not _is_layout_text(text):
            chunks.append(_make_chunk(text, section, role or project, company, _kind_for_section(section)))

    if before_first_section:
        text = _clean_text(" ".join(before_first_section))
        if text:
            chunks.append(_make_chunk(text, "Summary", "", "", "summary"))

    return _dedupe_chunks(chunks)


def chunks_as_dicts(chunks: Iterable[ResumeChunk]) -> list[dict]:
    return [
        {
            "id": chunk.id,
            "text": chunk.text,
            "metadata": chunk.metadata,
            "section": chunk.section,
            "role": chunk.role,
            "company": chunk.company,
            "kind": chunk.kind,
        }
        for chunk in chunks
    ]


def _make_chunk(text: str, section: str, role: str, company: str, kind: str) -> ResumeChunk:
    key = "|".join([section, role, company, kind, text])
    chunk_id = "resume_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return ResumeChunk(
        id=chunk_id,
        text=text,
        section=section,
        role=role,
        company=company,
        kind=kind,
    )


def _dedupe_chunks(chunks: list[ResumeChunk]) -> list[ResumeChunk]:
    seen = set()
    unique: list[ResumeChunk] = []
    for chunk in chunks:
        if chunk.text in seen:
            continue
        seen.add(chunk.text)
        unique.append(chunk)
    return unique


def _kind_for_section(section: str) -> str:
    lookup = {
        "Education": "education",
        "Technical Skills": "skills",
        "Certifications": "certification",
        "Achievements": "achievement",
        "Leadership & Activities": "leadership",
        "Interests": "interest",
    }
    return lookup.get(section, "text")


def _clean_text(text: str) -> str:
    text = text.replace(r"\&", "&").replace(r"\%", "%").replace(r"\$", "$")
    text = text.replace(r"\_", "_").replace(r"\#", "#")
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:textbf|textit|emph)\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:hfill|vspace|smallskip|medskip|bigskip)\b(?:\{[^}]*\})?", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^]]*\])?(?:\{([^}]*)\})?", r"\1", text)
    text = re.sub(r"[{}]", " ", text)
    text = text.replace(r"\\", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -")


def _is_layout_text(text: str) -> bool:
    lowered = text.lower()
    return lowered in {"begin document", "end document"} or lowered.startswith("setlength")
