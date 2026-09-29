"""Confluence preflight — input population and point-in-time availability (story 21, T9).

Binds actual input coverage, population counts and news availability to each of the
fourteen cells before any is launched (spec CC-08, CC-09, CC-13, CC-24, CC-32; decisions
D2, D8). A standalone script outside the `algo_backtest` package (design.md: follows the
`experiments/heikin-ashi-signals/` layout).

**Population ledger** (`compute_population_ledger`, CC-24): for one (pair, clock, window)
it reconciles five counts — ``calendar_expanded_count`` (every UTC bar-length slot the
calendar contains), ``market_closure_count`` (slots inside the weekly FX closure, Friday
22:00 UTC through Sunday 22:00 UTC — an H4 bucket counts as closure if *any* of its four
constituent H1 hours is closed, the pinned reading of a bucket straddling the boundary),
``expected_valid_count`` (calendar minus closures), ``warmup_count`` (the declared
collection's own leading warmup bars) and ``missing_count`` (always 0 on a successful
call — a genuinely missing expected bar is a hard failure per D8/CC-24, never a soft
count). ``ready_count = expected_valid_count - warmup_count - missing_count``. File
presence or a `.done` marker establishes nothing; this ledger only ever reasons about
the counts a caller supplies (a real caller supplies them from actual row content).

**Arm ledger** (`compute_arm_ledger`, CC-13, CC-32, D9): M-only and both drift-control
arms never gate on news availability. A, B and T-only require an `AvailabilitySidecar`
proving every intensity observation's `available_at` precedes its decision timestamp; an
absent sidecar is an explicit `"unavailable"` status naming the reason, never a silently
dropped cell; a sidecar with a provenance violation is a hard failure, not a soft status.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

_TOOL = "preflight"
_CLOSURE_WEEKDAY_START, _CLOSURE_WEEKDAY_END = 4, 6  # Friday, Sunday (Python: Monday=0)
_CLOSURE_HOUR = 22
_NEWS_REQUIRED_ARMS = frozenset({"A", "B", "T-only"})
_NO_NEWS_ARMS = frozenset({"M-only", "always-short", "always-long"})
OK, UNAVAILABLE = "ok", "unavailable"


def _require_utc(value: datetime, *, what: str) -> None:
    """Fail fast on a naive or non-UTC datetime, naming which time it was."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{_TOOL}: {what} must be timezone-aware UTC, got {value!r}")


def _clock_label(clock_minutes: int) -> str:
    """A human label for a signal-bar clock: "H1" for 60, "H4" for 240, else minutes."""
    return {60: "H1", 240: "H4"}.get(clock_minutes, f"{clock_minutes}-minute")


def date_window(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    """`[start_date 00:00 UTC, end_date+1 day 00:00 UTC)`, both ISO `YYYY-MM-DD`, end inclusive."""
    start = datetime.combine(date.fromisoformat(start_date), datetime.min.time(), UTC)
    end = datetime.combine(date.fromisoformat(end_date), datetime.min.time(), UTC) + timedelta(
        days=1
    )
    return start, end


def _hour_closed(hour_start: datetime) -> bool:
    """Whether `[hour_start, hour_start + 1h)` falls in the weekly FX closure.

    Friday 22:00 UTC through Sunday 22:00 UTC — checking the hour's start suffices since
    the closure boundary aligns exactly to the hour grid.
    """
    weekday, hour = hour_start.weekday(), hour_start.hour
    if weekday == _CLOSURE_WEEKDAY_START:
        return hour >= _CLOSURE_HOUR
    if weekday == _CLOSURE_WEEKDAY_END:
        return hour < _CLOSURE_HOUR
    return _CLOSURE_WEEKDAY_START < weekday < _CLOSURE_WEEKDAY_END


def _slot_closed(slot_start: datetime, clock_minutes: int) -> bool:
    """Whether the slot counts as a documented closure: any constituent H1 hour closed."""
    hours = clock_minutes // 60
    return any(_hour_closed(slot_start + timedelta(hours=h)) for h in range(hours))


def _slots(window_start: datetime, window_end: datetime, clock_minutes: int) -> list[datetime]:
    """Every slot start on the clock grid in `[window_start, window_end)`."""
    step = timedelta(minutes=clock_minutes)
    slots = []
    slot = window_start
    while slot < window_end:
        slots.append(slot)
        slot += step
    return slots


def partition_path(pair: str, clock_minutes: int, month: str) -> str:
    """Where this pair's month lives in the real materialized data store, for display only.

    H1 and H4 both aggregate from the same materialized minute quotes — the lean-data
    store `algo_backtest.run.lean_data_covers` itself checks, and the same one
    `algo-backtest run`'s own CLI gates on (`cli.py`: `lean_data_dir_for(...).glob(
    "*_quote.zip")`) — so this does not depend on `clock_minutes` (kept in the
    signature so callers still name the clock they are checking; a diagnostic string
    only, `population_gate` calls `lean_data_covers` directly for the real check
    rather than reconstructing this path). `month` is ``YYYY-MM``.
    """
    del clock_minutes
    return f"lean-data/forex/oanda/minute/{pair.lower()}/{month}*_quote.zip"


def _group_contiguous(times: list[datetime], step: timedelta) -> list[list[datetime]]:
    """Sorted timestamps grouped into maximal runs of consecutive `step`-spaced values."""
    runs: list[list[datetime]] = []
    for t in times:
        if runs and t - runs[-1][-1] == step:
            runs[-1].append(t)
        else:
            runs.append([t])
    return runs


def _missing_message(missing: list[datetime], clock_minutes: int, window_start: datetime) -> str:
    """The hard-fail message for one or more missing expected bars (CC-24)."""
    label = _clock_label(clock_minutes)
    step = timedelta(minutes=clock_minutes)
    parts = []
    for run in _group_contiguous(sorted(missing), step):
        if len(run) == 1:
            parts.append(f"missing expected {label} bar at {run[0].isoformat()}")
        else:
            parts.append(
                f"missing expected {label} bars {run[0].isoformat()}..{run[-1].isoformat()} "
                f"({len(run)} bars)"
            )
    month = f"{window_start:%Y-%m}"
    summary = f"{len(missing)} missing expected bar(s) in {month}"
    return (
        f"{_TOOL}: " + "; ".join(parts) + f" — {summary} — backfill the source partition "
        "for that month"
    )


@dataclass(frozen=True)
class PopulationLedger:
    """The five reconciled counts for one (pair, clock, window); see module docstring."""

    pair: str
    clock_minutes: int
    window_start: datetime
    window_end: datetime
    calendar_expanded_count: int
    market_closure_count: int
    expected_valid_count: int
    warmup_count: int
    missing_count: int
    ready_count: int


def compute_population_ledger(
    *,
    pair: str,
    clock_minutes: int,
    window_start: datetime,
    window_end: datetime,
    warmup_bars: int = 0,
    missing_bars: Collection[datetime] = (),
    partition_exists: bool = True,
) -> PopulationLedger:
    """Reconcile one (pair, clock, window)'s population counts (CC-08, CC-09, CC-24).

    Raises:
        ValueError: the source partition is absent, or any expected bar is missing.
    """
    _require_utc(window_start, what="window_start")
    _require_utc(window_end, what="window_end")
    if not partition_exists:
        month = f"{window_start:%Y-%m}"
        raise ValueError(
            f"{_TOOL}: missing source partition for pair {pair!r} clock {clock_minutes} "
            f"month {month} — expected at {partition_path(pair, clock_minutes, month)} "
            "(relative to the data root) — "
            "materialize it by running the ingestion pipeline for that month before this "
            "preflight can pass"
        )
    if missing_bars:
        raise ValueError(_missing_message(list(missing_bars), clock_minutes, window_start))
    slots = _slots(window_start, window_end, clock_minutes)
    closures = sum(1 for slot in slots if _slot_closed(slot, clock_minutes))
    expected_valid = len(slots) - closures
    return PopulationLedger(
        pair=pair,
        clock_minutes=clock_minutes,
        window_start=window_start,
        window_end=window_end,
        calendar_expanded_count=len(slots),
        market_closure_count=closures,
        expected_valid_count=expected_valid,
        warmup_count=warmup_bars,
        missing_count=0,
        ready_count=expected_valid - warmup_bars,
    )


@dataclass(frozen=True)
class AvailabilityObservation:
    """One intensity observation's provenance: when it was decided on, when it was known."""

    decision_time: datetime
    available_at: datetime


@dataclass(frozen=True)
class AvailabilitySidecar:
    """The provenance proof for one (arm, window): every observation's availability."""

    observations: Sequence[AvailabilityObservation]


@dataclass(frozen=True)
class ArmLedger:
    """One arm's news-availability gate result for one window (CC-13, CC-32, D9)."""

    arm: str
    news_availability_required: bool
    status: str
    reason: str | None


def compute_arm_ledger(
    arm: str,
    *,
    clock_minutes: int,
    window_start: datetime,
    window_end: datetime,
    sidecar: AvailabilitySidecar | None = None,
) -> ArmLedger:
    """Whether `arm` needs news availability, and if so, whether it is proven (D9).

    Raises:
        ValueError: `arm` is unrecognized, or a present sidecar has an observation whose
            `available_at` is not strictly before its `decision_time`.
    """
    _require_utc(window_start, what="window_start")
    _require_utc(window_end, what="window_end")
    if arm not in _NEWS_REQUIRED_ARMS and arm not in _NO_NEWS_ARMS:
        raise ValueError(
            f"{_TOOL}: unknown arm {arm!r} — expected one of "
            f"{sorted(_NEWS_REQUIRED_ARMS | _NO_NEWS_ARMS)}"
        )
    if arm in _NO_NEWS_ARMS:
        return ArmLedger(arm=arm, news_availability_required=False, status=OK, reason=None)
    if sidecar is None:
        month = f"{window_start:%Y-%m}"
        return ArmLedger(
            arm=arm,
            news_availability_required=True,
            status=UNAVAILABLE,
            reason=f"no availability provenance sidecar for {month}",
        )
    for observation in sidecar.observations:
        if not observation.available_at < observation.decision_time:
            raise ValueError(
                f"{_TOOL}: available_at is not strictly before its decision timestamp "
                f"(decision {observation.decision_time.isoformat()}, available "
                f"{observation.available_at.isoformat()})"
            )
    return ArmLedger(arm=arm, news_availability_required=True, status=OK, reason=None)
