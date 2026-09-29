"""Cache backend factory: select a Cache implementation by name.

Registry + factory method (the same pattern the suite uses for data-source
adapters). Only the in-process ``LruCache`` is registered today; a future
containerized backend (Redis, Aerospike, ...) registers itself with
``@register_cache`` and is selected by config name, with no caller change. This
keeps the road prepared without building a backend we do not yet need.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from algo_core.cache.base import Cache
from algo_core.cache.lru import LruCache

CacheFactory = Callable[..., Cache]

_BACKENDS: dict[str, CacheFactory] = {}

DEFAULT_BACKEND = "lru"


def register_cache(name: str) -> Callable[[CacheFactory], CacheFactory]:
    """Register a cache-backend constructor under ``name`` (decorator)."""

    def decorator(factory: CacheFactory) -> CacheFactory:
        _BACKENDS[name] = factory
        return factory

    return decorator


def build_cache(name: str = DEFAULT_BACKEND, **options: Any) -> Cache:
    """Construct the named cache backend, passing ``options`` to its constructor.

    Raises ``ValueError`` if no backend is registered under ``name``.
    """
    try:
        factory = _BACKENDS[name]
    except KeyError as exc:
        raise ValueError(f"unknown cache backend: {name!r}") from exc
    return factory(**options)


register_cache(DEFAULT_BACKEND)(LruCache)
