"""Rule based classifier used for development, tests, and CI.

It satisfies the same port as the model adapter, so the API, the frontend, and every service
test can run with no torch install and no model download. It is never a quality substitute.
"""

from __future__ import annotations

import re
from typing import Dict, List

from app.domain.models import RawSpan
from app.domain.patterns import MONTHS, PATTERNS

# Small gazetteer so the fake backend produces believable PER and LOC hits in demos.
_PLACES = {
    "jakarta", "surakarta", "bandung", "surabaya", "medan", "yogyakarta", "bali",
    "semarang", "makassar", "palembang", "depok", "tangerang", "bekasi",
}
_GENDERS = {"pria", "wanita", "laki-laki", "perempuan", "male", "female"}
_MONTHS = set(MONTHS)

# Uppercase abbreviations that precede identifiers must not be mistaken for names.
_STOPWORDS = {
    "nik", "hp", "wa", "ktp", "npwp", "no", "tlp", "telp", "email", "id", "kk",
    "jl", "rt", "rw", "bpjs", "sim",
}

_WORD = re.compile(r"\b[\w.\-]+\b", re.UNICODE)
_DATE = re.compile(
    r"\b\d{1,2}\s+(?:" + "|".join(MONTHS) + r")(?:\s+\d{4})?\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    re.IGNORECASE,
)


class FakeClassifier:
    """Approximates the model with regex and a gazetteer at a deliberately modest score."""

    def classify(self, text: str) -> List[RawSpan]:
        spans: List[RawSpan] = []
        for label, pattern in PATTERNS.items():
            spans.extend(
                RawSpan(m.start(), m.end(), label, 0.95) for m in pattern.finditer(text)
            )
        spans.extend(RawSpan(m.start(), m.end(), "DATE_TIME", 0.9) for m in _DATE.finditer(text))
        spans.extend(self._words(text))
        return sorted(spans, key=lambda s: s.start)

    def _words(self, text: str) -> List[RawSpan]:
        """Capitalised words become PER unless the gazetteer claims them as LOC or GENDER."""
        found: List[RawSpan] = []
        for match in _WORD.finditer(text):
            token = match.group()
            lowered = token.lower()
            if lowered in _PLACES:
                found.append(RawSpan(match.start(), match.end(), "LOC", 0.9))
            elif lowered in _GENDERS:
                found.append(RawSpan(match.start(), match.end(), "GENDER", 0.85))
            elif token[:1].isupper() and match.start() > 0 and lowered not in _MONTHS and lowered not in _STOPWORDS:
                found.append(RawSpan(match.start(), match.end(), "PER", 0.7))
        return found

    def describe(self) -> Dict[str, str]:
        return {"backend": "fake", "model": "rule-based-demo", "loaded": "true"}
