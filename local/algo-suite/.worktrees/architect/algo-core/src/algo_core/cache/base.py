"""The Cache port: a read-through value cache."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class Cache(ABC):
    """Read-through cache: compute a key once on a miss, reuse it on every hit.

    Consumers depend only on this port, never on a concrete backend, so a
    backend swap (e.g. a containerized service for performance) touches no caller.
    """

    @abstractmethod
    def get_or_compute(self, key: str, compute: Callable[[], T]) -> T:
        """Return the cached value for ``key``; otherwise compute, store, return it.

        Args:
            key: the cache key; callers version it (e.g. include a model/feature
                version) so a stale entry is a different key, not a wrong hit.
            compute: a zero-argument thunk producing the value; invoked at most
                once per key (only on a miss).
        """
