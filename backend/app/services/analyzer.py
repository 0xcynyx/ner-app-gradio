"""Analysis orchestration, the only place that knows the full pipeline order."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import List, Optional, Sequence

from app.domain.labels import spec_for
from app.domain.models import Analysis, Entity, LabelCount, RawSpan, Stats
from app.domain.ports import Chunker, ResultCache, TokenClassifier, Verifier
from app.services.aggregation import SpanAggregator, hydrate

# Risk weights, a national ID present matters more than many low sensitivity hits.
_BASE_WEIGHT = 15
_VOLUME_CAP = 25


class AnalyzerService:
    """Runs chunk, classify, aggregate, verify, and summarise for one document."""

    def __init__(
        self,
        classifier: TokenClassifier,
        chunker: Chunker,
        aggregator: SpanAggregator,
        verifier: Optional[Verifier] = None,
        cache: Optional[ResultCache] = None,
        max_characters: int = 50_000,
    ) -> None:
        self._classifier = classifier
        self._chunker = chunker
        self._aggregator = aggregator
        self._verifier = verifier
        self._cache = cache
        self._max_characters = max_characters

    def analyze(self, text: str, min_score: float = 0.5) -> Analysis:
        clipped = text[: self._max_characters]
        truncated = len(text) > self._max_characters
        if not clipped.strip():
            return Analysis(text=clipped, entities=[], stats=_empty_stats(len(clipped)), truncated=truncated)

        key = self._key(clipped, min_score)
        cached = self._cache.get(key) if self._cache else None
        if isinstance(cached, Analysis):
            return cached

        chunks = self._chunker.split(clipped)
        spans: List[RawSpan] = []
        for chunk in chunks:
            for span in self._classifier.classify(chunk.text):
                spans.append(
                    RawSpan(span.start + chunk.offset, span.end + chunk.offset, span.label, span.score)
                )

        entities = hydrate(clipped, self._aggregator.build(clipped, spans, min_score))
        if self._verifier:
            entities = self._verifier.verify(clipped, entities)

        result = Analysis(
            text=clipped,
            entities=entities,
            stats=_build_stats(clipped, entities, len(chunks)),
            truncated=truncated,
        )
        if self._cache:
            self._cache.put(key, result)
        return result

    def _key(self, text: str, min_score: float) -> str:
        """Cache key covers the text, the threshold, and the active model."""
        model = self._classifier.describe().get("model", "unknown")
        return hashlib.blake2s(f"{model}|{min_score}|{text}".encode(), digest_size=16).hexdigest()


def _build_stats(text: str, entities: Sequence[Entity], chunks: int) -> Stats:
    counts = Counter(entity.label for entity in entities)
    by_label = [
        LabelCount(label=label, display=spec_for(label).display, count=count, color=spec_for(label).color)
        for label, count in counts.most_common()
    ]
    return Stats(
        total=len(entities),
        by_label=by_label,
        risk=_risk(entities),
        characters=len(text),
        chunks=chunks,
    )


def _risk(entities: Sequence[Entity]) -> int:
    """Score 0 to 100 from the most sensitive type present plus a capped volume term."""
    if not entities:
        return 0
    peak = max(entity.sensitivity for entity in entities)
    volume = min(_VOLUME_CAP, len(entities) * 2)
    return min(100, peak * _BASE_WEIGHT + volume)


def _empty_stats(characters: int) -> Stats:
    return Stats(total=0, by_label=[], risk=0, characters=characters, chunks=0)
