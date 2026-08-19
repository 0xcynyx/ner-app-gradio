---
title: NER Studio Bahasa Indonesia
emoji: 🔎
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# NER Studio, Bahasa Indonesia

Named entity recognition and PII redaction for Indonesian text, built on
[ner-roberta-large-bahasa-indonesia-finetuned](https://huggingface.co/0xcynyx/ner-roberta-large-bahasa-indonesia-finetuned).
A FastAPI service with a layered core and a React frontend, shipped as one container.

The model detects seven types: person, location, date or time, email, phone, gender, and
Indonesian national ID. That makes it a PII scanner, so the app is built around finding
identifiers and then removing them.

## What it does beyond the original demo

| Capability | Why it matters |
|---|---|
| Long document support | The model caps at 512 tokens. Text is split into overlapping windows and offsets are mapped back, so a full page is analysed instead of silently cut. |
| Rule assisted structured PII | Email, phone, and national ID have no continuation label in the model, so they arrive fragmented. Regex repairs the boundaries and recovers missed values, then marks them verified. |
| Five redaction strategies | Mask, label, pseudonym, partial, and remove. Pseudonym is stable per value, so the same person stays linkable across a corpus without exposing the name. |
| Sensitivity scoped redaction | Redact only what crosses a sensitivity level, for example national ID alone. |
| PII risk score | A 0 to 100 score from the most sensitive type present plus a capped volume term. |
| Confidence control | A live minimum score threshold, with per entity scores in the table and tooltips. |
| Batch and file input | Many documents at once, or upload a txt file as one document per line or a csv with a text column. |
| Exports | JSON, JSONL, and CSV downloads. |
| Correct entity boundaries | Adjacent same type entities no longer fuse, so "Joko dan Prabowo" stays two people. |
| Demo backend | A rule based classifier satisfies the same interface, so the UI and the full test suite run with no model download. |

## Run with Docker

```bash
docker compose up --build
```

Open http://localhost:7860. The first start downloads the model, roughly 2.2 GB.

To try the interface with no model download:

```bash
NER_BACKEND=fake docker compose up --build
```

## Run locally

```bash
make install
make dev      # API on 8000 with the rule based backend
make web      # React dev server on 5173, proxies /api
```

For the real model, install the extra requirements and use the model backend:

```bash
backend/.venv/bin/pip install -r backend/requirements-model.txt
make api
```

## Configuration

Everything is environment driven, nothing operational is hardcoded.

| Variable | Default | Purpose |
|---|---|---|
| NER_BACKEND | huggingface | `huggingface` or `fake` |
| NER_MODEL_ID | 0xcynyx/ner-roberta-large-bahasa-indonesia-finetuned | Model to load |
| NER_MODEL_REVISION | empty | Pin a specific commit |
| NER_MIN_SCORE | 0.5 | Default confidence floor |
| NER_WINDOW_CHARS | 1200 | Window size for long text |
| NER_OVERLAP_CHARS | 200 | Overlap between windows |
| NER_MAX_CHARACTERS | 50000 | Hard input cap per document |
| NER_MAX_BATCH | 50 | Documents per batch request |
| NER_CACHE_SIZE | 128 | Result cache entries, 0 disables |
| NER_PSEUDONYM_SALT | empty | Salt for the pseudonym strategy |
| NER_WARMUP | false | Load the model at startup |
| NER_CORS_ORIGINS | * | Comma separated origins |
| NER_FRONTEND_DIR | static | Built bundle to serve |

## API

Interactive docs at `/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | /api/health | Liveness and active backend |
| GET | /api/meta | Labels, strategies, formats, limits |
| POST | /api/analyze | Entities, stats, and risk for one document |
| POST | /api/redact | Rewritten text plus the entities behind it |
| POST | /api/batch | Many documents in one call |
| POST | /api/upload | txt or csv file, returns a batch result |
| POST | /api/export | Download entities as json, jsonl, or csv |

```bash
curl -X POST http://localhost:7860/api/redact \
  -H 'Content-Type: application/json' \
  -d '{"text":"Budi, NIK 3204 0125 0990 0001, HP 081234567890","strategy":"label"}'
```

## Architecture

Layers depend inward only, so the model library sits behind an interface and never leaks into
the services. See [ARCHITECTURE.md](ARCHITECTURE.md) for the diagrams and the reasoning.

```
frontend/           React and TypeScript, API client isolated from components
backend/app/domain  value objects, label taxonomy, PII patterns, ports
backend/app/services chunking, aggregation, verification, redaction, analysis, exporters
backend/app/adapters transformers classifier, rule based classifier, cache
backend/app/api     routes and DTOs
backend/app/container composition root, the only module that knows every concrete class
```

## Tests

```bash
make test
```

49 backend tests cover chunking, BIO aggregation, regex verification, every redaction
strategy, cross window offset mapping, caching, and all endpoints. They run without torch
because the classifier is injected.

## Limitations

- Scores come from the model and are not calibrated probabilities.
- Gender detection is a lexical signal, treat it as a hint.
- The pseudonym mapping re identifies people, so return it only in trusted contexts.
- Redaction reduces risk, it is not a compliance guarantee. Review sensitive output.

## License

MIT
