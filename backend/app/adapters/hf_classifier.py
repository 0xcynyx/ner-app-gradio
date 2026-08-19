"""Transformers backed classifier, the only module that imports torch or transformers."""

from __future__ import annotations

import logging
import threading
from typing import Dict, List

from app.domain.models import RawSpan

logger = logging.getLogger(__name__)


def _pick_device() -> int:
    """Return the transformers device index, preferring CUDA then Apple Metal then CPU."""
    try:
        import torch
    except ImportError:
        return -1
    if torch.cuda.is_available():
        return 0
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return 0
    return -1


class HuggingFaceClassifier:
    """Wraps a token classification pipeline and normalises its output into RawSpan."""

    def __init__(self, model_id: str, revision: str | None = None, aggregation: str = "simple") -> None:
        self._model_id = model_id
        self._revision = revision
        self._aggregation = aggregation
        self._pipe = None
        self._lock = threading.Lock()

    def warmup(self) -> None:
        """Force the model to load now so the first request does not pay for it."""
        self._ensure()

    def _ensure(self):
        """Load once, guarded so concurrent requests cannot build two pipelines."""
        if self._pipe is not None:
            return self._pipe
        with self._lock:
            if self._pipe is None:
                from transformers import pipeline

                logger.info("loading %s", self._model_id)
                kwargs = {"revision": self._revision} if self._revision else {}
                self._pipe = pipeline(
                    task="token-classification",
                    model=self._model_id,
                    aggregation_strategy=self._aggregation,
                    device=_pick_device(),
                    **kwargs,
                )
        return self._pipe

    def classify(self, text: str) -> List[RawSpan]:
        if not text.strip():
            return []
        raw = self._ensure()(text)
        return [
            RawSpan(
                start=int(item["start"]),
                end=int(item["end"]),
                label=str(item.get("entity_group") or item.get("entity") or "O"),
                score=float(item.get("score", 0.0)),
            )
            for item in raw
            if item.get("start") is not None and item.get("end") is not None
        ]

    def describe(self) -> Dict[str, str]:
        return {"backend": "huggingface", "model": self._model_id, "loaded": str(self._pipe is not None)}
