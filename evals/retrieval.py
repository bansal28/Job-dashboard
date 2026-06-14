from __future__ import annotations

import csv
import math
from pathlib import Path

from server.hybrid_retriever import get_retriever

from .schema import RetrievalExample


METHODS = ["dense", "sparse", "hybrid"]


def evaluate_retrieval(examples: list[RetrievalExample], k: int = 5) -> tuple[list[dict], dict[str, list[dict]]]:
    retriever = get_retriever()
    rows: list[dict] = []
    details: dict[str, list[dict]] = {}

    for method in METHODS:
        per_query = []
        for example in examples:
            hits = retriever.retrieve(example.query, k=k, method=method)
            ranked_ids = [hit.chunk.id for hit in hits]
            metrics = _metrics(ranked_ids, example.relevant_chunk_ids, k=k)
            per_query.append({
                "example_id": example.id,
                "job_id": example.job_id,
                "method": method,
                "query": example.query,
                "ranked_ids": ranked_ids,
                **metrics,
            })
        details[method] = per_query
        rows.append(_average_row(method, per_query))

    return rows, details


def write_retrieval_results(rows: list[dict], details: dict[str, list[dict]], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "retrieval_results.csv"
    md_path = output_dir / "retrieval_results.md"

    fieldnames = ["method", "queries", "precision_at_k", "recall_at_k", "mrr", "ndcg"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})

    lines = [
        "| Method | Queries | Precision@k | Recall@k | MRR | nDCG |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['method']} | {row['queries']} | {row['precision_at_k']:.4f} | "
            f"{row['recall_at_k']:.4f} | {row['mrr']:.4f} | {row['ndcg']:.4f} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path, csv_path


def _metrics(ranked_ids: list[str], relevant_ids: list[str], k: int) -> dict:
    relevant = set(relevant_ids)
    if not relevant:
        return {"precision_at_k": 0.0, "recall_at_k": 0.0, "mrr": 0.0, "ndcg": 0.0}

    top_k = ranked_ids[:k]
    hits = [1 if chunk_id in relevant else 0 for chunk_id in top_k]
    precision = sum(hits) / k if k else 0.0
    recall = sum(hits) / len(relevant)

    reciprocal_rank = 0.0
    for idx, chunk_id in enumerate(ranked_ids, start=1):
        if chunk_id in relevant:
            reciprocal_rank = 1.0 / idx
            break

    dcg = sum(hit / math.log2(idx + 2) for idx, hit in enumerate(hits))
    ideal_hits = [1] * min(len(relevant), k)
    idcg = sum(hit / math.log2(idx + 2) for idx, hit in enumerate(ideal_hits))
    ndcg = dcg / idcg if idcg else 0.0

    return {
        "precision_at_k": precision,
        "recall_at_k": recall,
        "mrr": reciprocal_rank,
        "ndcg": ndcg,
    }


def _average_row(method: str, rows: list[dict]) -> dict:
    count = len(rows) or 1
    return {
        "method": method,
        "queries": len(rows),
        "precision_at_k": sum(row["precision_at_k"] for row in rows) / count,
        "recall_at_k": sum(row["recall_at_k"] for row in rows) / count,
        "mrr": sum(row["mrr"] for row in rows) / count,
        "ndcg": sum(row["ndcg"] for row in rows) / count,
    }
