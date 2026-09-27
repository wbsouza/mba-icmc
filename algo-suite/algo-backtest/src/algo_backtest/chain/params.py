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


def optional_positive(
    values: Section, key: str, *, default: float, section: str, strategy: str
) -> float:
    """A number > 0 that falls back to `default` when the key is absent (never when `null`)."""
    if key not in values:
        return default
    return require_positive(values, key, section=section, strategy=strategy)


def require_non_negative(
    values: Section, key: str, *, default: float, section: str, strategy: str
) -> float:
    """A number >= 0 that falls back to `default` when the key is absent."""
    if key not in values:
        return default
    value = require_number(values, key, section=section, strategy=strategy)
    if value < 0:
        raise ValueError(f"{_where(section, key, strategy)} must be >= 0, got {value!r}")
    return value


def require_fraction(
    values: Section,
    key: str,
    *,
    default: float,
    section: str,
    strategy: str,
    low_inclusive: bool,
    high_inclusive: bool,
) -> float:
    """A number inside the unit interval, with each bound open or closed as requested,
    falling back to `default` when the key is absent."""
    if key not in values:
        return default
    value = require_number(values, key, section=section, strategy=strategy)
    above_low = value >= 0 if low_inclusive else value > 0
    below_high = value <= 1 if high_inclusive else value < 1
    if not (above_low and below_high):
        interval = f"{'[' if low_inclusive else '('}0, 1{']' if high_inclusive else ')'}"
        raise ValueError(
            f"{_where(section, key, strategy)} must be a fraction in {interval}, got {value!r}"
        )
    return value


def optional_choice(
    values: Section, key: str, *, default: str, choices: frozenset[str], section: str, strategy: str
) -> str:
    """A string drawn from `choices`, falling back to `default` when the key is absent."""
    value = values.get(key, default)
    if not isinstance(value, str) or value not in choices:
        raise ValueError(
            f"{_where(section, key, strategy)} must be one of {sorted(choices)}, got {value!r}"
        )
    return value


def reject_unknown_keys(
    values: Section, known: tuple[str, ...], *, section: str, strategy: str
) -> None:
    """Fail fast on a key the section's parser would otherwise silently ignore.

    Raises:
        ValueError: naming the unknown keys and the known ones, so a typo is fixed in
            `strategies/<strategy>/config.yaml` rather than quietly changing the economics.
    """
    unknown = sorted(set(values) - set(known))
    if unknown:
        raise ValueError(
            f"strategy {strategy!r}: {section} has unknown keys {unknown!r}; known keys: "
            f"{list(known)} — fix strategies/{strategy}/config.yaml"
        )
