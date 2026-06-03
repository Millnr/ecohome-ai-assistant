"""
EcoHome RAG — Ragas Evaluation
Scores retrieval quality and answer grounding from the JSONL dataset
produced by the TypeScript eval runner.

Usage:
    pip install ragas datasets
    python ragas/evaluate.py outputs/ragas-dataset.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python ragas/evaluate.py outputs/ragas-dataset.jsonl")

    rows = load_jsonl(Path(sys.argv[1]))

    # Only score rows that have retrieved contexts (RAG rows)
    rag_rows = [r for r in rows if r.get("contexts")]
    if not rag_rows:
        raise SystemExit("No rows with retrieved contexts to evaluate")

    print(f"Scoring {len(rag_rows)} RAG turns across {len({r['scenario_id'] for r in rag_rows})} scenarios\n")

    dataset = Dataset.from_list([
        {
            "question": row["question"],
            "answer": row["answer"],
            "contexts": row.get("contexts") or [],
            "ground_truth": row.get("ground_truth") or "",
        }
        for row in rag_rows
    ])

    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
    )

    print(result)

    # Print per-scenario breakdown
    df = result.to_pandas()
    df.insert(0, "scenario_id", [r["scenario_id"] for r in rag_rows])
    print("\nPer-scenario scores:")
    print(df[["scenario_id", "faithfulness", "answer_relevancy", "context_precision", "context_recall"]].to_string(index=False))

    # Flag any scenarios below threshold
    thresholds = {
        "faithfulness": 0.80,
        "answer_relevancy": 0.80,
        "context_precision": 0.75,
    }
    print("\nThreshold check:")
    all_pass = True
    for metric, threshold in thresholds.items():
        if metric in df.columns:
            below = df[df[metric] < threshold]["scenario_id"].tolist()
            if below:
                print(f"  ✗ {metric} < {threshold}: {below}")
                all_pass = False
            else:
                print(f"  ✓ {metric} >= {threshold}: all pass")

    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
