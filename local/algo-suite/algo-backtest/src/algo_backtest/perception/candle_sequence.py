"""Doji-to-engulfing next-bar confirmation state machine (Story 22, T5).

A pure IDLE -> CANDIDATE -> CONFIRMED | EXPIRED state machine over closed bars.
A doji closed bar (the catalog's ``doji`` rule, reused from T3) opens a candidate.
The next closed bar either engulfs the candidate's body inclusively with the
matching colour (CONFIRMED, timestamped at the confirming bar's close) or does
not (EXPIRED); a missing expected bar under the calendar policy also expires the
candidate, even when its body would otherwise qualify. A bar that ends one
candidate and is itself a doji reports CANDIDATE with the ending reason, never
its own confirmation. Sequence evidence is separately typed from geometry and
context (T2's ``SequenceEvidence``). Pure: no chain, engine or LEAN dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from algo_backtest.perception.candle_catalog import evaluate_catalog
from algo_backtest.perception.candle_contract import (
    READY,
    CandleConfig,
    ClosedBar,
    SequenceEvidence,
    validate_bar,
)

_EPOCH: Final = datetime(1970, 1, 1, tzinfo=UTC)
_DOJI_CONFIG: Final = CandleConfig(enabled_rules=("doji",))


def _is_doji(bar: ClosedBar) -> bool:
    """Whether ``bar`` alone satisfies the catalog's doji rule (lookback 1, reused from T3).

    A non-firing READY rule is omitted from ``evaluate_catalog``'s output entirely
    (T3's spec-precision gap 2), so an empty result means the bar is not a doji.
    """
    hits = evaluate_catalog((bar,), _DOJI_CONFIG)
    return bool(hits) and hits[0].status == READY


def _confirmation_direction(open_d: float, close_d: float, bar: ClosedBar) -> int | None:
    """+1/-1 when ``bar`` is a qualifying engulfing confirmation of the doji body, else None."""
    low, high = min(open_d, close_d), max(open_d, close_d)
    if bar.close > bar.open and bar.open <= low and bar.close >= high:
        return 1
    if bar.close < bar.open and bar.open >= high and bar.close <= low:
        return -1
    return None


@dataclass(frozen=True)
class ScheduledClosure:
    """One calendar closure ``[start, end)``: the market is closed for that half-open interval."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        """Both bounds are UTC-aware and ``end`` is strictly after ``start``."""
        for name in ("start", "end"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
                raise ValueError(
                    f"ScheduledClosure.{name} must be a timezone-aware UTC datetime, got {value!r}"
                )
        if self.end <= self.start:
            raise ValueError(
                f"ScheduledClosure.end ({self.end.isoformat()}) must be strictly after "
                f"start ({self.start.isoformat()})"
            )


@dataclass(frozen=True)
class CalendarPolicy:
    """The continuous timeframe grid, optionally interrupted by scheduled closures."""

    closures: tuple[ScheduledClosure, ...] = ()

    def __post_init__(self) -> None:
        """Every closure is a ``ScheduledClosure``."""
        if any(not isinstance(closure, ScheduledClosure) for closure in self.closures):
            raise ValueError("closures must contain ScheduledClosure values only")


def _aligned_strictly_after(after: datetime, period: timedelta) -> datetime:
    """The earliest timeframe-aligned instant strictly after ``after``."""
    periods = (after - _EPOCH) // period
    return _EPOCH + (periods + 1) * period


def _expected_next_close(
    close_time: datetime, period: timedelta, policy: CalendarPolicy
) -> datetime:
    """The next expected close: continuous grid, or past a closure the grid would fall inside."""
    continuous = close_time + period
    for closure in policy.closures:
        if closure.start <= continuous < closure.end:
            return _aligned_strictly_after(closure.end, period)
    return continuous


class SequenceEvaluator:
    """Streaming IDLE/CANDIDATE/CONFIRMED/EXPIRED state machine over validated closed bars."""

    def __init__(
        self, *, timeframe_minutes: int = 60, policy: CalendarPolicy | None = None
    ) -> None:
        """Bind the timeframe and calendar policy; the machine starts IDLE with no history."""
        self._timeframe_minutes = timeframe_minutes
        self._period = timedelta(minutes=timeframe_minutes)
        self._policy = policy if policy is not None else CalendarPolicy()
        self._last_close_time: datetime | None = None
        self._candidate_close_time: datetime | None = None
        self._candidate_open: float | None = None
        self._candidate_close: float | None = None
        self._candidate_expected: datetime | None = None

    @property
    def candidate_close_time(self) -> datetime | None:
        """The pending candidate's close_time, or None while idle."""
        return self._candidate_close_time

    def update(self, bar: ClosedBar) -> SequenceEvidence:
        """Consume one closed bar and report its sequence evidence; invalid input raises first."""
        validated = validate_bar(
            bar,
            timeframe_minutes=self._timeframe_minutes,
            previous_close_time=self._last_close_time,
        )
        self._last_close_time = validated.close_time
        candidate_time = self._candidate_close_time
        resolution, direction = self._resolve(validated)
        if resolution == "confirmed":
            self._clear_candidate()
            return SequenceEvidence(
                "CONFIRMED", candidate_time, direction, validated.close_time, "confirmed"
            )
        if _is_doji(validated):
            return self._open_candidate(validated, resolution)
        if resolution is not None:
            self._clear_candidate()
            return SequenceEvidence("EXPIRED", candidate_time, None, None, resolution)
        return SequenceEvidence("IDLE", None, None, None, None)

    def _resolve(self, bar: ClosedBar) -> tuple[str | None, int | None]:
        """The pending candidate's outcome on ``bar``: reason and, when confirmed, direction."""
        if self._candidate_close_time is None:
            return None, None
        if bar.close_time != self._candidate_expected:
            return "missing_expected_bar", None
        assert self._candidate_open is not None
        assert self._candidate_close is not None
        direction = _confirmation_direction(self._candidate_open, self._candidate_close, bar)
        return ("confirmed", direction) if direction is not None else ("not_engulfing", None)

    def _open_candidate(self, bar: ClosedBar, reason: str | None) -> SequenceEvidence:
        """Start a new candidate at this doji bar; ``reason`` explains how the prior one ended."""
        self._candidate_close_time = bar.close_time
        self._candidate_open = bar.open
        self._candidate_close = bar.close
        self._candidate_expected = _expected_next_close(bar.close_time, self._period, self._policy)
        return SequenceEvidence("CANDIDATE", bar.close_time, None, None, reason)

    def _clear_candidate(self) -> None:
        """Drop the pending candidate."""
        self._candidate_close_time = None
        self._candidate_open = None
        self._candidate_close = None
        self._candidate_expected = None
