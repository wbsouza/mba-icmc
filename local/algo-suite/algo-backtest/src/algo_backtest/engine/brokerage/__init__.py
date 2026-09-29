"""Adapter registration hub.

Importing this package imports each adapter for its ``@register`` side effect,
so ``build_brokerage_adapter`` can resolve every adapter by name. Adding an
adapter = a new module + one import line here; no other adapter is touched.
"""

from __future__ import annotations

from . import oanda  # noqa: F401
from .registry import (
    REGISTRY,
    UnknownBrokerageAdapterError,
    build_brokerage_adapter,
    register,
)

__all__ = [
    "REGISTRY",
    "UnknownBrokerageAdapterError",
    "build_brokerage_adapter",
    "register",
]
