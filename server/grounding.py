"""
Grounding guard for generated application text.

The guard is conservative: sentences that make candidate-specific claims need
lexical support from retrieved resume evidence, while generic application
sentences may pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "have", "i", "in", "into", "is", "it", "my", "of", "on", "or", "our",
    "that", "the", "their", "this", "to", "with", "you", "your", "will",
    "would", "am", "was", "were", "been", "being", "can", "could", "also",
}

GENERIC_PATTERNS = [
    r"\bi am excited\b",
    r"\bi am writing\b",
    r"\bthank you\b",
    r"\bi look forward\b",
    r"\bhiring team\b",
    r"\bthe role\b",
    r"\bthe position\b",
    r"\byour team\b",
    r"\byour company\b",
]


@dataclass
class GroundingReport:
    passed: bool
    grounded_letter: str
    unsupported_claims: list[str]
    supported_claims: list[str]

    @property
    def faithfulness_score(self) -> float:
        total = len(self.supported_claims) + len(self.unsupported_claims)
        if total == 0:
            return 1.0
        return len(self.supported_claims) / total

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "grounded_letter": self.grounded_letter,
            "unsupported_claims": self.unsupported_claims,
            "supported_claims": self.supported_claims,
            "faithfulness_score": round(self.faithfulness_score, 4),
        }


def enforce_grounding(letter: str, evidence_texts: list[str], min_overlap: int = 2) -> GroundingReport:
    evidence_tokens = _tokens(" ".join(evidence_texts))
    kept: list[str] = []
    supported: list[str] = []
    unsupported: list[str] = []

    for sentence in split_sentences(letter):
        if not sentence.strip():
            continue
        if _is_generic(sentence):
            kept.append(sentence)
            continue
        sentence_tokens = _tokens(sentence)
        overlap = sentence_tokens & evidence_tokens
        has_number = bool(re.search(r"\d", sentence))
        threshold = max(min_overlap, 3 if has_number else min_overlap)
        if len(overlap) >= threshold:
            kept.append(sentence)
            supported.append(sentence)
        else:
            unsupported.append(sentence)

    grounded_letter = " ".join(kept).strip()
    return GroundingReport(
        passed=not unsupported,
        grounded_letter=grounded_letter,
        unsupported_claims=unsupported,
        supported_claims=supported,
    )


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}", text)
        if token.lower() not in STOPWORDS
    }


def _is_generic(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(re.search(pattern, lowered) for pattern in GENERIC_PATTERNS)
