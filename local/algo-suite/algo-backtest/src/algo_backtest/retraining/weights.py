"""Exponential recency weights and support feasibility (Story 19, T4; RWT-02/04/05/06).

Policy E weights each training observation by its age at the stage cutoff:

    age_days = (cutoff - available_at) / 86400      elapsed UTC days, fractional
    w_raw    = 2 ** (-age_days / half_life_days)    (RWT-04)
    w_norm   = n * w_raw / sum(w_raw)               mean one per fitting stage (RWT-05)
    n_eff    = sum(w)^2 / sum(w^2)                  weight concentration, not power

Raw weights are computed absolutely: a row far older than the representable range
underflows to an exact `0.0` and keeps the others' ratios intact; a stage whose raw
weights all underflow is rejected as zero total weight rather than renormalized from
nothing (pinned reading 1). Normalization is applied independently inside each fitting
stage so its weights sum to its row count and the regularization scale is unchanged.
Uniform weights are all ones. Invalid inputs (non-positive or non-finite half-life,
availability after the cutoff, naive or non-UTC timestamps, negative or non-finite
weights, zero total weight) are rejected, never repaired (RWT-02).

`check_support` compares measured counts with the registered minima and states every
violated minimum as "measured versus required" (RWT-06). Per-class minima are raw row
counts; only the effective N carries the weights (pinned reading 6).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from algo_backtest.retraining.utc import iso_utc, require_utc

_MODULE = "retraining.weights"
_SECONDS_PER_DAY = 86400.0


@dataclass(frozen=True)
class SupportMinima:
    """Registered minima for one fitting or calibration stage; `None` means not required."""

    min_rows: int
    min_per_class: int | None
    min_effective_n: float | None


REGISTERED_MINIMA: Mapping[str, SupportMinima] = {
    "family": SupportMinima(min_rows=1000, min_per_class=50, min_effective_n=200),
    "combiner": SupportMinima(min_rows=100, min_per_class=20, min_effective_n=50),
    "threshold": SupportMinima(min_rows=100, min_per_class=None, min_effective_n=None),
}


def _require_half_life(half_life_days: float) -> None:
    """A half-life must be a finite, strictly positive number of days."""
    if not math.isfinite(half_life_days):
        raise ValueError(
            f"{_MODULE}: half_life_days must be finite, got {half_life_days!r}; register a "
            "finite half-life (the protocol uses 60 days)"
        )
    if half_life_days <= 0:
        raise ValueError(
            f"{_MODULE}: half_life_days must be positive, got {half_life_days!r}; a "
            "non-positive half-life has no exponential-forgetting meaning"
        )


def _require_rows(count: int) -> None:
    """A stage needs at least one row to weight."""
    if count < 1:
        raise ValueError(
            f"{_MODULE}: at least one row is required, got {count}; an empty stage cannot "
            "be weighted (check the stage span and the row selection)"
        )


def age_days(available_at: Sequence[datetime], cutoff: datetime) -> tuple[float, ...]:
    """Elapsed UTC days from each row's availability to `cutoff`, fractional.

    Raises:
        ValueError: `cutoff` or an availability is not a UTC instant, no rows are given,
            or a row is available after the cutoff (a negative age).
    """
    require_utc(cutoff, what="cutoff")
    _require_rows(len(available_at))
    ages: list[float] = []
    for index, stamp in enumerate(available_at):
        require_utc(stamp, what=f"row {index} available_at")
        if stamp > cutoff:
            raise ValueError(
                f"{_MODULE}: row {index} available at {iso_utc(stamp)} is after the cutoff "
                f"{iso_utc(cutoff)} (a future availability has negative age); the stage "
                "span must not admit rows beyond its cutoff"
            )
        ages.append((cutoff - stamp).total_seconds() / _SECONDS_PER_DAY)
    return tuple(ages)


def exponential_weights(
    available_at: Sequence[datetime], cutoff: datetime, half_life_days: float
) -> tuple[float, ...]:
    """Raw weights `2 ** (-age_days / half_life_days)` per row (RWT-04), unnormalized.

    Raises:
        ValueError: an invalid half-life, cutoff or availability (see `age_days`), or
            every weight underflowed to zero so the stage has no total weight.
    """
    _require_half_life(half_life_days)
    ages = age_days(available_at, cutoff)
    weights = tuple(2.0 ** (-age / half_life_days) for age in ages)
    if sum(weights) == 0.0:
        raise ValueError(
            f"{_MODULE}: zero total weight: every raw weight underflowed to 0.0 for "
            f"half_life_days={half_life_days!r} (oldest age {max(ages)} days); the stage is "
            "unrepresentable at this half-life, not renormalizable"
        )
    return weights


def _validated_total(weights: Sequence[float]) -> float:
    """Sum of `weights` after rejecting empty, non-finite, negative and zero-mass inputs."""
    _require_rows(len(weights))
    for index, weight in enumerate(weights):
        if not math.isfinite(weight):
            raise ValueError(
                f"{_MODULE}: weight {index} is not finite ({weight!r}); weights must be "
                "finite non-negative numbers"
            )
        if weight < 0:
            raise ValueError(
                f"{_MODULE}: weight {index} is negative ({weight!r}); weights must be "
                "finite non-negative numbers"
            )
    total = sum(weights)
    if total == 0.0:
        raise ValueError(
            f"{_MODULE}: zero total weight over {len(weights)} rows; nothing can be "
            "normalized or fitted on an all-zero weight vector"
        )
    return total


def normalize_mean_one(weights: Sequence[float]) -> tuple[float, ...]:
    """`n * w / sum(w)`: the weights of one stage rescaled to sum to its row count (RWT-05)."""
    total = _validated_total(weights)
    count = len(weights)
    return tuple(count * weight / total for weight in weights)


def effective_n(weights: Sequence[float]) -> float:
    """`sum(w)^2 / sum(w^2)`: how concentrated the weights are, invariant to their scale."""
    total = _validated_total(weights)
    return total * total / sum(weight * weight for weight in weights)


def uniform_weights(count: int) -> tuple[float, ...]:
    """`count` weights of exactly 1.0: the unweighted fit expressed as weights."""
    _require_rows(count)
    return (1.0,) * count


def _class_counts(labels: Sequence[int]) -> dict[int, int]:
    """Raw row counts of the two classes, both keys always present."""
    counts = {0: 0, 1: 0}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return counts


def _row_violation(labels: Sequence[int], minimum: int) -> list[str]:
    """The row-count shortfall, if any."""
    if len(labels) < minimum:
        return [f"rows: measured {len(labels)}, required {minimum}"]
    return []


def _class_violations(labels: Sequence[int], minimum: int | None) -> list[str]:
    """Per-class raw row-count shortfalls, if a per-class minimum is registered."""
    if minimum is None:
        return []
    return [
        f"class {label}: measured {count}, required {minimum}"
        for label, count in sorted(_class_counts(labels).items())
        if count < minimum
    ]


def _effective_violation(weights: Sequence[float], minimum: float | None) -> list[str]:
    """The effective-N shortfall, if an effective-N minimum is registered."""
    if minimum is None:
        return []
    measured = effective_n(weights)
    if measured < minimum:
        return [f"effective N: measured {measured}, required {minimum}"]
    return []


def check_support(
    labels: Sequence[int], weights: Sequence[float], minima: SupportMinima, *, stage: str
) -> None:
    """Reject a stage whose rows, per-class rows or effective N fall below `minima` (RWT-06).

    Every violated minimum is reported together as "measured X, required Y" so a failed
    candidate names all of its shortfalls at once.

    Raises:
        ValueError: `labels` and `weights` differ in length, or any registered minimum is
            violated.
    """
    if len(labels) != len(weights):
        raise ValueError(
            f"{_MODULE}: {stage} stage has {len(labels)} labels but {len(weights)} weights; "
            "weights must be row-aligned with the labels"
        )
    violations = (
        _row_violation(labels, minima.min_rows)
        + _class_violations(labels, minima.min_per_class)
        + _effective_violation(weights, minima.min_effective_n)
    )
    if violations:
        raise ValueError(
            f"{_MODULE}: {stage} stage support is insufficient ({'; '.join(violations)}); "
            "the epoch candidate is rejected, widen the span or lower the registered minima "
            "by amendment"
        )
