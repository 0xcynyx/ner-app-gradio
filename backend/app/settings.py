"""Environment driven settings, nothing operational is hardcoded in the modules that use it."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for one process."""

    backend: str
    model_id: str
    model_revision: str
    aggregation: str
    min_score: float
    window: int
    overlap: int
    max_characters: int
    max_batch: int
    cache_size: int
    pseudonym_salt: str
    cors_origins: str
    warmup: bool
    frontend_dir: str

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            backend=os.getenv("NER_BACKEND", "huggingface").strip().lower(),
            model_id=os.getenv("NER_MODEL_ID", "0xcynyx/ner-roberta-large-bahasa-indonesia-finetuned"),
            model_revision=os.getenv("NER_MODEL_REVISION", ""),
            aggregation=os.getenv("NER_AGGREGATION", "simple"),
            min_score=float(os.getenv("NER_MIN_SCORE", "0.5")),
            window=int(os.getenv("NER_WINDOW_CHARS", "1200")),
            overlap=int(os.getenv("NER_OVERLAP_CHARS", "200")),
            max_characters=int(os.getenv("NER_MAX_CHARACTERS", "50000")),
            max_batch=int(os.getenv("NER_MAX_BATCH", "50")),
            cache_size=int(os.getenv("NER_CACHE_SIZE", "128")),
            pseudonym_salt=os.getenv("NER_PSEUDONYM_SALT", ""),
            cors_origins=os.getenv("NER_CORS_ORIGINS", "*"),
            warmup=_flag("NER_WARMUP", "false"),
            frontend_dir=os.getenv("NER_FRONTEND_DIR", "static"),
        )

    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
