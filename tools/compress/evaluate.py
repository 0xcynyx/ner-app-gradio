"""Measures every compression variant against the original checkpoint.

Two numbers matter and they answer different questions. Fidelity is span agreement with the
original model, which is what tells you whether compression changed behaviour. F1 is scored
against the synthetic gold set, which tells you whether the task still works at all.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

# The backend services are the real post processing, so scoring reuses them rather than copying.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.domain.models import RawSpan  # noqa: E402
from app.services.aggregation import SpanAggregator, hydrate  # noqa: E402
from app.services.verification import RegexVerifier  # noqa: E402

_KEY = Tuple[int, int, str]


def load_rows(path: Path) -> List[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


_AGGREGATOR = SpanAggregator(min_score=0.5)
_VERIFIER = RegexVerifier()


def post_process(text: str, raw: Sequence[dict]) -> Set[_KEY]:
    """Apply the production aggregation and verification the app runs on every request."""
    spans = [
        RawSpan(int(item["start"]), int(item["end"]), str(item.get("entity_group") or item.get("entity") or "O"), float(item.get("score", 0.0)))
        for item in raw
        if item.get("start") is not None
    ]
    entities = hydrate(text, _AGGREGATOR.build(text, spans, 0.5))
    return {(e.start, e.end, e.label) for e in _VERIFIER.verify(text, entities)}


def build_pipeline(kind: str, path: str):
    """Return a callable that maps text to a list of span dicts."""
    if kind == "torch":
        from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

        return pipeline(
            task="token-classification",
            model=AutoModelForTokenClassification.from_pretrained(path),
            tokenizer=AutoTokenizer.from_pretrained(path),
            aggregation_strategy="simple",
            device=-1,
        )
    from optimum.onnxruntime import ORTModelForTokenClassification
    from transformers import AutoTokenizer, pipeline

    file_name = "model_quantized.onnx" if kind == "onnx-int8" else "model.onnx"
    # Pin the CPU provider so latency is comparable with the torch CPU baseline.
    return pipeline(
        task="token-classification",
        model=ORTModelForTokenClassification.from_pretrained(path, file_name=file_name, provider="CPUExecutionProvider"),
        tokenizer=AutoTokenizer.from_pretrained(path),
        aggregation_strategy="simple",
        device=-1,
    )


def spans_of(prediction: Sequence[dict]) -> Set[_KEY]:
    return {(int(item["start"]), int(item["end"]), str(item["entity_group"])) for item in prediction}


def gold_of(row: dict) -> Set[_KEY]:
    return {(e["start"], e["end"], e["label"]) for e in row["entities"]}


def score(predicted: Set[_KEY], reference: Set[_KEY]) -> Tuple[int, int, int]:
    hit = len(predicted & reference)
    return hit, len(predicted) - hit, len(reference) - hit


def prf(hit: int, extra: int, missed: int) -> Tuple[float, float, float]:
    precision = hit / (hit + extra) if hit + extra else 0.0
    recall = hit / (hit + missed) if hit + missed else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def run(kind: str, path: str, rows: List[dict], mode: str) -> Dict[str, object]:
    pipe = build_pipeline(kind, path)
    pipe("pemanasan sebelum pengukuran")
    predictions: List[Set[_KEY]] = []
    started = time.perf_counter()
    for row in rows:
        raw = pipe(row["text"])
        predictions.append(post_process(row["text"], raw) if mode == "production" else spans_of(raw))
    elapsed = time.perf_counter() - started

    totals = [0, 0, 0]
    for prediction, row in zip(predictions, rows):
        for index, value in enumerate(score(prediction, gold_of(row))):
            totals[index] += value
    precision, recall, f1 = prf(*totals)
    return {
        "predictions": predictions,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "ms_per_doc": 1000 * elapsed / max(len(rows), 1),
    }


def fidelity(candidate: List[Set[_KEY]], baseline: List[Set[_KEY]]) -> Dict[str, float]:
    """Agreement with the original model, exact means every span in a document matched."""
    totals = [0, 0, 0]
    identical = 0
    for mine, theirs in zip(candidate, baseline):
        if mine == theirs:
            identical += 1
        for index, value in enumerate(score(mine, theirs)):
            totals[index] += value
    _, _, f1 = prf(*totals)
    return {"span_agreement": f1, "exact_documents": identical / max(len(baseline), 1)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare compressed variants to the original")
    parser.add_argument("--testset", type=Path, required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--variant", action="append", default=[], metavar="NAME=KIND=PATH")
    parser.add_argument("--mode", choices=("production", "raw"), default="production")
    args = parser.parse_args()

    rows = load_rows(args.testset)
    print(f"evaluating on {len(rows)} sentences\n")

    print(f"post processing: {args.mode}\n")
    baseline = run("torch", args.baseline, rows, args.mode)
    header = f"{'variant':22} {'F1':>7} {'P':>7} {'R':>7} {'ms/doc':>8} {'agree':>7} {'exact':>7}"
    print(header)
    print("-" * len(header))
    print(f"{'original fp32':22} {baseline['f1']:7.4f} {baseline['precision']:7.4f} {baseline['recall']:7.4f} {baseline['ms_per_doc']:8.1f} {'':>7} {'':>7}")

    for spec in args.variant:
        name, kind, path = spec.split("=", 2)
        result = run(kind, path, rows, args.mode)
        agreement = fidelity(result["predictions"], baseline["predictions"])
        print(
            f"{name:22} {result['f1']:7.4f} {result['precision']:7.4f} {result['recall']:7.4f} "
            f"{result['ms_per_doc']:8.1f} {agreement['span_agreement']:7.4f} {agreement['exact_documents']:7.2%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
