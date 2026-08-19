"""Protocols that invert the dependencies, services depend on these and never on adapters."""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, Sequence, runtime_checkable

from app.domain.models import Chunk, Entity, RawSpan


@runtime_checkable
class TokenClassifier(Protocol):
    """Anything that can turn text into labelled spans, model backed or rule backed."""

    def classify(self, text: str) -> List[RawSpan]: ...

    def describe(self) -> Dict[str, str]: ...


@runtime_checkable
class Chunker(Protocol):
    """Splits long text into windows the classifier can accept."""

    def split(self, text: str) -> List[Chunk]: ...


@runtime_checkable
class Verifier(Protocol):
    """Repairs and confirms structured entities the model tends to fragment."""

    def verify(self, text: str, entities: Sequence[Entity]) -> List[Entity]: ...


@runtime_checkable
class RedactionStrategy(Protocol):
    """Produces the replacement string for one entity occurrence."""

    name: str

    def replace(self, entity: Entity) -> str: ...


@runtime_checkable
class ResultCache(Protocol):
    """Optional memoisation so repeated documents skip inference."""

    def get(self, key: str) -> Optional[object]: ...

    def put(self, key: str, value: object) -> None: ...
