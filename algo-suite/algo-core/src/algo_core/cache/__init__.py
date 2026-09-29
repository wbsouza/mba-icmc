"""Cache port and its dependency-free backends.

The port is read-through (`get_or_compute`): a key is computed once on a miss and
reused thereafter. Default backends are in-process (`LruCache`) and file-backed
(`LocalCache`); a containerized backend is an optional later upgrade behind the
same port. See SPEC.md §3 and algo-suite/docs/parquet-evaluation.md.
"""

from algo_core.cache.base import Cache
from algo_core.cache.factory import DEFAULT_BACKEND, build_cache, register_cache
from algo_core.cache.local import LocalCache
from algo_core.cache.lru import LruCache

__all__ = [
    "DEFAULT_BACKEND",
    "Cache",
    "LocalCache",
    "LruCache",
    "build_cache",
    "register_cache",
]
