"""Vocabulary pruning for a single language token classifier.

XLM-R carries a 250k piece vocabulary covering 100 languages, and for a 1024 wide model that
embedding table is 256M of the 559M parameters. Indonesian is Latin script, so every piece
containing a non Latin character can be dropped with no effect on how Indonesian text is
segmented. The script rebuilds the tokenizer over the kept pieces, slices the embedding rows
to match, and verifies that both tokenizers still produce the same token sequence.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Set

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

# SentencePiece marks word starts with this glyph, it must survive pruning.
_SP_SPACE = "▁"

# Latin letters, digits, and punctuation are all Indonesian needs.
_ALLOWED_CATEGORIES = {"Lu", "Ll", "Lt", "Lm", "Nd", "No", "Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk", "So", "Zs"}

_PROBE = [
    "Joko Widodo lahir di Surakarta pada tanggal 21 Juni 1961.",
    "Nama saya Budi, pria, NIK 3204 0125 0990 0001, HP +62 812-3456-7890.",
    "Silakan hubungi Siti di siti.rahma+kerja@contoh.co.id atau 081234567890.",
    "Ibu Ani tinggal di Jalan Merdeka No. 12, Bandung, Jawa Barat.",
    "Pasien perempuan berusia 45 tahun dengan diagnosis diabetes melitus tipe 2.",
]


def is_latin_piece(piece: str) -> bool:
    """Keep pieces whose every character is Latin script, a digit, or punctuation."""
    body = piece.lstrip(_SP_SPACE)
    if not body:
        return True
    for char in body:
        if char.isascii():
            continue
        category = unicodedata.category(char)
        if category not in _ALLOWED_CATEGORIES:
            return False
        try:
            if "LATIN" not in unicodedata.name(char):
                return False
        except ValueError:
            return False
    return True


def corpus_pieces(tokenizer, corpus: Path) -> Set[str]:
    """Collect every piece the tokenizer actually emits over a corpus file."""
    seen: Set[str] = set()
    with corpus.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line:
                seen.update(tokenizer.tokenize(line))
    return seen


def build_keep_set(tokenizer, mode: str, corpora: List[Path], floor: int) -> Set[str]:
    """Decide which pieces survive, with a safety net that guarantees any Latin text still tokenizes."""
    vocab = tokenizer.get_vocab()
    keep: Set[str] = set(tokenizer.all_special_tokens)

    # Short pieces and digit runs are the fallback segmentation for anything unseen.
    for piece in vocab:
        body = piece.lstrip(_SP_SPACE)
        if not body:
            keep.add(piece)
        elif body.isdigit():
            keep.add(piece)
        elif len(body) <= floor and is_latin_piece(piece):
            keep.add(piece)

    if mode == "latin":
        keep.update(piece for piece in vocab if is_latin_piece(piece))
        return keep

    if not corpora:
        raise SystemExit("corpus mode needs at least one --corpus")
    for corpus in corpora:
        keep.update(piece for piece in corpus_pieces(tokenizer, corpus) if piece in vocab)
    return keep


def rewrite_tokenizer(source: Path, destination: Path, keep: Set[str]) -> Dict[str, int]:
    """Filter the Unigram vocab in tokenizer.json and return the old id to new id mapping."""
    payload = json.loads((source / "tokenizer.json").read_text(encoding="utf-8"))
    model = payload["model"]
    if model.get("type") != "Unigram":
        raise SystemExit(f"expected a Unigram tokenizer, found {model.get('type')}")

    kept_entries: List[list] = []
    remap: Dict[int, int] = {}
    for old_id, entry in enumerate(model["vocab"]):
        if entry[0] in keep:
            remap[old_id] = len(kept_entries)
            kept_entries.append(entry)

    unk_id = model.get("unk_id", 0)
    if unk_id not in remap:
        raise SystemExit("the unk piece was pruned, refusing to continue")
    model["vocab"] = kept_entries
    model["unk_id"] = remap[unk_id]

    # Added tokens carry their own ids and must be renumbered alongside the vocab.
    for added in payload.get("added_tokens", []):
        if added["id"] in remap:
            added["id"] = remap[added["id"]]
    payload["added_tokens"] = [a for a in payload.get("added_tokens", []) if a["content"] in keep]

    destination.mkdir(parents=True, exist_ok=True)
    (destination / "tokenizer.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    for name in ("tokenizer_config.json", "special_tokens_map.json"):
        if (source / name).exists():
            shutil.copy(source / name, destination / name)
    return remap


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune a multilingual vocabulary to one script")
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mode", choices=("latin", "corpus"), default="latin")
    parser.add_argument("--corpus", type=Path, action="append", default=[])
    parser.add_argument("--floor", type=int, default=3, help="always keep Latin pieces this short")
    args = parser.parse_args()

    out = Path(args.out)
    cache = out.parent / "_source_tokenizer"
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    tokenizer.save_pretrained(cache)

    model = AutoModelForTokenClassification.from_pretrained(args.model)
    before = sum(p.numel() for p in model.parameters())

    keep = build_keep_set(tokenizer, args.mode, args.corpus, args.floor)
    remap = rewrite_tokenizer(cache, out, keep)
    print(f"vocabulary {len(tokenizer.get_vocab())} -> {len(remap)} pieces")

    embeddings = model.get_input_embeddings().weight.data
    pruned = torch.empty((len(remap), embeddings.shape[1]), dtype=embeddings.dtype)
    for old_id, new_id in remap.items():
        pruned[new_id] = embeddings[old_id]

    model.resize_token_embeddings(len(remap))
    model.get_input_embeddings().weight.data.copy_(pruned)
    model.config.vocab_size = len(remap)
    after = sum(p.numel() for p in model.parameters())
    model.save_pretrained(out)
    print(f"parameters {before/1e6:.1f}M -> {after/1e6:.1f}M ({100 * (1 - after / before):.1f}% smaller)")

    rate = divergence_rate(args.model, out, remap, args.corpus)
    if args.mode == "latin":
        if rate > 0:
            print(f"VERIFICATION FAILED, {rate:.2%} of sentences re-segmented", file=sys.stderr)
            return 1
        print("verified: pruned tokenizer maps to identical embedding rows, tokenization unchanged")
        return 0
    # Corpus mode drops pieces by design, so re-segmentation is expected and must be measured.
    print(f"tokenization changed on {rate:.2%} of sampled sentences, validate with evaluate.py")
    return 0


def divergence_rate(original: str, pruned_dir: Path, remap: Dict[int, int], corpora: List[Path]) -> float:
    """Share of sampled sentences whose tokenization changed after pruning."""
    old = AutoTokenizer.from_pretrained(original)
    new = AutoTokenizer.from_pretrained(pruned_dir)
    samples = list(_PROBE)
    for corpus in corpora:
        if corpus.exists():
            lines = [l.strip() for l in corpus.read_text(encoding="utf-8", errors="replace").splitlines()]
            samples.extend(l for l in lines[:500] if len(l) > 20)
    changed = 0
    for sentence in samples:
        translated = [remap.get(i, -1) for i in old(sentence)["input_ids"]]
        if translated != new(sentence)["input_ids"]:
            changed += 1
    return changed / max(len(samples), 1)


if __name__ == "__main__":
    raise SystemExit(main())
