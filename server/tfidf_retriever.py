"""
Small from-scratch TF-IDF retriever.

This preserves the repo's no-ML-library sparse matching path and makes it usable
as the sparse half of hybrid RAG.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

try:
    from .resume_chunks import ResumeChunk
except ImportError:  # pragma: no cover
    from resume_chunks import ResumeChunk


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.\-]{1,}")


@dataclass
class SparseHit:
    chunk: ResumeChunk
    score: float
    rank: int


class TfidfRetriever:
    def __init__(self, chunks: list[ResumeChunk]):
        self.chunks = chunks
        self.doc_tokens = [_tokenize(chunk.text) for chunk in chunks]
        self.idf = self._build_idf(self.doc_tokens)
        self.doc_vectors = [self._tfidf(tokens) for tokens in self.doc_tokens]
        self.doc_norms = [_norm(vec) for vec in self.doc_vectors]

    def search(self, query: str, k: int = 6) -> list[SparseHit]:
        if not query.strip() or not self.chunks:
            return []

        query_vec = self._tfidf(_tokenize(query))
        query_norm = _norm(query_vec)
        if query_norm == 0:
            return []

        scored: list[tuple[int, float]] = []
        for idx, doc_vec in enumerate(self.doc_vectors):
            denom = query_norm * self.doc_norms[idx]
            if denom == 0:
                continue
            score = _dot(query_vec, doc_vec) / denom
            if score > 0:
                scored.append((idx, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return [
            SparseHit(chunk=self.chunks[idx], score=score, rank=rank)
            for rank, (idx, score) in enumerate(scored[:k], start=1)
        ]

    def _build_idf(self, documents: list[list[str]]) -> dict[str, float]:
        doc_count = len(documents)
        df: Counter[str] = Counter()
        for tokens in documents:
            df.update(set(tokens))
        return {
            term: math.log((1 + doc_count) / (1 + freq)) + 1
            for term, freq in df.items()
        }

    def _tfidf(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        counts = Counter(tokens)
        total = len(tokens)
        return {
            term: (count / total) * self.idf.get(term, 0.0)
            for term, count in counts.items()
            if self.idf.get(term, 0.0) > 0
        }


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _dot(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


def _norm(vec: dict[str, float]) -> float:
    return math.sqrt(sum(weight * weight for weight in vec.values()))
