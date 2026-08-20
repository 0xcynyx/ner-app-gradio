"""Labels raw text with the teacher model to create the distillation training set.

The teacher emits fragmented subword spans, so its raw output is unusable as supervision. Both
production post processing steps run here, aggregation to rejoin fragments and regex
verification to fix structured identifiers, which means the student learns the corrected
boundaries rather than the teacher's mistakes.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.domain.models import RawSpan  # noqa: E402
from app.services.aggregation import SpanAggregator, hydrate  # noqa: E402
from app.services.verification import RegexVerifier  # noqa: E402


def read_lines(paths: List[Path], limit: int | None) -> List[str]:
    seen: List[str] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if 15 < len(line) < 600:
                seen.append(line)
    if limit:
        seen = seen[:limit]
    return seen


def main() -> int:
    parser = argparse.ArgumentParser(description="Create teacher labelled training data")
    parser.add_argument("--teacher", required=True)
    parser.add_argument("--source", type=Path, action="append", required=True)
    parser.add_argument("--out-train", required=True)
    parser.add_argument("--out-dev", required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--dev-fraction", type=float, default=0.05)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline

    if args.device == "auto":
        device = 0 if torch.backends.mps.is_available() or torch.cuda.is_available() else -1
    else:
        device = int(args.device)

    pipe = pipeline(
        task="token-classification",
        model=AutoModelForTokenClassification.from_pretrained(args.teacher),
        tokenizer=AutoTokenizer.from_pretrained(args.teacher),
        aggregation_strategy="simple",
        device=device,
    )
    aggregator = SpanAggregator(min_score=0.5)
    verifier = RegexVerifier()

    texts = read_lines(args.source, args.limit)
    print(f"labelling {len(texts)} sentences on device {device}")

    rows: List[Dict] = []
    started = time.perf_counter()
    for index in range(0, len(texts), args.batch_size):
        batch = texts[index:index + args.batch_size]
        for text, raw in zip(batch, pipe(batch, batch_size=len(batch))):
            spans = [
                RawSpan(int(i["start"]), int(i["end"]), str(i.get("entity_group") or "O"), float(i.get("score", 0.0)))
                for i in raw if i.get("start") is not None
            ]
            entities = verifier.verify(text, hydrate(text, aggregator.build(text, spans, 0.5)))
            rows.append({
                "text": text,
                "entities": [{"start": e.start, "end": e.end, "label": e.label} for e in entities],
            })
        if index and index % (args.batch_size * 40) == 0:
            rate = (index + len(batch)) / (time.perf_counter() - started)
            print(f"  {index + len(batch)}/{len(texts)} at {rate:.0f} sent/s")

    random.Random(11).shuffle(rows)
    split = max(1, int(len(rows) * args.dev_fraction))
    dev, train = rows[:split], rows[split:]
    for path, chunk in ((args.out_train, train), (args.out_dev, dev)):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in chunk), encoding="utf-8")

    labelled = sum(len(r["entities"]) for r in rows)
    print(f"train {len(train)}, dev {len(dev)}, {labelled} entities, {time.perf_counter() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
