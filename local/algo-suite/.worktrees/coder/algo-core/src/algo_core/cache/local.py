"""Persistent local cache: an in-process memory tier over a durable disk tier.

Read-through and write-through: a value computed once is reused from memory
within a process and from disk across processes or restarts. The memory tier is
any ``Cache`` (from the factory, default ``LruCache``), injected so it is
swappable and testable; the disk tier (de)serializes pydantic value objects as
JSON, keyed by a hash of the cache key.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

from pydantic import BaseModel

from algo_core.atomicio import write_text_atomic
from algo_core.cache.base import Cache
from algo_core.cache.factory import build_cache

T = TypeVar("T")


class LocalCache(Cache):
    """Two-tier cache: a memory ``Cache`` in front of a JSON-on-disk tier.

    Bound to a pydantic ``model`` so the disk tier can deserialize; cached values
    must be instances of that model.
    """

    def __init__(
        self, model: type[BaseModel], directory: Path, memory: Cache | None = None
    ) -> None:
        """Bind to a value-object type and directory; default the memory tier to the factory."""
        self._model = model
        self._directory = directory
        self._memory = memory if memory is not None else build_cache()

    def get_or_compute(self, key: str, compute: Callable[[], T]) -> T:
        """Resolve through the memory tier, falling back to disk, then to ``compute``."""
        return self._memory.get_or_compute(key, lambda: self._load_or_compute(key, compute))

    def _load_or_compute(self, key: str, compute: Callable[[], T]) -> T:
        """Return the value from the disk if present, else compute it and persist it."""
        path = self._path_for(key)
        if path.exists():
            return cast(T, self._model.model_validate_json(path.read_text()))
        value = compute()
        self._persist(path, value)
        return value

    @staticmethod
    def _persist(path: Path, value: object) -> None:
        """Write a pydantic value object to disk as JSON, atomically.

        Writes to a unique temp file then ``os.replace`` (atomic on the same
        filesystem), so a crash mid-write never leaves a corrupt cache entry and
        concurrent writers do not collide.
        """
        if not isinstance(value, BaseModel):
            raise TypeError("LocalCache only persists pydantic value objects")
        write_text_atomic(path, value.model_dump_json())

    def _path_for(self, key: str) -> Path:
        """Map a cache key to a stable on-disk filename (hashed to avoid charset issues)."""
        digest = hashlib.sha256(key.encode()).hexdigest()
        return self._directory / f"{digest}.json"
