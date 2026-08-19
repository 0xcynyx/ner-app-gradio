"""Builds a synthetic Indonesian PII test set with gold spans.

Templates give exact character offsets for free, which makes span level scoring possible
without hand annotation. It measures pattern coverage rather than natural text difficulty, so
treat the absolute numbers as a floor and the delta between variants as the real signal.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

NAMES = ["Joko Widodo", "Siti Rahma", "Budi Santoso", "Ani Yudhoyono", "Rina Marlina", "Agus Salim", "Dewi Lestari", "Bambang Pamungkas"]
PLACES = ["Jakarta", "Surakarta", "Bandung", "Surabaya", "Medan", "Yogyakarta", "Semarang", "Makassar", "Denpasar", "Palembang"]
DATES = ["21 Juni 1961", "3 Maret 1990", "17 Agustus 1945", "12/05/1988", "1 Januari 2020"]
GENDERS = ["pria", "wanita", "perempuan", "laki-laki"]
EMAILS = ["budi@contoh.co.id", "siti.rahma+kerja@contoh.co.id", "agus_salim@mail.com"]
PHONES = ["081234567890", "+62 812-3456-7890", "0857 1234 5678"]
IDS = ["3204012509900001", "3175 0405 8800 0012"]

# Each template names its slots so gold spans can be recovered by offset arithmetic.
TEMPLATES = [
    ("{PER} lahir di {LOC} pada tanggal {DATE_TIME}.", ["PER", "LOC", "DATE_TIME"]),
    ("Nama saya {PER}, {GENDER}, NIK {SSN}, HP {PHONE}.", ["PER", "GENDER", "SSN", "PHONE"]),
    ("Silakan hubungi {PER} di {EMAIL} atau {PHONE}.", ["PER", "EMAIL", "PHONE"]),
    ("Pasien {GENDER} bernama {PER} dari {LOC} datang pada {DATE_TIME}.", ["GENDER", "PER", "LOC", "DATE_TIME"]),
    ("Data {PER}: alamat {LOC}, email {EMAIL}, telepon {PHONE}, NIK {SSN}.", ["PER", "LOC", "EMAIL", "PHONE", "SSN"]),
    ("{PER} dan {PER} sama sama tinggal di {LOC}.", ["PER", "PER", "LOC"]),
    ("Surat untuk {PER} dikirim ke {LOC} pada {DATE_TIME}.", ["PER", "LOC", "DATE_TIME"]),
]

POOLS: Dict[str, List[str]] = {
    "PER": NAMES, "LOC": PLACES, "DATE_TIME": DATES, "GENDER": GENDERS,
    "EMAIL": EMAILS, "PHONE": PHONES, "SSN": IDS,
}


def render(template: str, slots: List[str], rng: random.Random) -> Tuple[str, List[dict]]:
    """Fill slots left to right, recording the offset of each inserted value."""
    text = template
    spans: List[dict] = []
    for label in slots:
        value = rng.choice(POOLS[label])
        placeholder = "{" + label + "}"
        index = text.index(placeholder)
        text = text[:index] + value + text[index + len(placeholder):]
        spans.append({"start": index, "end": index + len(value), "label": label, "text": value})
    return text, sorted(spans, key=lambda s: s["start"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a labelled Indonesian PII test set")
    parser.add_argument("--out", required=True)
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rows = []
    for index in range(args.count):
        template, slots = TEMPLATES[index % len(TEMPLATES)]
        text, spans = render(template, slots, rng)
        rows.append({"text": text, "entities": spans})

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    print(f"wrote {len(rows)} labelled sentences to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
