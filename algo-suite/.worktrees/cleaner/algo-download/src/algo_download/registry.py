"""Source registry + factory: self-registering adapters, built by name.

Registry + Factory Method (the same pattern as ``algo_core.cache``). A concrete
source self-registers with ``@register`` at import time, keyed by its ``name``;
``build_data_source`` constructs one by name and **fails fast** on an unknown
name rather than defaulting. Adding a source touches no other adapter.
"""

from __future__ import annotations

from typing import Any

from algo_download.source import DataSource

REGISTRY: dict[str, type[DataSource]] = {}


class UnknownSourceError(LookupError):
    """Raised when no source is registered under the requested name."""


def register(cls: type[DataSource]) -> type[DataSource]:
    """Register a ``DataSource`` subclass under its ``name`` (class decorator).

    Idempotent for the same class (safe re-import), but **fails fast** if a
    different class tries to claim a name already taken — silent overwrite in an
    import-side-effect registry is a subtle bug waiting to happen.
    """
    existing = REGISTRY.get(cls.name)
    if existing is not None and existing is not cls:
        raise ValueError(
            f"source name {cls.name!r} already registered by {existing.__name__}; "
            f"cannot also register {cls.__name__}. Fix: give the new source a distinct name."
        )
    REGISTRY[cls.name] = cls
    return cls


def build_data_source(name: str, **options: Any) -> DataSource:
    """Construct the source registered under ``name``, passing ``options`` on.

    Raises ``UnknownSourceError`` (listing the known names) rather than guessing,
    so a typo never silently selects the wrong feed.
    """
    try:
        cls = REGISTRY[name]
    except KeyError as exc:
        raise UnknownSourceError(
            f"unknown source: {name!r}; known sources: {sorted(REGISTRY)}"
        ) from exc
    return cls(**options)
