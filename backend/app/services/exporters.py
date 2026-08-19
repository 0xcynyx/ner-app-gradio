"""Serialisers for analysis results, registered by format name."""

from __future__ import annotations

import csv
import io
import json
from typing import Callable, Dict, List

from app.domain.models import Analysis


def to_json(analysis: Analysis) -> str:
    payload = {
        "text": analysis.text,
        "stats": {
            "total": analysis.stats.total,
            "risk": analysis.stats.risk,
            "characters": analysis.stats.characters,
            "by_label": [
                {"label": item.label, "count": item.count} for item in analysis.stats.by_label
            ],
        },
        "entities": [_row(index, entity) for index, entity in enumerate(analysis.entities)],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def to_jsonl(analysis: Analysis) -> str:
    lines = [json.dumps(_row(i, e), ensure_ascii=False) for i, e in enumerate(analysis.entities)]
    return "\n".join(lines)


def to_csv(analysis: Analysis) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["index", "label", "text", "start", "end", "score", "verified"])
    writer.writeheader()
    for index, entity in enumerate(analysis.entities):
        writer.writerow(_row(index, entity))
    return buffer.getvalue()


def _row(index: int, entity) -> Dict[str, object]:
    return {
        "index": index,
        "label": entity.label,
        "text": entity.text,
        "start": entity.start,
        "end": entity.end,
        "score": round(entity.score, 4),
        "verified": entity.verified,
    }


EXPORTERS: Dict[str, Callable[[Analysis], str]] = {"json": to_json, "jsonl": to_jsonl, "csv": to_csv}

MEDIA_TYPES: Dict[str, str] = {
    "json": "application/json",
    "jsonl": "application/x-ndjson",
    "csv": "text/csv",
}


def format_names() -> List[str]:
    return sorted(EXPORTERS)
