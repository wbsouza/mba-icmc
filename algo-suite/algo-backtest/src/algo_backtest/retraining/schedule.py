"""Exact-UTC epoch planning (Story 19, T3; RWT-01, RWT-02, RWT-03, RWT-09).

The registered study replays one continuous account per policy across monthly epochs.
Each epoch deploys over the half-open UTC month `[D, next D)` (RWT-03) and prepares its
model on half-open stage spans derived from `D` by the frozen temporal contract
(`method-design.md`, "Temporal contract"):

    C          = D - 1 day                      (preparation embargo)
    family fit = [start, C - 60d)               R: start = C - 60d - 180d
                                                U, E: start = 2015-03-02T00:00:00Z
    combiner   = [C - 60d, C - 30d)
    threshold  = [C - 30d, C)
    deployment = [D, next D)

F and Q keep the family and combiner spans of the schedule's initial epoch (they share
U's first bundle); Q refreshes its threshold span every month, F keeps the initial one.

Row membership (`select_rows`) is decided by feature availability, the bar close, never by
a bucket-start timestamp, and a row is admitted only if its label_time is strictly before
the span's end (RWT-01). The selector sees keys, availability, label_time and label only,
so trade execution, vetoes and realized profit cannot influence eligibility (RWT-09). The
legacy date-based `walk_forward_split` keeps its own inclusive day-end semantics.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from algo_backtest.retraining.ingestion import SourceRow, require_label_time
from algo_backtest.retraining.utc import iso_utc, require_utc

POLICIES = ("F", "Q", "R", "U", "E")
EXPANDING_START = datetime(2015, 3, 2, tzinfo=UTC)
_EMBARGO = timedelta(days=1)
_FAMILY_GAP = timedelta(days=60)
_COMBINER_DAYS = timedelta(days=30)
_THRESHOLD_DAYS = timedelta(days=30)
_ROLLING_DAYS = timedelta(days=180)
_MODULE = "retraining.schedule"


@dataclass(frozen=True)
class Span:
    """A half-open UTC interval `[start, end)`; invalid bounds are rejected on construction."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        """Both bounds must be UTC instants and the end strictly after the start."""
        require_utc(self.start, what="span start")
        require_utc(self.end, what="span end")
        if self.end <= self.start:
            raise ValueError(
                f"{_MODULE}: span end {iso_utc(self.end)} must be after its start "
                f"{iso_utc(self.start)}; an empty or inverted span selects nothing meaningful"
            )


@dataclass(frozen=True)
class Epoch:
    """One deployment month `[start, end)` plus the registered schedule's first `D`."""

    start: datetime
    end: datetime
    schedule_start: datetime


@dataclass(frozen=True)
class StageSpans:
    """The four half-open spans one policy uses to prepare and deploy an epoch."""

    policy: str
    family: Span
    combiner: Span
    threshold: Span
    deployment: Span


def _is_month_start(value: datetime) -> bool:
    """Whether `value` is exactly 00:00:00 on the first day of a month."""
    return value == value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _next_month(value: datetime) -> datetime:
    """The month start following `value` (itself a month start)."""
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1)
    return value.replace(month=value.month + 1)


def monthly_epochs(start: datetime, end: datetime) -> tuple[Epoch, ...]:
    """Contiguous half-open monthly epochs covering the registered span `[start, end)`.

    Raises:
        ValueError: a bound is not a UTC instant, `end` is not after `start`, or either
            bound is not a UTC month start (the schedule is defined on whole months).
    """
    span = Span(start, end)
    for name, bound in (("start", span.start), ("end", span.end)):
        if not _is_month_start(bound):
            raise ValueError(
                f"{_MODULE}: schedule {name} {iso_utc(bound)} must be a UTC month start "
                "(00:00:00 on the first of a month); epochs are whole calendar months"
            )
    epochs: list[Epoch] = []
    current = span.start
    while current < span.end:
        following = _next_month(current)
        epochs.append(Epoch(start=current, end=following, schedule_start=span.start))
        current = following
    return tuple(epochs)


def epoch_starting(epochs: Sequence[Epoch], start: datetime) -> Epoch:
    """The registered epoch deploying from `start`, or a failure naming the schedule."""
    for epoch in epochs:
        if epoch.start == start:
            return epoch
    raise ValueError(
        f"{_MODULE}: no epoch starting {iso_utc(start)} in the registered schedule "
        f"[{iso_utc(epochs[0].start)}, {iso_utc(epochs[-1].end)}); only its month starts "
        "are deployable"
    )


def _fitting_spans(deployment_start: datetime, *, rolling: bool) -> tuple[Span, Span]:
    """Family and combiner spans for a model prepared for the epoch deploying at `D`."""
    cutoff = deployment_start - _EMBARGO
    family_end = cutoff - _FAMILY_GAP
    family_start = family_end - _ROLLING_DAYS if rolling else EXPANDING_START
    return Span(family_start, family_end), Span(family_end, cutoff - _COMBINER_DAYS)


def _threshold_span(deployment_start: datetime) -> Span:
    """The threshold-calibration span for the epoch deploying at `D`."""
    cutoff = deployment_start - _EMBARGO
    return Span(cutoff - _THRESHOLD_DAYS, cutoff)


def stage_spans(epoch: Epoch, policy: str) -> StageSpans:
    """The temporal contract's stage spans for `epoch` under `policy` (F, Q, R, U or E).

    Raises:
        ValueError: `policy` is not one of the five registered policies.
    """
    if policy not in POLICIES:
        raise ValueError(
            f"{_MODULE}: unknown policy {policy!r}; the registered policies are "
            f"{', '.join(POLICIES)}"
        )
    model_anchor = epoch.schedule_start if policy in ("F", "Q") else epoch.start
    threshold_anchor = epoch.schedule_start if policy == "F" else epoch.start
    family, combiner = _fitting_spans(model_anchor, rolling=policy == "R")
    return StageSpans(
        policy=policy,
        family=family,
        combiner=combiner,
        threshold=_threshold_span(threshold_anchor),
        deployment=Span(epoch.start, epoch.end),
    )


def select_rows(rows: Sequence[SourceRow], span: Span) -> tuple[SourceRow, ...]:
    """Rows available in `[span.start, span.end)` whose label_time is before `span.end`.

    Input order is preserved. An empty result is a valid selection; whether it is enough
    to fit on is `weights.check_support`'s decision (RWT-06).

    Raises:
        ValueError: a row's label_time is `None`; unknown maturity is not maturity in the
            adaptive path (RWT-24).
    """
    selected: list[SourceRow] = []
    for row in rows:
        label_time = require_label_time(row)
        if span.start <= row.available_at < span.end and label_time < span.end:
            selected.append(row)
    return tuple(selected)
