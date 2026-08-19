"""Request and response DTOs, the wire contract kept separate from the domain objects."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.domain.models import Analysis, Entity, Redaction, Stats


class AnalyzeRequest(BaseModel):
    text: str = Field(default="", description="Document to analyse")
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class RedactRequest(AnalyzeRequest):
    strategy: str = Field(default="mask")
    min_sensitivity: int = Field(default=0, ge=0, le=5)
    include_mapping: bool = Field(default=False, description="Return original to token pairs")


class BatchDocument(BaseModel):
    id: str
    text: str = ""


class BatchRequest(BaseModel):
    items: List[BatchDocument] = Field(default_factory=list)
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ExportRequest(AnalyzeRequest):
    format: str = Field(default="json")


class EntityOut(BaseModel):
    start: int
    end: int
    label: str
    text: str
    score: float
    verified: bool
    sensitivity: int

    @classmethod
    def of(cls, entity: Entity) -> "EntityOut":
        return cls(
            start=entity.start,
            end=entity.end,
            label=entity.label,
            text=entity.text,
            score=round(entity.score, 4),
            verified=entity.verified,
            sensitivity=entity.sensitivity,
        )


class LabelCountOut(BaseModel):
    label: str
    display: str
    count: int
    color: str


class StatsOut(BaseModel):
    total: int
    risk: int
    characters: int
    chunks: int
    by_label: List[LabelCountOut]

    @classmethod
    def of(cls, stats: Stats) -> "StatsOut":
        return cls(
            total=stats.total,
            risk=stats.risk,
            characters=stats.characters,
            chunks=stats.chunks,
            by_label=[LabelCountOut(**vars(item)) for item in stats.by_label],
        )


class AnalyzeResponse(BaseModel):
    text: str
    truncated: bool
    stats: StatsOut
    entities: List[EntityOut]

    @classmethod
    def of(cls, analysis: Analysis) -> "AnalyzeResponse":
        return cls(
            text=analysis.text,
            truncated=analysis.truncated,
            stats=StatsOut.of(analysis.stats),
            entities=[EntityOut.of(entity) for entity in analysis.entities],
        )


class RedactResponse(BaseModel):
    text: str
    strategy: str
    replaced: int
    mapping: Dict[str, str]
    stats: StatsOut
    entities: List[EntityOut]

    @classmethod
    def of(cls, analysis: Analysis, redaction: Redaction) -> "RedactResponse":
        return cls(
            text=redaction.text,
            strategy=redaction.strategy,
            replaced=redaction.replaced,
            mapping=redaction.mapping,
            stats=StatsOut.of(analysis.stats),
            entities=[EntityOut.of(entity) for entity in analysis.entities],
        )


class BatchItemOut(BaseModel):
    id: str
    error: Optional[str] = None
    result: Optional[AnalyzeResponse] = None


class BatchResponse(BaseModel):
    items: List[BatchItemOut]
    documents: int
    entities: int


class LabelOut(BaseModel):
    code: str
    display: str
    color: str
    sensitivity: int
    structured: bool


class MetaResponse(BaseModel):
    model: Dict[str, str]
    labels: List[LabelOut]
    strategies: List[str]
    formats: List[str]
    limits: Dict[str, float]
