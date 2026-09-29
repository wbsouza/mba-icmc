"""In-process least-recently used cache: the dependency-free default backend."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from typing import TypeVar, cast

from algo_core.cache.base import Cache

T = TypeVar("T")

_DEFAULT_MAXSIZE = 1024


class LruCache(Cache):
    """Bounded in-process LRU cache. Evicts the least-recently used key when full."""

    def __init__(self, maxsize: int = _DEFAULT_MAXSIZE) -> None:
        self._store: OrderedDict[str, object] = OrderedDict()
        self._maxsize = maxsize

    def get_or_compute(self, key: str, compute: Callable[[], T]) -> T:
        if key in self._store:
            self._store.move_to_end(key)
            return cast(T, self._store[key])
        value = compute()
        self._store[key] = value
        if len(self._store) > self._maxsize:
            self._store.popitem(last=False)
        return value
