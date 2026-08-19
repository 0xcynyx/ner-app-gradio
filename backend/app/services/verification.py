"""Rule assisted repair for structured PII.

The model exposes only B- tags for EMAIL, PHONE, and SSN, so those entities carry no
continuation label and frequently arrive truncated. Regex both repairs the boundaries and
recovers instances the model missed, which raises recall on exactly the highest risk types.
"""

from __future__ import annotations

from typing import List, Sequence

from app.domain.models import Entity
from app.domain.patterns import PATTERNS

# A recovered match needs this score so it ranks alongside confident model output.
_RULE_SCORE = 0.99


class RegexVerifier:
    """Expands, confirms, and recovers the structured entity types."""

    def __init__(self, recover_missing: bool = True) -> None:
        self._recover = recover_missing

    def verify(self, text: str, entities: Sequence[Entity]) -> List[Entity]:
        matches = self._scan(text)
        repaired = [self._repair(entity, matches) for entity in entities]
        return self._add_missing(repaired, matches) if self._recover else repaired

    def _scan(self, text: str) -> List[Entity]:
        """Collect every regex hit as a candidate entity."""
        found: List[Entity] = []
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                found.append(
                    Entity(match.start(), match.end(), label, match.group(), _RULE_SCORE, True)
                )
        return found

    def _repair(self, entity: Entity, matches: Sequence[Entity]) -> Entity:
        """Snap a structured entity out to the full regex match it sits inside."""
        if entity.label not in PATTERNS:
            return entity
        for match in matches:
            if match.label != entity.label:
                continue
            if entity.start < match.end and match.start < entity.end:
                return Entity(
                    match.start, match.end, entity.label, match.text, max(entity.score, _RULE_SCORE), True
                )
        return entity

    def _add_missing(self, entities: Sequence[Entity], matches: Sequence[Entity]) -> List[Entity]:
        """Append regex hits that no model entity covers."""
        result = list(entities)
        for match in matches:
            if not any(match.start < e.end and e.start < match.end for e in result):
                result.append(match)
        return sorted(result, key=lambda e: e.start)
