"""Intensity history — frozen, causal monthly quantile snapshots (story 21, T3).

The relative news trigger (F4 `direction_source: intensity_relative`, T4) compares the
current bar's event intensity with the 10 % and 90 % quantiles of the intensities seen
over the trailing thirty calendar days. This module is the pure calculator of those
thresholds; nothing here reads Parquet, knows a pair or sees an outcome label.

Sampling contract (spec CC-09, CC-10, CC-13, CC-14; decisions D1, D2, D8):

- For a decision at UTC time `t` the **cutoff** M is the start of `t`'s UTC month and the
  **window** is `[M - 30 calendar days, M)` — `calibration_window(t)`. The window is thirty
  days before the fixed month start, never the previous calendar month and never the
  first trade of the month.
- One `IntensityObservation` per **completed signal bar**: `bar_closed_at` (UTC, on the
  `clock_minutes` grid, strictly increasing as recorded), `available_at` (UTC: when the
  value was knowable — its point-in-time provenance), a finite `intensity` and a
  non-empty `source_id`. Malformed, duplicated, unordered or off-grid observations are
  rejected and leave the history unchanged.
- The **sample** is every observation with `window_start <= bar_closed_at < cutoff` and
  `available_at < cutoff`. A bar closing exactly at the cutoff belongs to the next month;
  a value that became available at or after the cutoff is not in the sample (the row still
  counts as coverage of its bar).
- **Coverage**: once the declared collection (`collection_started_at`) reaches back to
  `window_start`, every bar close on the clock grid inside the window must have an
  observation, except bars lying wholly inside a documented market closure
  (`declare_closure(start, end)`). A missing bar, or an empty window, is a hard failure
  naming the interval and the fix (CC-13). A collection declared *after* `window_start`
  is a valid but incomplete initial collection: the snapshot is `WARMUP` with null
  quantiles, the trigger's cue to HOLD (CC-14). Warmup is never used to disguise a gap.
- **Quantiles**: values sorted; linear interpolation at index `(n - 1) * q`, q = 0.10 and
  0.90 — numpy `quantile(..., method="linear")` semantics, implemented here without numpy.
- **Frozen**: `snapshot_for` caches by cutoff, so the whole month reuses the snapshot
  computed at its first lookup; a mid-month start computes the same one; rows recorded
  later never change it (CC-10). A source revised after the freeze cannot rewrite a
  recorded bar (ordering rejects it); mismatch detection against a re-read archive is the
  integration lane's (T9/T13).

`IntensitySnapshot` carries the thresholds and their provenance (CC-31): cutoff,
window_start, clock_minutes, q_low, q_high, sample_count, max_closed_at, max_available_at,
source_hash (SHA-256 over the sampled observations, nothing else), quantile_method,
schema_version and status; `as_mapping` / `from_mapping` round-trip it through plain
JSON-safe values.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_WINDOW = timedelta(days=30)
QUANTILE_METHOD = "linear"
SCHEMA_VERSION = 1
READY, WARMUP = "READY", "WARMUP"
_Q_LOW, _Q_HIGH = 0.10, 0.90
_HISTORY = "IntensityHistory"


def _require_utc(value: datetime, *, what: str) -> None:
    """Fail fast on a naive or non-UTC datetime, naming which time it was."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(
            f"{what} must be timezone-aware UTC, got {value!r} — construct it with tzinfo=UTC"
        )


@dataclass(frozen=True)
class CalibrationWindow:
    """The month a decision belongs to: `[window_start, cutoff)` calibrates its thresholds."""

    cutoff: datetime
    window_start: datetime


def calibration_window(decision_time: datetime) -> CalibrationWindow:
    """The fixed UTC month start of `decision_time` and the thirty days before it (D1).

    Raises:
        ValueError: `decision_time` is naive or not UTC.
    """
    _require_utc(decision_time, what="decision_time")
    cutoff = decision_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return CalibrationWindow(cutoff=cutoff, window_start=cutoff - _WINDOW)


@dataclass(frozen=True)
class IntensityObservation:
    """One completed signal bar's intensity with its point-in-time provenance.

    Raises:
        ValueError: a naive/non-UTC time, a missing `available_at`, a nonfinite intensity
            or an empty `source_id`.
    """

    bar_closed_at: datetime
    available_at: datetime
    intensity: float
    source_id: str

    def __post_init__(self) -> None:
        """Validate provenance and value; the history validates grid and order."""
        _require_utc(self.bar_closed_at, what="bar_closed_at")
        closed = self.bar_closed_at.isoformat()
        if self.available_at is None:  # a Parquet/YAML row can carry a null
            raise ValueError(
                f"available_at is required for the bar closing at {closed} — record when the "
                "value became knowable (point-in-time provenance), never infer it"
            )
        _require_utc(self.available_at, what=f"available_at (bar closing at {closed})")
        if not math.isfinite(self.intensity):
            raise ValueError(
                f"intensity must be finite, got {self.intensity!r} for the bar closing at "
                f"{closed} — fix the source archive"
            )
        if not self.source_id:
            raise ValueError(
                f"source_id must be non-empty for the bar closing at {closed} — name the "
                "archive the value came from"
            )


def _iso(value: datetime | None) -> str | None:
    """A datetime as its ISO-8601 string, `None` kept as `None`."""
    return None if value is None else value.isoformat()


def _from_iso(value: object, *, key: str) -> datetime | None:
    """A mapping's ISO-8601 string back to an aware datetime, `None` kept as `None`."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"IntensitySnapshot.from_mapping: {key} must be an ISO string or null")
    parsed = datetime.fromisoformat(value)
    _require_utc(parsed, what=f"IntensitySnapshot.{key}")
    return parsed


@dataclass(frozen=True)
class IntensitySnapshot:
    """The frozen thresholds of one (clock, month) and their provenance (see module docstring).

    `q_low` / `q_high` are `None` only while `status` is `WARMUP`.
    """

    cutoff: datetime
    window_start: datetime
    clock_minutes: int
    q_low: float | None
    q_high: float | None
    sample_count: int
    max_closed_at: datetime | None
    max_available_at: datetime | None
    source_hash: str
    quantile_method: str
    schema_version: int
    status: str

    def as_mapping(self) -> dict[str, Any]:
        """The snapshot as plain JSON-safe values (datetimes as ISO-8601 strings)."""
        return {
            "cutoff": self.cutoff.isoformat(),
            "window_start": self.window_start.isoformat(),
            "clock_minutes": self.clock_minutes,
            "q_low": self.q_low,
            "q_high": self.q_high,
            "sample_count": self.sample_count,
            "max_closed_at": _iso(self.max_closed_at),
            "max_available_at": _iso(self.max_available_at),
            "source_hash": self.source_hash,
            "quantile_method": self.quantile_method,
            "schema_version": self.schema_version,
            "status": self.status,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> IntensitySnapshot:
        """The inverse of `as_mapping`.

        Raises:
            ValueError: a datetime field is not an ISO string, or a required key is absent.
            KeyError: a required key is absent.
        """
        cutoff = _from_iso(mapping["cutoff"], key="cutoff")
        window_start = _from_iso(mapping["window_start"], key="window_start")
        assert cutoff is not None and window_start is not None
        return cls(
            cutoff=cutoff,
            window_start=window_start,
            clock_minutes=int(mapping["clock_minutes"]),
            q_low=mapping["q_low"],
            q_high=mapping["q_high"],
            sample_count=int(mapping["sample_count"]),
            max_closed_at=_from_iso(mapping["max_closed_at"], key="max_closed_at"),
            max_available_at=_from_iso(mapping["max_available_at"], key="max_available_at"),
            source_hash=str(mapping["source_hash"]),
            quantile_method=str(mapping["quantile_method"]),
            schema_version=int(mapping["schema_version"]),
            status=str(mapping["status"]),
        )


def linear_quantile(sorted_values: list[float], q: float) -> float:
    """Linear interpolation at index `(n - 1) * q` of an ascending list (numpy `linear`).

    Raises:
        ValueError: the list is empty.
    """
    if not sorted_values:
        raise ValueError("linear_quantile: the sample is empty")
    position = (len(sorted_values) - 1) * q
    low = math.floor(position)
    high = min(low + 1, len(sorted_values) - 1)
    fraction = position - low
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * fraction


def _source_hash(sample: list[IntensityObservation]) -> str:
    """SHA-256 over the sampled observations (time order), nothing else."""
    digest = hashlib.sha256()
    for observation in sample:
        digest.update(
            f"{observation.bar_closed_at.isoformat()}|{observation.available_at.isoformat()}|"
            f"{observation.intensity!r}|{observation.source_id}\n".encode()
        )
    return digest.hexdigest()


@dataclass
class IntensityHistory:
    """The recorded observations of one pair and clock, and their frozen monthly snapshots.

    - ``clock_minutes``: the signal-bar clock (60 for H1, 240 for H4); bar closes must lie
      on this UTC grid.
    - ``collection_started_at``: from when the archive is declared complete. A window
      starting before it is WARMUP; one starting at or after it must be fully covered.

    Raises:
        ValueError: `clock_minutes` is not a positive integer or the start is not UTC.
    """

    clock_minutes: int
    collection_started_at: datetime
    _observations: list[IntensityObservation] = field(init=False, default_factory=list)
    _closures: list[tuple[datetime, datetime]] = field(init=False, default_factory=list)
    _snapshots: dict[datetime, IntensitySnapshot] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the clock and the declared collection start."""
        clock = self.clock_minutes
        if isinstance(clock, bool) or not isinstance(clock, int) or clock <= 0:
            raise ValueError(f"{_HISTORY}: clock_minutes must be a positive integer, got {clock!r}")
        _require_utc(self.collection_started_at, what=f"{_HISTORY}.collection_started_at")

    @property
    def observation_count(self) -> int:
        """How many observations have been recorded."""
        return len(self._observations)

    @property
    def last_closed_at(self) -> datetime | None:
        """The bar close of the newest observation, or `None` while empty."""
        return self._observations[-1].bar_closed_at if self._observations else None

    def declare_closure(self, start: datetime, end: datetime) -> None:
        """Register a documented market closure `[start, end]`: bars lying wholly inside it
        are not expected by the coverage check.

        Raises:
            ValueError: a naive/non-UTC bound, or `end` not after `start`.
        """
        _require_utc(start, what=f"{_HISTORY} closure start")
        _require_utc(end, what=f"{_HISTORY} closure end")
        if end <= start:
            raise ValueError(
                f"{_HISTORY}: closure end {end.isoformat()} must be after its start "
                f"{start.isoformat()}"
            )
        self._closures.append((start, end))

    def record(self, observation: IntensityObservation) -> None:
        """Append one completed bar's observation, in chronological order, on the grid.

        Raises:
            ValueError: the close is off the clock grid, or not strictly after the last
                recorded close (a duplicate, an out-of-order row, or a rewrite of a bar
                already recorded). The history is left unchanged.
        """
        closed = observation.bar_closed_at
        if (closed - _EPOCH) % timedelta(minutes=self.clock_minutes) != timedelta(0):
            raise ValueError(
                f"{_HISTORY}: bar_closed_at {closed.isoformat()} is not on the "
                f"{self.clock_minutes}-minute UTC grid — record one observation per completed "
                "signal bar at its close"
            )
        last = self.last_closed_at
        if last is not None and closed <= last:
            raise ValueError(
                f"{_HISTORY}: bar_closed_at {closed.isoformat()} is not after the last recorded "
                f"{last.isoformat()} — observations must arrive once each, in chronological "
                "order; a recorded bar is never rewritten in place"
            )
        self._observations.append(observation)

    def snapshot_for(self, decision_time: datetime) -> IntensitySnapshot:
        """The frozen snapshot of `decision_time`'s month, computed at its first lookup.

        Raises:
            ValueError: `decision_time` is not UTC; or the window the declared collection
                should cover is empty or misses a bar (CC-13).
        """
        window = calibration_window(decision_time)
        cached = self._snapshots.get(window.cutoff)
        if cached is None:
            cached = self._compute(window)
            self._snapshots[window.cutoff] = cached
        return cached

    def _compute(self, window: CalibrationWindow) -> IntensitySnapshot:
        """One month's snapshot from the observations recorded so far."""
        in_window = [
            o for o in self._observations if window.window_start <= o.bar_closed_at < window.cutoff
        ]
        sample = [o for o in in_window if o.available_at < window.cutoff]
        if self.collection_started_at > window.window_start:
            return self._snapshot(window, sample, status=WARMUP)
        self._check_coverage(window, in_window)
        if not sample:
            raise ValueError(
                f"{_HISTORY}: no observation in window {_interval(window)} was available "
                f"before the cutoff {window.cutoff.isoformat()} — check the archive's "
                "available_at provenance"
            )
        return self._snapshot(window, sample, status=READY)

    def _check_coverage(
        self, window: CalibrationWindow, in_window: list[IntensityObservation]
    ) -> None:
        """Every expected bar close of the window has an observation (closures exempt)."""
        if not in_window:
            raise ValueError(
                f"{_HISTORY}: no observations in window {_interval(window)} although the "
                f"collection is declared from {self.collection_started_at.isoformat()} — "
                "backfill the archive or declare the collection start honestly"
            )
        recorded = {o.bar_closed_at for o in in_window}
        for close in self._expected_closes(window):
            if close not in recorded:
                raise ValueError(
                    f"{_HISTORY}: no observation for the bar closing at {close.isoformat()} in "
                    f"window {_interval(window)} — backfill the archive or register the closure "
                    "with declare_closure(start, end)"
                )

    def _expected_closes(self, window: CalibrationWindow) -> list[datetime]:
        """Every grid close in `[window_start, cutoff)` not wholly inside a closure."""
        step = timedelta(minutes=self.clock_minutes)
        closes: list[datetime] = []
        close = window.window_start
        while close < window.cutoff:
            if not self._in_closure(close - step, close):
                closes.append(close)
            close += step
        return closes

    def _in_closure(self, bar_start: datetime, bar_end: datetime) -> bool:
        """Whether the bar `[bar_start, bar_end)` lies wholly inside a documented closure."""
        return any(start <= bar_start and bar_end <= end for start, end in self._closures)

    def _snapshot(
        self, window: CalibrationWindow, sample: list[IntensityObservation], *, status: str
    ) -> IntensitySnapshot:
        """Assemble the snapshot; quantiles only when READY."""
        values = sorted(o.intensity for o in sample)
        ready = status == READY
        return IntensitySnapshot(
            cutoff=window.cutoff,
            window_start=window.window_start,
            clock_minutes=self.clock_minutes,
            q_low=linear_quantile(values, _Q_LOW) if ready else None,
            q_high=linear_quantile(values, _Q_HIGH) if ready else None,
            sample_count=len(sample),
            max_closed_at=max((o.bar_closed_at for o in sample), default=None),
            max_available_at=max((o.available_at for o in sample), default=None),
            source_hash=_source_hash(sample),
            quantile_method=QUANTILE_METHOD,
            schema_version=SCHEMA_VERSION,
            status=status,
        )


def _interval(window: CalibrationWindow) -> str:
    """`[window_start, cutoff)` for messages."""
    return f"[{window.window_start.isoformat()}, {window.cutoff.isoformat()})"
