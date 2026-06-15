"""
Unified dense/sparse/hybrid resume retrieval interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

try:
    from .resume_chunks import ResumeChunk, load_resume_chunks
    from .settings import (
        RETRIEVAL_K,
        RETRIEVAL_METHOD,
        RRF_DENSE_WEIGHT,
        RRF_K,
        RRF_SPARSE_WEIGHT,
    )
    from .tfidf_retriever import TfidfRetriever
    from .vector_store import DenseResumeRetriever
except ImportError:  # pragma: no cover
    from resume_chunks import ResumeChunk, load_resume_chunks
    from settings import (
        RETRIEVAL_K,
        RETRIEVAL_METHOD,
        RRF_DENSE_WEIGHT,
        RRF_K,
        RRF_SPARSE_WEIGHT,
    )
    from tfidf_retriever import TfidfRetriever
    from vector_store import DenseResumeRetriever


RetrievalMethod = Literal["dense", "sparse", "hybrid"]


@dataclass
class RetrievalResult:
    chunk: ResumeChunk
    score: float
    rank: int
    method: str
    sources: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "id": self.chunk.id,
            "text": self.chunk.text,
            "score": round(self.score, 4),
            "rank": self.rank,
            "method": self.method,
            "sources": {key: round(value, 4) for key, value in self.sources.items()},
            "metadata": self.chunk.metadata,
            "section": self.chunk.section,
            "role": self.chunk.role,
            "company": self.chunk.company,
            "kind": self.chunk.kind,
        }


class HybridResumeRetriever:
    def __init__(self, chunks: list[ResumeChunk] | None = None):
        self.chunks = chunks if chunks is not None else load_resume_chunks()
        self.sparse = TfidfRetriever(self.chunks)
        self.dense = DenseResumeRetriever(self.chunks)

    def retrieve(
        self,
        query: str,
        k: int = RETRIEVAL_K,
        method: RetrievalMethod = RETRIEVAL_METHOD,  # type: ignore[assignment]
    ) -> list[RetrievalResult]:
        method = _normalize_method(method)
        if method == "sparse":
            return _convert_hits(self.sparse.search(query, k), "sparse")
        if method == "dense":
            return _convert_hits(self.dense.search(query, k), "dense")

        dense_hits = _convert_hits(self.dense.search(query, k), "dense")
        sparse_hits = _convert_hits(self.sparse.search(query, k), "sparse")
        return rrf_fuse(
            {"dense": dense_hits, "sparse": sparse_hits},
            k=k,
            rrf_k=RRF_K,
            weights={"dense": RRF_DENSE_WEIGHT, "sparse": RRF_SPARSE_WEIGHT},
        )

    def score_query(self, query: str, method: RetrievalMethod = RETRIEVAL_METHOD) -> tuple[int, list[RetrievalResult]]:
        results = self.retrieve(query, k=RETRIEVAL_K, method=method)
        return self._score_results(results, method)

    def score_queries(
        self,
        queries: list[str],
        method: RetrievalMethod = RETRIEVAL_METHOD,
    ) -> list[tuple[int, list[RetrievalResult]]]:
        method = _normalize_method(method)
        if method == "dense":
            dense_many = self.dense.search_many(queries, k=RETRIEVAL_K)
            return [
                self._score_results(_convert_hits(hits, "dense"), method)
                for hits in dense_many
            ]
        if method == "sparse":
            return [
                self._score_results(_convert_hits(self.sparse.search(query, RETRIEVAL_K), "sparse"), method)
                for query in queries
            ]

        dense_many = self.dense.search_many(queries, k=RETRIEVAL_K)
        scored: list[tuple[int, list[RetrievalResult]]] = []
        for query, dense_hits in zip(queries, dense_many):
            dense_results = _convert_hits(dense_hits, "dense")
            sparse_results = _convert_hits(self.sparse.search(query, RETRIEVAL_K), "sparse")
            fused = rrf_fuse(
                {"dense": dense_results, "sparse": sparse_results},
                k=RETRIEVAL_K,
                rrf_k=RRF_K,
                weights={"dense": RRF_DENSE_WEIGHT, "sparse": RRF_SPARSE_WEIGHT},
            )
            scored.append(self._score_results(fused, method))
        return scored

    def _score_results(
        self,
        results: list[RetrievalResult],
        method: RetrievalMethod,
    ) -> tuple[int, list[RetrievalResult]]:
        if not results:
            return 0, []
        if method == "hybrid" and results[0].method == "hybrid":
            if not self.dense.available and "sparse" in results[0].sources:
                score = int(round(min(1.0, max(0.0, results[0].sources["sparse"])) * 100))
                return max(0, min(100, score)), results
            if self.dense.available and "sparse" not in results[0].sources and "dense" in results[0].sources:
                score = int(round(min(1.0, max(0.0, results[0].sources["dense"])) * 100))
                return max(0, min(100, score)), results
            active_weight = sum(
                {"dense": RRF_DENSE_WEIGHT, "sparse": RRF_SPARSE_WEIGHT}.get(source, 1.0)
                for source in results[0].sources
            ) or 1.0
            max_possible = active_weight / (RRF_K + 1)
            score = int(round(min(1.0, results[0].score / max_possible) * 100))
        else:
            score = int(round(min(1.0, max(0.0, results[0].score)) * 100))
        return max(0, min(100, score)), results


def retrieve(query: str, k: int = RETRIEVAL_K, method: RetrievalMethod = RETRIEVAL_METHOD) -> list[dict]:
    return [result.as_dict() for result in get_retriever().retrieve(query, k=k, method=method)]


def rrf_fuse(
    ranked_lists: dict[str, list[RetrievalResult]],
    k: int,
    rrf_k: int = 60,
    weights: dict[str, float] | None = None,
) -> list[RetrievalResult]:
    weights = weights or {}
    fused: dict[str, RetrievalResult] = {}
    scores: dict[str, float] = {}
    source_scores: dict[str, dict[str, float]] = {}

    for method, results in ranked_lists.items():
        weight = weights.get(method, 1.0)
        for rank, result in enumerate(results, start=1):
            chunk_id = result.chunk.id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + weight * (1.0 / (rrf_k + rank))
            source_scores.setdefault(chunk_id, {})[method] = result.score
            if chunk_id not in fused:
                fused[chunk_id] = result

    ordered_ids = sorted(scores, key=lambda chunk_id: scores[chunk_id], reverse=True)
    output: list[RetrievalResult] = []
    for rank, chunk_id in enumerate(ordered_ids[:k], start=1):
        base = fused[chunk_id]
        output.append(
            RetrievalResult(
                chunk=base.chunk,
                score=scores[chunk_id],
                rank=rank,
                method="hybrid",
                sources=source_scores.get(chunk_id, {}),
            )
        )
    return output


_retriever_cache: HybridResumeRetriever | None = None


def get_retriever(force_reload: bool = False) -> HybridResumeRetriever:
    global _retriever_cache
    if force_reload or _retriever_cache is None:
        _retriever_cache = HybridResumeRetriever()
    return _retriever_cache


def reload_retriever() -> HybridResumeRetriever:
    return get_retriever(force_reload=True)


def _convert_hits(hits, method: str) -> list[RetrievalResult]:
    return [
        RetrievalResult(
            chunk=hit.chunk,
            score=float(hit.score),
            rank=int(hit.rank),
            method=method,
            sources={method: float(hit.score)},
        )
        for hit in hits
    ]


def _normalize_method(method: str) -> RetrievalMethod:
    if method not in {"dense", "sparse", "hybrid"}:
        return "hybrid"
    return method  # type: ignore[return-value]
