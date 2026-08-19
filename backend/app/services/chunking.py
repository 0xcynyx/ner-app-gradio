"""Sliding window chunking, the model caps at 512 tokens so long documents need windows."""

from __future__ import annotations

import re
from typing import List

from app.domain.models import Chunk

# Prefer breaking after sentence punctuation, then any whitespace, to avoid splitting words.
_BOUNDARY = re.compile(r"[.!?\n]\s|\s")


class WindowChunker:
    """Splits text into overlapping character windows that map back to absolute offsets."""

    def __init__(self, window: int = 1200, overlap: int = 200) -> None:
        if window <= 0:
            raise ValueError("window must be positive")
        if not 0 <= overlap < window:
            raise ValueError("overlap must be non negative and smaller than window")
        self._window = window
        self._overlap = overlap

    def split(self, text: str) -> List[Chunk]:
        if not text:
            return []
        if len(text) <= self._window:
            return [Chunk(text=text, offset=0)]

        chunks: List[Chunk] = []
        start = 0
        while start < len(text):
            end = min(start + self._window, len(text))
            if end < len(text):
                end = self._snap(text, start, end)
            chunks.append(Chunk(text=text[start:end], offset=start))
            if end >= len(text):
                break
            start = max(end - self._overlap, start + 1)
        return chunks

    def _snap(self, text: str, start: int, end: int) -> int:
        """Pull the cut back to the last boundary in the final quarter of the window."""
        floor = start + (end - start) * 3 // 4
        matches = list(_BOUNDARY.finditer(text, floor, end))
        return matches[-1].end() if matches else end
