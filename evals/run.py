from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path

from .generation import evaluate_generation, write_generation_results
from .retrieval import evaluate_retrieval, write_retrieval_results
from .schema import load_dataset
from server.resume_chunks import load_resume_chunks, resume_fingerprint


RESULTS_DIR = Path(__file__).resolve().parent / "results"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Job Hunter RAG evals.")
    parser.add_argument("--k", type=int, default=5, help="Retrieval cutoff.")
    parser.add_argument("--generation-limit", type=int, default=5, help="Number of labelled examples for generation eval.")
    parser.add_argument("--judge-backend", choices=["llm", "openai", "groq", "ragas"], default="llm")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--allow-stale-labels",
        action="store_true",
        help="Run even when labelled chunk IDs do not exist in the active resume.",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = RESULTS_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    all_examples = load_dataset()
    labelled = [example for example in all_examples if example.is_labelled]
    stale = _stale_label_report(labelled)
    if stale["missing_label_ids"] and not args.allow_stale_labels:
        stale_path = output_dir / "stale_labels.json"
        stale_path.write_text(json.dumps(stale, indent=2), encoding="utf-8")
        raise SystemExit(
            "Eval labels do not match the active resume. "
            f"{stale['missing_label_ids']} labelled chunk IDs are missing. "
            f"Relabel evals/dataset.jsonl for resume {stale['resume_hash'][:12]} "
            f"or rerun with --allow-stale-labels. Details: {stale_path}"
        )

    retrieval_rows, retrieval_details = evaluate_retrieval(labelled, k=args.k)
    retrieval_md, retrieval_csv = write_retrieval_results(retrieval_rows, retrieval_details, output_dir)

    generation_results = evaluate_generation(labelled, limit=args.generation_limit, backend=args.judge_backend)
    generation_path = write_generation_results(generation_results, output_dir)

    summary = {
        "seed": args.seed,
        "dataset_examples": len(all_examples),
        "labelled_examples": len(labelled),
        "todo_examples": len(all_examples) - len(labelled),
        "retrieval_results": retrieval_rows,
        "generation_examples": len(generation_results),
        "average_generation_faithfulness": _avg(generation_results, "faithfulness_score"),
        "average_jd_relevance": _avg(generation_results, "jd_relevance_score"),
        "paths": {
            "retrieval_md": str(retrieval_md),
            "retrieval_csv": str(retrieval_csv),
            "generation_json": str(generation_path),
        },
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "summary.md").write_text(_summary_markdown(summary), encoding="utf-8")

    print(_summary_markdown(summary))


def _avg(rows: list[dict], key: str) -> float:
    values = [float(row.get(key, 0.0)) for row in rows if key in row]
    return round(sum(values) / len(values), 4) if values else 0.0


def _stale_label_report(examples) -> dict:
    active_ids = {chunk.id for chunk in load_resume_chunks()}
    missing = []
    for example in examples:
        for chunk_id in example.relevant_chunk_ids:
            if chunk_id not in active_ids:
                missing.append({"example_id": example.id, "chunk_id": chunk_id})
    return {
        "resume_hash": resume_fingerprint(),
        "active_chunk_count": len(active_ids),
        "labelled_examples": len(examples),
        "missing_label_ids": len(missing),
        "missing": missing[:100],
    }


def _summary_markdown(summary: dict) -> str:
    lines = [
        "# Eval Summary",
        "",
        f"Seed: {summary['seed']}",
        f"Dataset: {summary['dataset_examples']} examples ({summary['labelled_examples']} labelled, {summary['todo_examples']} TODO)",
        "",
        "## Retrieval",
        "",
        "| Method | Queries | Precision@k | Recall@k | MRR | nDCG |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary["retrieval_results"]:
        lines.append(
            f"| {row['method']} | {row['queries']} | {row['precision_at_k']:.4f} | "
            f"{row['recall_at_k']:.4f} | {row['mrr']:.4f} | {row['ndcg']:.4f} |"
        )
    lines.extend([
        "",
        "## Generation",
        "",
        f"Examples judged: {summary['generation_examples']}",
        f"Average faithfulness: {summary['average_generation_faithfulness']:.4f}",
        f"Average JD relevance: {summary['average_jd_relevance']:.4f}",
        "",
        "## Outputs",
        "",
        f"- Retrieval Markdown: {summary['paths']['retrieval_md']}",
        f"- Retrieval CSV: {summary['paths']['retrieval_csv']}",
        f"- Generation JSON: {summary['paths']['generation_json']}",
    ])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
