"""Separate-span threshold calibration (Story 19, T8; RWT-01, RWT-10).

Each epoch's q10 thresholds come from the reserved threshold span, never from the
combiner-fit rows and never time-weighted:

    theta_low  = quantile(scores, 0.10)     linear (numpy's default, type 7)
    theta_high = quantile(scores, 0.90)     unweighted

A scored row carries a key, its availability (bar close), its label_time and the epoch
model's score; rows join the span by the same half-open selector as every other stage
(`start <= available_at < end` and `label_time < end`, RWT-01) even though the label
itself is never used here. The result is rejected, never repaired, when fewer rows than
the registered minimum are admitted, when a score is non-finite, when the thresholds are
not strictly increasing (a tie), or when a threshold is not strictly inside (0, 1) —
F7's terminal rule needs a non-empty HOLD band.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from algo_backtest.retraining.schedule import Span
from algo_backtest.retraining.weights import REGISTERED_MINIMA

_MODULE = "retraining.thresholds"
_LOW_QUANTILE = 0.10
_HIGH_QUANTILE = 0.90
REGISTERED_MINIMUM_ROWS = REGISTERED_MINIMA["threshold"].min_rows


@dataclass(frozen=True)
class ScoredRow:
    """One row's epoch-model score for threshold calibration; its label is not used."""

    key: str
    available_at: datetime
    label_time: datetime
    score: float


@dataclass(frozen=True)
class ThresholdResult:
    """The calibrated q10/q90 thresholds plus the span and rows they were computed from."""

    theta_low: float
    theta_high: float
    span: Span
    row_keys: tuple[str, ...]

    @property
    def rows(self) -> int:
        """How many rows the span admitted and the quantiles were computed over."""
        return len(self.row_keys)


def select_scored_rows(rows: Sequence[ScoredRow], span: Span) -> tuple[ScoredRow, ...]:
    """Rows available in `[span.start, span.end)` whose label_time is before `span.end`
    (RWT-01); input order is preserved."""
    return tuple(
        row
        for row in rows
        if span.start <= row.available_at < span.end and row.label_time < span.end
    )


def _require_finite_scores(rows: Sequence[ScoredRow]) -> None:
    """Every admitted score must be finite before any quantile is computed."""
    for row in rows:
        if not math.isfinite(row.score):
            raise ValueError(
                f"{_MODULE}: row {row.key!r} has a non-finite score ({row.score!r}); every "
                "threshold-span score must be finite"
            )


def _require_probability(value: float, name: str) -> None:
    """A calibrated threshold must be a probability strictly inside (0, 1)."""
    if not 0.0 < value < 1.0:
        raise ValueError(
            f"{_MODULE}: {name} {value!r} must be strictly inside (0, 1); F7's terminal "
            "rule needs a non-empty HOLD band"
        )


def calibrate_thresholds(
    rows: Sequence[ScoredRow], span: Span, *, minimum_rows: int = REGISTERED_MINIMUM_ROWS
) -> ThresholdResult:
    """The threshold span's unweighted linear 0.10/0.90 score quantiles (RWT-10).

    Raises:
        ValueError: fewer admitted rows than `minimum_rows` (naming measured and required
            counts); a non-finite admitted score (naming the row's key); or the resulting
            thresholds are not strictly increasing, or not each strictly inside (0, 1).
    """
    admitted = select_scored_rows(rows, span)
    if len(admitted) < minimum_rows:
        raise ValueError(
            f"{_MODULE}: threshold stage support is insufficient (rows: measured "
            f"{len(admitted)}, required {minimum_rows}); widen the span or lower the "
            "registered minimum by amendment"
        )
    _require_finite_scores(admitted)
    scores = [row.score for row in admitted]
    theta_low = float(np.quantile(scores, _LOW_QUANTILE))
    theta_high = float(np.quantile(scores, _HIGH_QUANTILE))
    if not theta_low < theta_high:
        raise ValueError(
            f"{_MODULE}: non-increasing thresholds: theta_low {theta_low!r} is not "
            f"strictly below theta_high {theta_high!r}; the threshold span's scores do "
            "not spread enough to fit F7's HOLD band"
        )
    _require_probability(theta_low, "theta_low")
    _require_probability(theta_high, "theta_high")
    return ThresholdResult(
        theta_low=theta_low,
        theta_high=theta_high,
        span=span,
        row_keys=tuple(row.key for row in admitted),
    )
