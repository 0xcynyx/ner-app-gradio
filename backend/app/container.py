"""Composition root, the one module allowed to know every concrete class."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.adapters.fake_classifier import FakeClassifier
from app.adapters.hf_classifier import HuggingFaceClassifier
from app.adapters.memory_cache import LruCache
from app.domain.ports import TokenClassifier
from app.services.aggregation import SpanAggregator
from app.services.analyzer import AnalyzerService
from app.services.chunking import WindowChunker
from app.services.redaction import RedactionService
from app.services.verification import RegexVerifier
from app.settings import Settings


def build_classifier(settings: Settings) -> TokenClassifier:
    """Select the classifier adapter, the rest of the app never learns which one won."""
    if settings.backend == "fake":
        return FakeClassifier()
    return HuggingFaceClassifier(
        model_id=settings.model_id,
        revision=settings.model_revision or None,
        aggregation=settings.aggregation,
    )


@dataclass(frozen=True)
class Container:
    """Assembled services handed to the API layer."""

    settings: Settings
    classifier: TokenClassifier
    analyzer: AnalyzerService
    redactor: RedactionService

    @classmethod
    def build(cls, settings: Optional[Settings] = None) -> "Container":
        resolved = settings or Settings.load()
        classifier = build_classifier(resolved)
        analyzer = AnalyzerService(
            classifier=classifier,
            chunker=WindowChunker(window=resolved.window, overlap=resolved.overlap),
            aggregator=SpanAggregator(min_score=resolved.min_score),
            verifier=RegexVerifier(),
            cache=LruCache(resolved.cache_size) if resolved.cache_size > 0 else None,
            max_characters=resolved.max_characters,
        )
        return cls(
            settings=resolved,
            classifier=classifier,
            analyzer=analyzer,
            redactor=RedactionService(salt=resolved.pseudonym_salt),
        )
