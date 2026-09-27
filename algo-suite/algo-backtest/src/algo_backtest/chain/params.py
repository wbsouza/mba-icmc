"""Shared fail-fast parsing of one filter's section of a strategy `config.yaml`.

Each configurable filter owns a `parse_*_config(section, *, strategy)` that reads its own
section — `news_context` (F4), `risk_guard` (F5), `capital_mgmt` (F6), `meta_learner`
(F7) — of `strategies/<name>/config.yaml`. These helpers give those parsers one
vocabulary: every failure names the section, the key, the strategy and the fix, so a
typo in the YAML stops the run before the first bar instead of silently changing the
economics (CLAUDE.md fail-fast policy).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

Section = Mapping[str, Any]


def _where(section: str, key: str, strategy: str) -> str:
    """The `strategy: section.key` prefix every message starts with."""
    return f"strategy {strategy!r}: {section}.{key}"


def require_key(values: Section, key: str, *, section: str, strategy: str) -> Any:
    """The raw value at `key`; an explicit `null` counts as present, an absent key does not.

    Raises:
        ValueError: the key is absent from the section.
    """
    if key not in values:
        raise ValueError(
            f"{_where(section, key, strategy)} is missing — add it under '{section}:' in "
            f"strategies/{strategy}/config.yaml"
        )
    return values[key]


def _number(value: object, *, where: str) -> float:
    """`value` as a float; booleans and strings are rejected, not coerced."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{where} must be a number, got {value!r}")
    return float(value)


def require_number(values: Section, key: str, *, section: str, strategy: str) -> float:
    """A required numeric key (int or float; never a bool or a string)."""
    value = require_key(values, key, section=section, strategy=strategy)
    return _number(value, where=_where(section, key, strategy))


def optional_number(values: Section, key: str, *, section: str, strategy: str) -> float | None:
    """A required key whose value may be `null` (meaning: this parameter is disabled)."""
    value = require_key(values, key, section=section, strategy=strategy)
    return None if value is None else _number(value, where=_where(section, key, strategy))


def optional_int(values: Section, key: str, *, section: str, strategy: str) -> int | None:
    """A required key holding an integer or `null` (disabled); a fraction is rejected."""
    value = require_key(values, key, section=section, strategy=strategy)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"{_where(section, key, strategy)} must be an integer or null, got {value!r}"
        )
    return value


def require_bool(values: Section, key: str, *, section: str, strategy: str) -> bool:
    """A required boolean key; YAML `true`/`false` only, never `1`, `"yes"` or similar."""
    value = require_key(values, key, section=section, strategy=strategy)
    if not isinstance(value, bool):
        raise ValueError(f"{_where(section, key, strategy)} must be true or false, got {value!r}")
    return value


def require_positive(values: Section, key: str, *, section: str, strategy: str) -> float:
    """A required number that must be strictly greater than zero."""
    value = require_number(values, key, section=section, strategy=strategy)
    if value <= 0:
        raise ValueError(f"{_where(section, key, strategy)} must be > 0, got {value!r}")
    return value
