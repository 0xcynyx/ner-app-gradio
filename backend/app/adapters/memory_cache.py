"""Bounded in process cache, enough for a single container and safe across threads."""

from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional


class LruCache:
    """Least recently used cache with a hard entry count."""

    def __init__(self, capacity: int = 128) -> None:
        self._capacity = max(1, capacity)
        self._items: "OrderedDict[str, object]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[object]:
        with self._lock:
            if key not in self._items:
                return None
            self._items.move_to_end(key)
            return self._items[key]

    def put(self, key: str, value: object) -> None:
        with self._lock:
            self._items[key] = value
            self._items.move_to_end(key)
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)
