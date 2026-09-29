"""Brokerage-adapter registry + factory: self-registering adapters, built by name.

Registry + Factory Method, mirroring ``algo_download.registry`` (``CLAUDE.md``
"Patterns in use"). A concrete adapter self-registers with ``@register`` at
import time, keyed by its ``name``; ``build_brokerage_adapter`` constructs one
by name and **fails fast** on an unknown name rather than defaulting, since the
brokerage model changes fill economics (never a silent default).

Kept separate from ``engine/brokerage/__init__.py`` (which imports each adapter
for its ``@register`` side effect) so an adapter module can import ``register``
from here without a circular import.
"""

from __future__ import annotations

from typing import Any

from .base import BrokerageAdapter

REGISTRY: dict[str, type[BrokerageAdapter]] = {}


class UnknownBrokerageAdapterError(LookupError):
    """Raised when no adapter is registered under the requested name."""


def register(cls: type[BrokerageAdapter]) -> type[BrokerageAdapter]:
    """Register a ``BrokerageAdapter`` subclass under its ``name`` (class decorator).

    Idempotent for the same class (safe re-import), but fails fast if a different
    class tries to claim a name already taken.
    """
    existing = REGISTRY.get(cls.name)
    if existing is not None and existing is not cls:
        raise ValueError(
            f"brokerage adapter name {cls.name!r} already registered by "
            f"{existing.__name__}; cannot also register {cls.__name__}. "
            f"Fix: give the new adapter a distinct name."
        )
    REGISTRY[cls.name] = cls
    return cls


def build_brokerage_adapter(name: str, **options: Any) -> BrokerageAdapter:
    """Construct the adapter registered under ``name``, passing ``options`` on.

    Raises:
        UnknownBrokerageAdapterError: naming the known adapters, rather than
            guessing — a typo must never silently select the wrong fill model.
    """
    try:
        cls = REGISTRY[name]
    except KeyError as exc:
        raise UnknownBrokerageAdapterError(
            f"unknown brokerage adapter: {name!r}; known adapters: {sorted(REGISTRY)}"
        ) from exc
    return cls(**options)
