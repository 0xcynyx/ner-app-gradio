"""Core value objects, deliberately free of FastAPI, torch, and transformers imports."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from app.domain.labels import spec_for


@dataclass(frozen=True)
class RawSpan:
    """One entity as emitted by a token classifier, offsets are absolute in the source text."""

    start: int
    end: int
    label: str
    score: float


@dataclass(frozen=True)
class Entity:
    """A resolved entity ready for presentation."""

    start: int
    end: int
    label: str
    text: str
    score: float
    verified: bool = False

    @property
    def sensitivity(self) -> int:
        return spec_for(self.label).sensitivity


@dataclass(frozen=True)
class Chunk:
    """A window of source text plus the offset needed to map results back."""

    text: str
    offset: int


@dataclass(frozen=True)
class LabelCount:
    label: str
    display: str
    count: int
    color: str


@dataclass(frozen=True)
class Stats:
    """Aggregate view of one analysis, risk is 0 to 100."""

    total: int
    by_label: Sequence[LabelCount]
    risk: int
    characters: int
    chunks: int


@dataclass(frozen=True)
class Analysis:
    """Result of analysing a single document."""

    text: str
    entities: List[Entity]
    stats: Stats
    truncated: bool = False


@dataclass(frozen=True)
class Redaction:
    """Result of rewriting a document to remove entities."""

    text: str
    strategy: str
    replaced: int
    mapping: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BatchItem:
    """One document inside a batch request, id is echoed back for correlation."""

    id: str
    analysis: Optional[Analysis] = None
    error: Optional[str] = None
