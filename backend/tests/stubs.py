"""Test doubles that satisfy the ports without loading a model."""

from __future__ import annotations

import re
from typing import Dict, List

from app.domain.models import RawSpan


class MarkerClassifier:
    """Labels every occurrence of given words, so expected offsets are known exactly."""

    def __init__(self, words: Dict[str, str], score: float = 0.9) -> None:
        self._words = words
        self._score = score
        self.calls: List[str] = []

    def classify(self, text: str) -> List[RawSpan]:
        self.calls.append(text)
        spans: List[RawSpan] = []
        for word, label in self._words.items():
            for match in re.finditer(re.escape(word), text):
                spans.append(RawSpan(match.start(), match.end(), label, self._score))
        return sorted(spans, key=lambda span: span.start)

    def describe(self) -> Dict[str, str]:
        return {"backend": "stub", "model": "marker"}
