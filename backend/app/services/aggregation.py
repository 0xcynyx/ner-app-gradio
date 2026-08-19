"""Turns raw classifier spans into clean, non overlapping entities.

Merging is BIO aware on purpose. An I- span continues the entity before it, while a B- span
starts a new one, which is what keeps two adjacent people from fusing into a single name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from app.domain.labels import strip_bio
from app.domain.models import Entity, RawSpan

# Characters trimmed from span edges, models routinely include trailing punctuation.
_TRIM = " \t\n\r.,;:!?()[]{}\"'"


@dataclass
class _Candidate:
    """Working span that still remembers whether it was a continuation."""

    start: int
    end: int
    label: str
    score: float
    continuation: bool


class SpanAggregator:
    """Merges window duplicates and BIO continuations, then resolves label conflicts."""

    def __init__(self, min_score: float = 0.5) -> None:
        self._min_score = min_score

    def build(self, text: str, spans: Iterable[RawSpan], min_score: float | None = None) -> List[Entity]:
        threshold = self._min_score if min_score is None else min_score
        candidates = [c for c in (self._normalise(text, s) for s in spans) if c is not None]
        strong = [c for c in candidates if c.score >= threshold]
        merged = self._merge(text, strong)
        return self._resolve(merged)

    def _normalise(self, text: str, span: RawSpan) -> _Candidate | None:
        """Clamp offsets into range and trim edge noise, dropping spans that empty out."""
        start = max(0, min(span.start, len(text)))
        end = max(start, min(span.end, len(text)))
        surface = text[start:end]
        lead = len(surface) - len(surface.lstrip(_TRIM))
        tail = len(surface) - len(surface.rstrip(_TRIM))
        start, end = start + lead, end - tail
        if end <= start:
            return None
        return _Candidate(start, end, strip_bio(span.label), span.score, span.label.startswith("I-"))

    def _merge(self, text: str, candidates: Sequence[_Candidate]) -> List[_Candidate]:
        """Fuse spans of one type when they overlap or form a whitespace joined continuation."""
        kept: List[_Candidate] = []
        for candidate in sorted(candidates, key=lambda c: (c.start, -c.score)):
            target = self._mergeable(text, kept, candidate)
            if target is None:
                kept.append(candidate)
                continue
            target.end = max(target.end, candidate.end)
            target.score = max(target.score, candidate.score)
        return kept

    def _mergeable(self, text: str, kept: Sequence[_Candidate], candidate: _Candidate) -> _Candidate | None:
        """Find an earlier span of the same type this candidate should join, if any."""
        for existing in reversed(kept):
            if existing.label != candidate.label:
                continue
            if candidate.start < existing.end:
                return existing
            gap = text[existing.end : candidate.start]
            if candidate.continuation and (gap == "" or gap.isspace()):
                return existing
            break
        return None

    def _resolve(self, candidates: Sequence[_Candidate]) -> List[_Candidate]:
        """Drop cross label overlaps, the higher scoring span wins the characters."""
        ordered = sorted(candidates, key=lambda c: (-c.score, c.start))
        kept: List[_Candidate] = []
        for candidate in ordered:
            if any(candidate.start < other.end and other.start < candidate.end for other in kept):
                continue
            kept.append(candidate)
        return sorted(kept, key=lambda c: c.start)


def hydrate(text: str, candidates: Sequence[object]) -> List[Entity]:
    """Convert working spans into immutable entities carrying their surface text."""
    return [
        Entity(
            start=item.start,
            end=item.end,
            label=item.label,
            text=text[item.start : item.end],
            score=item.score,
            verified=getattr(item, "verified", False),
        )
        for item in candidates
    ]
