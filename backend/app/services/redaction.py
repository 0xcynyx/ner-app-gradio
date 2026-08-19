"""Redaction strategies and the service that applies them.

Strategies register themselves in a table, so a new redaction mode is a new class plus one
registry entry and never an edit to the service, which keeps this open for extension.
"""

from __future__ import annotations

import hashlib
from typing import Callable, Dict, List, Sequence

from app.domain.labels import spec_for
from app.domain.models import Entity, Redaction

# Types where keeping a short suffix stays useful for support workflows.
_SUFFIX_TYPES = {"PHONE", "SSN"}


class MaskStrategy:
    """Replaces characters with a block glyph, preserving the original length."""

    name = "mask"

    def replace(self, entity: Entity) -> str:
        return "•" * len(entity.text)


class LabelStrategy:
    """Replaces the span with its bracketed entity type."""

    name = "label"

    def replace(self, entity: Entity) -> str:
        return f"[{entity.label}]"


class PseudonymStrategy:
    """Replaces the span with a stable per value token, keeping references consistent."""

    name = "pseudonym"

    def __init__(self, salt: str = "") -> None:
        self._salt = salt

    def replace(self, entity: Entity) -> str:
        digest = hashlib.blake2s(f"{self._salt}{entity.label}{entity.text.lower()}".encode(), digest_size=3)
        return f"{entity.label}_{digest.hexdigest()}"


class PartialStrategy:
    """Keeps the last four characters of identifiers and the email domain."""

    name = "partial"

    def replace(self, entity: Entity) -> str:
        if entity.label == "EMAIL" and "@" in entity.text:
            local, _, domain = entity.text.partition("@")
            return f"{local[:1]}{'•' * max(len(local) - 1, 1)}@{domain}"
        if entity.label in _SUFFIX_TYPES and len(entity.text) > 4:
            return f"{'•' * (len(entity.text) - 4)}{entity.text[-4:]}"
        return "•" * len(entity.text)


class RemoveStrategy:
    """Deletes the span entirely."""

    name = "remove"

    def replace(self, entity: Entity) -> str:
        return ""


# Factories keep the salt injectable without the registry knowing about settings.
STRATEGIES: Dict[str, Callable[[str], object]] = {
    MaskStrategy.name: lambda salt: MaskStrategy(),
    LabelStrategy.name: lambda salt: LabelStrategy(),
    PseudonymStrategy.name: lambda salt: PseudonymStrategy(salt),
    PartialStrategy.name: lambda salt: PartialStrategy(),
    RemoveStrategy.name: lambda salt: RemoveStrategy(),
}


def strategy_names() -> List[str]:
    return sorted(STRATEGIES)


class RedactionService:
    """Rewrites text by replacing entity spans from right to left so offsets stay valid."""

    def __init__(self, salt: str = "") -> None:
        self._salt = salt

    def apply(
        self,
        text: str,
        entities: Sequence[Entity],
        strategy: str = MaskStrategy.name,
        min_sensitivity: int = 0,
        include_mapping: bool = False,
    ) -> Redaction:
        factory = STRATEGIES.get(strategy)
        if factory is None:
            raise ValueError(f"unknown strategy: {strategy}")
        engine = factory(self._salt)

        targets = [e for e in entities if spec_for(e.label).sensitivity >= min_sensitivity]
        mapping: Dict[str, str] = {}
        out = text
        for entity in sorted(targets, key=lambda e: e.start, reverse=True):
            token = engine.replace(entity)
            mapping[entity.text] = token
            out = f"{out[:entity.start]}{token}{out[entity.end:]}"
        return Redaction(
            text=out,
            strategy=strategy,
            replaced=len(targets),
            mapping=mapping if include_mapping else {},
        )
