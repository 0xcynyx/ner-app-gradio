"""HTTP routes, each one translates DTOs to service calls and back."""

from __future__ import annotations

import csv
import io
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse

from app.api import schemas
from app.api.deps import get_container
from app.container import Container
from app.domain.labels import LABELS
from app.services.exporters import EXPORTERS, MEDIA_TYPES, format_names
from app.services.redaction import strategy_names

router = APIRouter(prefix="/api")


@router.get("/health", tags=["meta"])
def health(container: Container = Depends(get_container)) -> dict:
    return {"status": "ok", "backend": container.classifier.describe()["backend"]}


@router.get("/meta", response_model=schemas.MetaResponse, tags=["meta"])
def meta(container: Container = Depends(get_container)) -> schemas.MetaResponse:
    settings = container.settings
    return schemas.MetaResponse(
        model=container.classifier.describe(),
        labels=[schemas.LabelOut(**vars(spec)) for spec in LABELS],
        strategies=strategy_names(),
        formats=format_names(),
        limits={
            "max_characters": settings.max_characters,
            "max_batch": settings.max_batch,
            "default_min_score": settings.min_score,
            "window": settings.window,
        },
    )


@router.post("/analyze", response_model=schemas.AnalyzeResponse, tags=["analysis"])
def analyze(
    payload: schemas.AnalyzeRequest, container: Container = Depends(get_container)
) -> schemas.AnalyzeResponse:
    analysis = container.analyzer.analyze(payload.text, _score(payload, container))
    return schemas.AnalyzeResponse.of(analysis)


@router.post("/redact", response_model=schemas.RedactResponse, tags=["analysis"])
def redact(
    payload: schemas.RedactRequest, container: Container = Depends(get_container)
) -> schemas.RedactResponse:
    analysis = container.analyzer.analyze(payload.text, _score(payload, container))
    try:
        redaction = container.redactor.apply(
            text=analysis.text,
            entities=analysis.entities,
            strategy=payload.strategy,
            min_sensitivity=payload.min_sensitivity,
            include_mapping=payload.include_mapping,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return schemas.RedactResponse.of(analysis, redaction)


@router.post("/batch", response_model=schemas.BatchResponse, tags=["analysis"])
def batch(
    payload: schemas.BatchRequest, container: Container = Depends(get_container)
) -> schemas.BatchResponse:
    limit = container.settings.max_batch
    if len(payload.items) > limit:
        raise HTTPException(status_code=422, detail=f"batch limit is {limit} documents")
    score = _score(payload, container)
    items: List[schemas.BatchItemOut] = []
    total = 0
    for document in payload.items:
        try:
            analysis = container.analyzer.analyze(document.text, score)
            total += analysis.stats.total
            items.append(
                schemas.BatchItemOut(id=document.id, result=schemas.AnalyzeResponse.of(analysis))
            )
        except Exception as error:
            items.append(schemas.BatchItemOut(id=document.id, error=str(error)))
    return schemas.BatchResponse(items=items, documents=len(items), entities=total)


@router.post("/export", tags=["analysis"])
def export(payload: schemas.ExportRequest, container: Container = Depends(get_container)):
    exporter = EXPORTERS.get(payload.format)
    if exporter is None:
        raise HTTPException(status_code=422, detail=f"unknown format: {payload.format}")
    analysis = container.analyzer.analyze(payload.text, _score(payload, container))
    return PlainTextResponse(
        content=exporter(analysis),
        media_type=MEDIA_TYPES[payload.format],
        headers={"Content-Disposition": f'attachment; filename="entities.{payload.format}"'},
    )


@router.post("/upload", response_model=schemas.BatchResponse, tags=["analysis"])
async def upload(
    file: UploadFile = File(...), container: Container = Depends(get_container)
) -> schemas.BatchResponse:
    """Accepts a txt file as one document per line or a csv file with a text column."""
    raw = (await file.read()).decode("utf-8", errors="replace")
    documents = _parse_upload(file.filename or "", raw, container.settings.max_batch)
    if not documents:
        raise HTTPException(status_code=422, detail="no readable rows in file")
    return batch(schemas.BatchRequest(items=documents), container)


def _parse_upload(filename: str, raw: str, limit: int) -> List[schemas.BatchDocument]:
    """Pick the text column for csv input, otherwise treat each non empty line as a document."""
    if filename.lower().endswith(".csv"):
        reader = csv.DictReader(io.StringIO(raw))
        column = _text_column(reader.fieldnames or [])
        rows = [row.get(column, "") for row in reader] if column else []
    else:
        rows = raw.splitlines()
    return [
        schemas.BatchDocument(id=str(index + 1), text=value)
        for index, value in enumerate(rows[:limit])
        if value and value.strip()
    ]


def _text_column(fields: List[str]) -> str:
    """Prefer a column literally named text, else fall back to the first column."""
    for candidate in fields:
        if candidate.strip().lower() in {"text", "teks", "content", "isi"}:
            return candidate
    return fields[0] if fields else ""


def _score(payload: schemas.AnalyzeRequest, container: Container) -> float:
    return container.settings.min_score if payload.min_score is None else payload.min_score
