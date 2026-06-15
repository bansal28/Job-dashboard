"""
Chroma-backed dense resume retriever.

Imports are intentionally lazy so the existing app can still boot before the
new optional dependencies are installed.
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from .resume_chunks import ResumeChunk, resume_fingerprint
    from .settings import (
        EMBEDDING_FALLBACK_MODEL,
        EMBEDDING_MODEL,
        VECTOR_COLLECTION,
        VECTOR_STORE_PATH,
    )
except ImportError:  # pragma: no cover
    from resume_chunks import ResumeChunk, resume_fingerprint
    from settings import (
        EMBEDDING_FALLBACK_MODEL,
        EMBEDDING_MODEL,
        VECTOR_COLLECTION,
        VECTOR_STORE_PATH,
    )


@dataclass
class DenseHit:
    chunk: ResumeChunk
    score: float
    rank: int


class DenseResumeRetriever:
    def __init__(self, chunks: list[ResumeChunk]):
        self.chunks = chunks
        self.available = False
        self.error = ""
        self.model_name = EMBEDDING_MODEL
        self._model = None
        self._collection = None

        try:
            self._load_dependencies()
            self._ensure_index()
            self.available = True
        except Exception as exc:
            self.error = str(exc)
            self.available = False

    def search(self, query: str, k: int = 6) -> list[DenseHit]:
        if not self.available or not query.strip() or self._collection is None:
            return []

        query_embedding = self._encode([query])[0]
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=max(k, 1),
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        hits: list[DenseHit] = []

        for rank, (chunk_id, text, metadata, distance) in enumerate(
            zip(ids, documents, metadatas, distances),
            start=1,
        ):
            score = max(0.0, 1.0 - float(distance or 0.0))
            hits.append(
                DenseHit(
                    chunk=ResumeChunk(
                        id=chunk_id,
                        text=text,
                        section=str(metadata.get("section", "")),
                        role=str(metadata.get("role", "")),
                        company=str(metadata.get("company", "")),
                        kind=str(metadata.get("kind", "")),
                    ),
                    score=score,
                    rank=rank,
                )
            )
        return hits

    def search_many(self, queries: list[str], k: int = 6) -> list[list[DenseHit]]:
        if not self.available or self._collection is None:
            return [[] for _ in queries]

        non_empty = [(idx, query) for idx, query in enumerate(queries) if query.strip()]
        results_by_index: list[list[DenseHit]] = [[] for _ in queries]
        if not non_empty:
            return results_by_index

        embeddings = self._encode([query for _, query in non_empty])
        result = self._collection.query(
            query_embeddings=embeddings,
            n_results=max(k, 1),
            include=["documents", "metadatas", "distances"],
        )

        all_ids = result.get("ids", [])
        all_documents = result.get("documents", [])
        all_metadatas = result.get("metadatas", [])
        all_distances = result.get("distances", [])

        for result_idx, (original_idx, _) in enumerate(non_empty):
            ids = all_ids[result_idx] if result_idx < len(all_ids) else []
            documents = all_documents[result_idx] if result_idx < len(all_documents) else []
            metadatas = all_metadatas[result_idx] if result_idx < len(all_metadatas) else []
            distances = all_distances[result_idx] if result_idx < len(all_distances) else []
            hits: list[DenseHit] = []
            for rank, (chunk_id, text, metadata, distance) in enumerate(
                zip(ids, documents, metadatas, distances),
                start=1,
            ):
                score = max(0.0, 1.0 - float(distance or 0.0))
                hits.append(
                    DenseHit(
                        chunk=ResumeChunk(
                            id=chunk_id,
                            text=text,
                            section=str(metadata.get("section", "")),
                            role=str(metadata.get("role", "")),
                            company=str(metadata.get("company", "")),
                            kind=str(metadata.get("kind", "")),
                        ),
                        score=score,
                        rank=rank,
                    )
                )
            results_by_index[original_idx] = hits
        return results_by_index

    def _load_dependencies(self) -> None:
        import chromadb  # type: ignore
        from sentence_transformers import SentenceTransformer  # type: ignore

        try:
            self._model = SentenceTransformer(EMBEDDING_MODEL)
            self.model_name = EMBEDDING_MODEL
        except Exception:
            self._model = SentenceTransformer(EMBEDDING_FALLBACK_MODEL)
            self.model_name = EMBEDDING_FALLBACK_MODEL

        VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(VECTOR_STORE_PATH))
        self._client = client
        self._collection = client.get_or_create_collection(
            name=VECTOR_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def _ensure_index(self) -> None:
        if self._collection is None:
            return

        resume_hash = resume_fingerprint()
        if self._collection.count() > 0:
            existing = self._collection.get(limit=1, include=["metadatas"])
            metadatas = existing.get("metadatas", [])
            existing_hash = metadatas[0].get("resume_hash") if metadatas else None
            if existing_hash != resume_hash:
                self._client.delete_collection(VECTOR_COLLECTION)
                self._collection = self._client.get_or_create_collection(
                    name=VECTOR_COLLECTION,
                    metadata={"hnsw:space": "cosine"},
                )
            else:
                return

        if not self.chunks:
            return

        embeddings = self._encode([chunk.text for chunk in self.chunks])
        self._collection.upsert(
            ids=[chunk.id for chunk in self.chunks],
            documents=[chunk.text for chunk in self.chunks],
            metadatas=[
                {
                    "section": chunk.section,
                    "role": chunk.role,
                    "company": chunk.company,
                    "kind": chunk.kind,
                    "resume_hash": resume_hash,
                    "embedding_model": self.model_name,
                }
                for chunk in self.chunks
            ],
            embeddings=embeddings,
        )

    def _encode(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            return []
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [vec.tolist() for vec in vectors]
