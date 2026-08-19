"""Entity taxonomy for the Indonesian PII model, the single source of truth for label metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class LabelSpec:
    """Presentation and policy metadata for one entity type."""

    code: str
    display: str
    color: str
    sensitivity: int
    structured: bool


# Sensitivity drives the document risk score, 5 is a direct national identifier.
LABELS: Tuple[LabelSpec, ...] = (
    LabelSpec("PER", "Person", "#e2504f", 4, False),
    LabelSpec("LOC", "Location", "#d99b2b", 2, False),
    LabelSpec("DATE_TIME", "Date or time", "#8a63d2", 3, False),
    LabelSpec("EMAIL", "Email", "#2a9d8f", 4, True),
    LabelSpec("PHONE", "Phone", "#3b82c4", 4, True),
    LabelSpec("GENDER", "Gender", "#7d8597", 1, False),
    LabelSpec("SSN", "National ID", "#b5179e", 5, True),
)

BY_CODE: Dict[str, LabelSpec] = {spec.code: spec for spec in LABELS}


def spec_for(code: str) -> LabelSpec:
    """Return the spec for a label, falling back to a neutral one for unknown codes."""
    return BY_CODE.get(code, LabelSpec(code, code.title(), "#94a3b8", 2, False))


def strip_bio(raw: str) -> str:
    """Drop a BIO prefix so B-PER and I-PER both resolve to PER."""
    return raw[2:] if len(raw) > 2 and raw[1] == "-" else raw
