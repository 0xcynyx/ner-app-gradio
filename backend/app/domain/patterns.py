"""Indonesian PII surface formats, shared domain knowledge for verification and demo mode."""

from __future__ import annotations

import re
from typing import Dict, Pattern

# NIK is 16 digits, optionally grouped by dots or spaces, phones use +62 or a leading 0.
PATTERNS: Dict[str, Pattern[str]] = {
    "EMAIL": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "PHONE": re.compile(r"(?:\+62|\b62|\b0)[\s.\-]?8\d{1,3}(?:[\s.\-]?\d{2,4}){2,3}\b"),
    "SSN": re.compile(r"\b\d{4}[\s.]?\d{4}[\s.]?\d{4}[\s.]?\d{4}\b"),
}

MONTHS = (
    "januari", "februari", "maret", "april", "mei", "juni",
    "juli", "agustus", "september", "oktober", "november", "desember",
)
