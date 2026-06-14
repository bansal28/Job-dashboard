from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


DATASET_PATH = Path(__file__).resolve().parent / "dataset.jsonl"


@dataclass(frozen=True)
class RetrievalExample:
    id: str
    job_id: str
    query: str
    relevant_chunk_ids: list[str]
    label_status: str = "TODO"
    notes: str = ""

    @property
    def is_labelled(self) -> bool:
        return self.label_status.lower() == "labelled" and bool(self.relevant_chunk_ids)


def load_dataset(path: Path = DATASET_PATH, labelled_only: bool = False) -> list[RetrievalExample]:
    examples: list[RetrievalExample] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        example = RetrievalExample(
            id=data["id"],
            job_id=data["job_id"],
            query=data["query"],
            relevant_chunk_ids=list(data.get("relevant_chunk_ids", [])),
            label_status=data.get("label_status", "TODO"),
            notes=data.get("notes", ""),
        )
        if labelled_only and not example.is_labelled:
            continue
        examples.append(example)
    return examples
