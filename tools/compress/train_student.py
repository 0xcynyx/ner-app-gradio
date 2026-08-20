"""Distils the teacher into a small Indonesian encoder for browser deployment.

Supervision is character spans produced by the teacher, not token logits, because the student
uses a different tokenizer. That also lets the student learn a complete BIO inventory with an
I- tag for every type, which the teacher lacks and which is the reason the teacher fragments
emails, phone numbers, and identifiers across tokens.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.domain.labels import LABELS  # noqa: E402

TYPES = [spec.code for spec in LABELS]
LABEL_NAMES = ["O"] + [f"{prefix}-{code}" for code in TYPES for prefix in ("B", "I")]
LABEL_TO_ID = {name: index for index, name in enumerate(LABEL_NAMES)}


def load(path: Path) -> List[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def encode(rows: Sequence[dict], tokenizer, max_length: int):
    """Turn character spans into per token BIO ids using the tokenizer offset mapping."""
    import torch

    texts = [row["text"] for row in rows]
    encoded = tokenizer(texts, truncation=True, max_length=max_length, padding="max_length",
                        return_offsets_mapping=True, return_tensors="pt")
    labels = torch.full(encoded["input_ids"].shape, -100, dtype=torch.long)
    for index, row in enumerate(rows):
        offsets = encoded["offset_mapping"][index].tolist()
        spans = sorted(row["entities"], key=lambda e: e["start"])
        for position, (start, end) in enumerate(offsets):
            if start == end:
                continue
            labels[index][position] = LABEL_TO_ID["O"]
            for span in spans:
                if start >= span["start"] and end <= span["end"]:
                    prefix = "B" if start == span["start"] else "I"
                    name = f"{prefix}-{span['label']}"
                    if name in LABEL_TO_ID:
                        labels[index][position] = LABEL_TO_ID[name]
                    break
    encoded.pop("offset_mapping")
    encoded["labels"] = labels
    return encoded


def decode_spans(text: str, offsets: Sequence[Tuple[int, int]], ids: Sequence[int]) -> Set[Tuple[int, int, str]]:
    """Read a BIO id sequence back into character spans."""
    spans: Set[Tuple[int, int, str]] = set()
    current = None
    for (start, end), label_id in zip(offsets, ids):
        if start == end:
            continue
        name = LABEL_NAMES[label_id]
        if name == "O":
            if current:
                spans.add(current)
                current = None
            continue
        prefix, _, code = name.partition("-")
        if prefix == "B" or current is None or current[2] != code:
            if current:
                spans.add(current)
            current = (start, end, code)
        else:
            current = (current[0], end, code)
    if current:
        spans.add(current)
    return spans


def span_f1(predicted: Sequence[Set], gold: Sequence[Set]) -> Tuple[float, float, float]:
    hit = extra = missed = 0
    for mine, theirs in zip(predicted, gold):
        hit += len(mine & theirs)
        extra += len(mine - theirs)
        missed += len(theirs - mine)
    precision = hit / (hit + extra) if hit + extra else 0.0
    recall = hit / (hit + missed) if hit + missed else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def evaluate(model, tokenizer, rows: Sequence[dict], max_length: int, device, batch_size: int) -> Tuple[float, float, float]:
    import torch

    model.eval()
    predicted, gold = [], []
    with torch.no_grad():
        for index in range(0, len(rows), batch_size):
            chunk = rows[index:index + batch_size]
            batch = tokenizer([r["text"] for r in chunk], truncation=True, max_length=max_length,
                              padding=True, return_offsets_mapping=True, return_tensors="pt")
            offsets = batch.pop("offset_mapping")
            logits = model(**{k: v.to(device) for k, v in batch.items()}).logits.argmax(-1).cpu()
            for position, row in enumerate(chunk):
                predicted.append(decode_spans(row["text"], offsets[position].tolist(), logits[position].tolist()))
                gold.append({(e["start"], e["end"], e["label"]) for e in row["entities"]})
    model.train()
    return span_f1(predicted, gold)


def load_tokenizer(name: str, auto_cls, bert_cls):
    """IndoBERT lite declares the albert type but ships a WordPiece vocab, so fall back to BERT."""
    try:
        return auto_cls.from_pretrained(name)
    except (ValueError, OSError) as error:
        print(f"auto tokenizer failed ({error}), using BertTokenizerFast")
        return bert_cls.from_pretrained(name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Distil the teacher into a small student")
    parser.add_argument("--student", default="indobenchmark/indobert-lite-base-p1")
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--dev", type=Path, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--max-length", type=int, default=192)
    parser.add_argument("--layers", type=int, default=0, help="override hidden layer count, 0 keeps the default")
    args = parser.parse_args()

    import torch
    from torch.optim import AdamW
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer, BertTokenizerFast, get_linear_schedule_with_warmup

    device = torch.device("mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = load_tokenizer(args.student, AutoTokenizer, BertTokenizerFast)

    config = AutoConfig.from_pretrained(args.student, num_labels=len(LABEL_NAMES))
    config.id2label = {index: name for index, name in enumerate(LABEL_NAMES)}
    config.label2id = dict(LABEL_TO_ID)
    if args.layers:
        config.num_hidden_layers = args.layers
    model = AutoModelForTokenClassification.from_pretrained(args.student, config=config, ignore_mismatched_sizes=True)
    model.to(device)
    total = sum(p.numel() for p in model.parameters())
    print(f"student {args.student}: {total/1e6:.1f}M params, {len(LABEL_NAMES)} labels, device {device}")

    train_rows, dev_rows = load(args.train), load(args.dev)
    print(f"train {len(train_rows)}, dev {len(dev_rows)}")
    encoded = encode(train_rows, tokenizer, args.max_length)
    dataset = torch.utils.data.TensorDataset(encoded["input_ids"], encoded["attention_mask"], encoded["labels"])
    loader = torch.utils.data.DataLoader(dataset, batch_size=args.batch_size, shuffle=True)

    steps = len(loader) * args.epochs
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(0.06 * steps), steps)

    best = -1.0
    started = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        running = 0.0
        for step, (ids, mask, labels) in enumerate(loader, start=1):
            loss = model(input_ids=ids.to(device), attention_mask=mask.to(device), labels=labels.to(device)).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            running += loss.item()
            if step % 100 == 0:
                print(f"  epoch {epoch} step {step}/{len(loader)} loss {running/step:.4f}")
        precision, recall, f1 = evaluate(model, tokenizer, dev_rows, args.max_length, device, args.batch_size)
        print(f"epoch {epoch}: dev P {precision:.4f} R {recall:.4f} F1 {f1:.4f}  [{time.perf_counter()-started:.0f}s]")
        if f1 > best:
            best = f1
            model.save_pretrained(args.out)
            tokenizer.save_pretrained(args.out)
            print(f"  saved new best to {args.out}")
    print(f"best dev F1 {best:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
