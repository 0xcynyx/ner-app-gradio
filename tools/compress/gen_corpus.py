"""Generates Indonesian sentences that carry PII, for teacher labelling.

Templates give dense coverage of the patterns that matter, and the slot pools are large enough
that the student sees thousands of distinct surface forms rather than memorising a few. Natural
corpus lines are mixed in separately so the student is not trained on templates alone.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import List

FIRST = ["Joko", "Siti", "Budi", "Ani", "Rina", "Agus", "Dewi", "Bambang", "Putri", "Eko", "Sri", "Andi",
         "Wahyu", "Indah", "Rizki", "Nur", "Tri", "Yusuf", "Fitri", "Hendra", "Lina", "Doni", "Maya", "Iwan",
         "Ratna", "Slamet", "Yuni", "Bayu", "Citra", "Dimas", "Erni", "Fajar", "Gita", "Hadi", "Ika", "Joni"]
LAST = ["Widodo", "Rahma", "Santoso", "Yudhoyono", "Marlina", "Salim", "Lestari", "Pamungkas", "Wijaya",
        "Hidayat", "Nugroho", "Saputra", "Kusuma", "Handoko", "Permata", "Setiawan", "Halim", "Utami",
        "Prasetyo", "Anggraini", "Firmansyah", "Wulandari", "Siregar", "Nasution", "Simbolon", "Ginting"]
PLACES = ["Jakarta", "Surakarta", "Bandung", "Surabaya", "Medan", "Yogyakarta", "Semarang", "Makassar",
          "Denpasar", "Palembang", "Malang", "Bogor", "Depok", "Tangerang", "Bekasi", "Padang", "Manado",
          "Balikpapan", "Pontianak", "Samarinda", "Banjarmasin", "Pekanbaru", "Jambi", "Mataram", "Kupang"]
STREETS = ["Jalan Merdeka", "Jalan Sudirman", "Jalan Thamrin", "Jalan Diponegoro", "Jalan Gatot Subroto",
           "Jalan Ahmad Yani", "Jalan Pahlawan", "Jalan Kartini"]
MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September",
          "Oktober", "November", "Desember"]
GENDERS = ["pria", "wanita", "perempuan", "laki-laki"]
DOMAINS = ["contoh.co.id", "mail.com", "surat.id", "kantor.co.id", "webmail.net", "pos.id"]

TEMPLATES = [
    "{PER} lahir di {LOC} pada tanggal {DATE_TIME}.",
    "Nama saya {PER}, {GENDER}, NIK {SSN}, HP {PHONE}.",
    "Silakan hubungi {PER} di {EMAIL} atau {PHONE}.",
    "Pasien {GENDER} bernama {PER} dari {LOC} datang pada {DATE_TIME}.",
    "Data {PER}: alamat {LOC}, email {EMAIL}, telepon {PHONE}, NIK {SSN}.",
    "{PER} dan {PER} sama sama tinggal di {LOC}.",
    "Surat untuk {PER} dikirim ke {LOC} pada {DATE_TIME}.",
    "Pemohon {PER} beralamat di {LOC} dengan nomor kontak {PHONE}.",
    "Verifikasi akun {EMAIL} milik {PER} sudah selesai pada {DATE_TIME}.",
    "Menurut catatan, {PER} seorang {GENDER} yang berdomisili di {LOC}.",
    "Nomor induk {SSN} terdaftar atas nama {PER}.",
    "Kirim tagihan ke {PER}, {LOC}, atau email {EMAIL}.",
    "Pada {DATE_TIME}, {PER} melakukan pendaftaran di kantor {LOC}.",
    "Kontak darurat: {PER}, {PHONE}.",
    "Berkas {PER} ({GENDER}) telah diterima tim {LOC}.",
    "Saya {PER}, tinggal di {LOC}, bisa dihubungi lewat {PHONE} atau {EMAIL}.",
    "Rekam medis {PER} tanggal {DATE_TIME} menunjukkan hasil normal.",
    "Undangan dikirim kepada {PER} di {LOC} untuk acara {DATE_TIME}.",
    "Petugas mencatat {PER} dengan NIK {SSN} dan alamat {LOC}.",
    "Balasan dari {EMAIL} diterima pada {DATE_TIME}.",
]


def person(rng: random.Random) -> str:
    if rng.random() < 0.25:
        return rng.choice(FIRST)
    if rng.random() < 0.12:
        return f"{rng.choice(FIRST)} {rng.choice(LAST)} {rng.choice(LAST)}"
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def place(rng: random.Random) -> str:
    roll = rng.random()
    if roll < 0.2:
        return f"{rng.choice(STREETS)} No. {rng.randint(1, 199)}, {rng.choice(PLACES)}"
    if roll < 0.3:
        return f"{rng.choice(STREETS)}, {rng.choice(PLACES)}"
    return rng.choice(PLACES)


def date(rng: random.Random) -> str:
    roll = rng.random()
    day, year = rng.randint(1, 28), rng.randint(1940, 2026)
    if roll < 0.45:
        return f"{day} {rng.choice(MONTHS)} {year}"
    if roll < 0.65:
        return f"{day}/{rng.randint(1, 12)}/{year}"
    if roll < 0.8:
        return f"{day} {rng.choice(MONTHS)}"
    return f"{day}-{rng.randint(1, 12)}-{year}"


def phone(rng: random.Random) -> str:
    body = f"{rng.randint(811, 899)}{rng.randint(1000000, 9999999)}"
    roll = rng.random()
    if roll < 0.35:
        return f"0{body}"
    if roll < 0.6:
        return f"+62 {body[:3]}-{body[3:7]}-{body[7:]}"
    if roll < 0.8:
        return f"0{body[:3]} {body[3:7]} {body[7:]}"
    return f"+62{body}"


def national_id(rng: random.Random) -> str:
    digits = "".join(str(rng.randint(0, 9)) for _ in range(16))
    if rng.random() < 0.4:
        return f"{digits[:4]} {digits[4:8]} {digits[8:12]} {digits[12:]}"
    return digits


def email(rng: random.Random) -> str:
    handle = rng.choice(FIRST).lower()
    roll = rng.random()
    if roll < 0.3:
        handle = f"{handle}.{rng.choice(LAST).lower()}"
    elif roll < 0.45:
        handle = f"{handle}{rng.randint(1, 99)}"
    elif roll < 0.55:
        handle = f"{handle}+{rng.choice(['kerja', 'pribadi', 'info'])}"
    return f"{handle}@{rng.choice(DOMAINS)}"


BUILDERS = {"PER": person, "LOC": place, "DATE_TIME": date, "GENDER": lambda r: r.choice(GENDERS),
            "PHONE": phone, "SSN": national_id, "EMAIL": email}


def render(template: str, rng: random.Random) -> str:
    """Fill every slot, leaving the sentence as plain text for the teacher to label."""
    text = template
    while "{" in text:
        start = text.index("{")
        end = text.index("}", start)
        label = text[start + 1:end]
        text = text[:start] + BUILDERS[label](rng) + text[end + 1:]
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PII bearing Indonesian sentences")
    parser.add_argument("--out", required=True)
    parser.add_argument("--count", type=int, default=30000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    lines: List[str] = [render(TEMPLATES[i % len(TEMPLATES)], rng) for i in range(args.count)]
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {len(lines)} sentences, {len(set(lines))} unique, to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
