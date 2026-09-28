"""Steps for confluence_history.feature — frozen monthly intensity snapshots (story 21, T3).

Scenarios stage observations first (so a row can be removed or revised before the
archive is fed), then feed them into a real `IntensityHistory` the first time a snapshot
is computed or a direct `record` is attempted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from itertools import cycle
from typing import Any

import pytest
import yaml
from algo_backtest.chain.intensity_history import (
    CalibrationWindow,
    IntensityHistory,
    IntensityObservation,
    IntensitySnapshot,
    calibration_window,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_history.feature")

_SOURCE = "gdelt-h1-fixture"


@dataclass
class _Archive:
    """One history under construction: its clock, declared start, closures and rows."""

    clock_minutes: int
    started_at: datetime
    closures: list[tuple[datetime, datetime]] = field(default_factory=list)
    observations: list[IntensityObservation] = field(default_factory=list)
    history: IntensityHistory | None = None

    def materialized(self) -> IntensityHistory:
        """The real history, fed once from the staged closures and observations."""
        if self.history is None:
            self.history = IntensityHistory(
                clock_minutes=self.clock_minutes, collection_started_at=self.started_at
            )
            for start, end in self.closures:
                self.history.declare_closure(start, end)
            for observation in self.observations:
                self.history.record(observation)
        return self.history

    def replace(self, closed_at: datetime, **changes: Any) -> None:
        """Re-stage the observation closing at `closed_at` with `changes` applied."""
        index = next(i for i, o in enumerate(self.observations) if o.bar_closed_at == closed_at)
        current = self.observations[index]
        self.observations[index] = IntensityObservation(
            bar_closed_at=current.bar_closed_at,
            available_at=changes.get("available_at", current.available_at),
            intensity=changes.get("intensity", current.intensity),
            source_id=current.source_id,
        )


@dataclass
class _HistoryCtx:
    """Per-scenario context: one or two archives, the snapshots seen and any error."""

    archives: list[_Archive] = field(default_factory=list)
    window: CalibrationWindow | None = None
    snapshots: list[IntensitySnapshot] = field(default_factory=list)
    error: Exception | None = None


@pytest.fixture
def history_ctx() -> _HistoryCtx:
    """A fresh per-scenario history context."""
    return _HistoryCtx()


def _utc(raw: str) -> datetime:
    """An ISO timestamp (`Z` or offset) as an aware UTC datetime."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _observation(
    closed_at: datetime, intensity: float, available_at: datetime
) -> IntensityObservation:
    return IntensityObservation(
        bar_closed_at=closed_at,
        available_at=available_at,
        intensity=intensity,
        source_id=_SOURCE,
    )


def _first(history_ctx: _HistoryCtx) -> _Archive:
    """The scenario's (first) archive."""
    assert history_ctx.archives, "no intensity history staged"
    return history_ctx.archives[0]


def _latest(history_ctx: _HistoryCtx) -> IntensitySnapshot:
    """The most recently computed snapshot."""
    assert history_ctx.snapshots, "no snapshot computed"
    return history_ctx.snapshots[-1]


def _daily(archives: list[_Archive], first_day: str, docstring: str) -> None:
    """Daily 00:00 UTC closes from `first_day`, available at close, one value per token."""
    start = datetime.combine(date.fromisoformat(first_day), datetime.min.time(), UTC)
    for archive in archives:
        for index, token in enumerate(docstring.split()):
            closed = start + timedelta(days=index)
            archive.observations.append(_observation(closed, float(token), closed))


# --- Rule: the calibration window (D1) ---


@when(parsers.parse('the calibration window for decision time "{decision}" is derived'))
def _derive_window(history_ctx: _HistoryCtx, decision: str) -> None:
    history_ctx.window = calibration_window(_utc(decision))


@when(
    parsers.parse(
        'the calibration window for a naive decision time "{decision}" is derived and fails'
    )
)
def _derive_window_naive(history_ctx: _HistoryCtx, decision: str) -> None:
    naive = datetime.fromisoformat(decision)
    assert naive.tzinfo is None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        calibration_window(naive)
    history_ctx.error = exc_info.value


@then(parsers.parse('the calibration cutoff is "{expected}"'))
def _cutoff_is(history_ctx: _HistoryCtx, expected: str) -> None:
    assert history_ctx.window is not None
    assert history_ctx.window.cutoff.isoformat() == expected


@then(parsers.parse('the calibration window_start is "{expected}"'))
def _window_start_is(history_ctx: _HistoryCtx, expected: str) -> None:
    assert history_ctx.window is not None
    assert history_ctx.window.window_start.isoformat() == expected


# --- Staging archives ---


@given(
    parsers.parse(
        "an intensity history on a {clock:d}-minute clock with collection declared from {start}"
    )
)
def _one_history(history_ctx: _HistoryCtx, clock: int, start: str) -> None:
    history_ctx.archives = [_Archive(clock_minutes=clock, started_at=_utc(start))]


@given(
    parsers.parse(
        "two intensity histories on a {clock:d}-minute clock with collection declared from {start}"
    )
)
def _two_histories(history_ctx: _HistoryCtx, clock: int, start: str) -> None:
    history_ctx.archives = [_Archive(clock_minutes=clock, started_at=_utc(start)) for _ in range(2)]


@given(parsers.parse('a documented market closure from "{start}" to "{end}"'))
def _closure(history_ctx: _HistoryCtx, start: str, end: str) -> None:
    _first(history_ctx).closures.append((_utc(start), _utc(end)))


@given(
    parsers.parse(
        "daily observations closing at 00:00 UTC from {first_day} available at close, with "
        "intensities in time order:"
    )
)
def _daily_observations(history_ctx: _HistoryCtx, first_day: str, docstring: str) -> None:
    _daily([_first(history_ctx)], first_day, docstring)


@given(
    parsers.parse(
        "both are fed daily observations closing at 00:00 UTC from {first_day} available at "
        "close, with intensities in time order:"
    )
)
def _daily_observations_both(history_ctx: _HistoryCtx, first_day: str, docstring: str) -> None:
    _daily(history_ctx.archives, first_day, docstring)


@given(
    parsers.parse(
        "hourly observations closing every hour from {first} through {last} available at "
        "close, with intensities cycling through {values}"
    )
)
def _hourly_observations(history_ctx: _HistoryCtx, first: str, last: str, values: str) -> None:
    intensities = cycle(float(token) for token in values.split(","))
    closed, end = _utc(first), _utc(last)
    while closed <= end:
        _first(history_ctx).observations.append(_observation(closed, next(intensities), closed))
        closed += timedelta(hours=1)


@given("no observations")
def _no_observations(history_ctx: _HistoryCtx) -> None:
    assert not _first(history_ctx).observations


@given(parsers.parse('the observation closing at "{closed_at}" is removed'))
def _remove(history_ctx: _HistoryCtx, closed_at: str) -> None:
    archive = _first(history_ctx)
    before = len(archive.observations)
    archive.observations = [o for o in archive.observations if o.bar_closed_at != _utc(closed_at)]
    assert len(archive.observations) == before - 1


@given(parsers.parse('the observation closing at "{closed_at}" became available at "{available}"'))
def _revise_availability(history_ctx: _HistoryCtx, closed_at: str, available: str) -> None:
    _first(history_ctx).replace(_utc(closed_at), available_at=_utc(available))


@given(
    parsers.parse(
        'in the second the observation closing at "{closed_at}" has intensity {value:g} instead'
    )
)
def _revise_second(history_ctx: _HistoryCtx, closed_at: str, value: float) -> None:
    history_ctx.archives[1].replace(_utc(closed_at), intensity=value)


@given(
    parsers.parse(
        'only the second is fed an observation closing at "{closed_at}" with intensity '
        '{value:g} available at "{available}"'
    )
)
def _extra_second(history_ctx: _HistoryCtx, closed_at: str, value: float, available: str) -> None:
    history_ctx.archives[1].observations.append(
        _observation(_utc(closed_at), value, _utc(available))
    )


# --- Computing snapshots ---


@when(parsers.parse('the intensity snapshot for decision time "{decision}" is computed'))
def _compute(history_ctx: _HistoryCtx, decision: str) -> None:
    history_ctx.snapshots.append(_first(history_ctx).materialized().snapshot_for(_utc(decision)))


@when(parsers.parse('the intensity snapshot for decision time "{decision}" is computed on both'))
def _compute_both(history_ctx: _HistoryCtx, decision: str) -> None:
    for archive in history_ctx.archives:
        history_ctx.snapshots.append(archive.materialized().snapshot_for(_utc(decision)))


@when(parsers.parse('the intensity snapshot for decision time "{decision}" is computed and fails'))
def _compute_fails(history_ctx: _HistoryCtx, decision: str) -> None:
    history = _first(history_ctx).materialized()
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        history.snapshot_for(_utc(decision))
    history_ctx.error = exc_info.value


@when(
    parsers.parse(
        'a later observation closing at "{closed_at}" with intensity {value:g} available at '
        '"{available}" is recorded'
    )
)
def _record_later(history_ctx: _HistoryCtx, closed_at: str, value: float, available: str) -> None:
    _first(history_ctx).materialized().record(_observation(_utc(closed_at), value, _utc(available)))


@when(
    parsers.parse(
        'an observation closing at "{closed_at}" with intensity {value} available at '
        '"{available}" is recorded and fails'
    )
)
def _record_fails(history_ctx: _HistoryCtx, closed_at: str, value: str, available: str) -> None:
    """`value` may be `nan`/`inf`; the observation itself may already refuse to build."""
    history = _first(history_ctx).materialized()
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        history.record(_observation(_utc(closed_at), float(value), _utc(available)))
    history_ctx.error = exc_info.value


@when(
    parsers.parse(
        'an observation closing at "{closed_at}" with intensity {value:g} and no availability '
        "time is recorded and fails"
    )
)
def _record_no_availability(history_ctx: _HistoryCtx, closed_at: str, value: float) -> None:
    history = _first(history_ctx).materialized()
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        history.record(
            IntensityObservation(
                bar_closed_at=_utc(closed_at),
                available_at=None,  # type: ignore[arg-type]
                intensity=value,
                source_id=_SOURCE,
            )
        )
    history_ctx.error = exc_info.value


@when(
    parsers.parse(
        'an observation closing at "{closed_at}" with intensity {value:g} and an empty '
        "source_id is recorded and fails"
    )
)
def _record_no_source(history_ctx: _HistoryCtx, closed_at: str, value: float) -> None:
    history = _first(history_ctx).materialized()
    closed = _utc(closed_at)
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        history.record(
            IntensityObservation(
                bar_closed_at=closed, available_at=closed, intensity=value, source_id=""
            )
        )
    history_ctx.error = exc_info.value


# --- Assertions ---


def _expect_field(snapshot: IntensitySnapshot, name: str, raw: str) -> None:
    """Compare one snapshot field with a flow-YAML cell: datetimes by ISO string, floats
    approximately, everything else exactly (`null` is `None`)."""
    actual = getattr(snapshot, name)
    expected = yaml.safe_load(raw)
    if isinstance(actual, datetime):
        assert actual.isoformat() == expected, (name, actual, expected)
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected), (name, actual, expected)
    else:
        assert actual == expected, (name, actual, expected)


@then(parsers.parse("the snapshot {name:w} is {raw:S}"))
def _snapshot_field(history_ctx: _HistoryCtx, name: str, raw: str) -> None:
    _expect_field(_latest(history_ctx), name, raw)


@then("the two snapshots are equal")
def _snapshots_equal(history_ctx: _HistoryCtx) -> None:
    assert len(history_ctx.snapshots) >= 2
    assert history_ctx.snapshots[-2] == history_ctx.snapshots[-1]


@then("the two snapshots have the same source_hash")
def _same_hash(history_ctx: _HistoryCtx) -> None:
    assert history_ctx.snapshots[-2].source_hash == history_ctx.snapshots[-1].source_hash


@then("the two snapshots have different source_hash values")
def _different_hash(history_ctx: _HistoryCtx) -> None:
    assert history_ctx.snapshots[-2].source_hash != history_ctx.snapshots[-1].source_hash


@then(
    parsers.parse(
        'the {which:w} snapshot has cutoff "{cutoff}", q_low {q_low:g} and q_high {q_high:g}'
    )
)
def _nth_snapshot(
    history_ctx: _HistoryCtx, which: str, cutoff: str, q_low: float, q_high: float
) -> None:
    snapshot = history_ctx.snapshots[{"first": 0, "second": 1}[which]]
    assert snapshot.cutoff.isoformat() == cutoff
    assert snapshot.q_low == pytest.approx(q_low)
    assert snapshot.q_high == pytest.approx(q_high)


@then(parsers.parse("the {which:w} snapshot sample_count is {count:d}"))
def _nth_sample_count(history_ctx: _HistoryCtx, which: str, count: int) -> None:
    assert history_ctx.snapshots[{"first": 0, "second": 1}[which]].sample_count == count


@then(
    parsers.parse(
        'the intensity snapshot for decision time "{decision}" still has q_high {q_high:g}'
    )
)
def _still_has(history_ctx: _HistoryCtx, decision: str, q_high: float) -> None:
    snapshot = _first(history_ctx).materialized().snapshot_for(_utc(decision))
    assert snapshot.q_high == pytest.approx(q_high)


@then(parsers.parse("the history holds {count:d} observations"))
def _holds(history_ctx: _HistoryCtx, count: int) -> None:
    assert _first(history_ctx).materialized().observation_count == count


@then(parsers.parse('the last recorded bar close is "{expected}"'))
def _last_close(history_ctx: _HistoryCtx, expected: str) -> None:
    last = _first(history_ctx).materialized().last_closed_at
    assert last is not None and last.isoformat() == expected


@then(parsers.parse('the history failure names "{fragment}"'))
def _failure_names(history_ctx: _HistoryCtx, fragment: str) -> None:
    assert history_ctx.error is not None, "expected a failure but none was raised"
    assert fragment in str(history_ctx.error), str(history_ctx.error)


# --- Rule: provenance round-trips through plain values (CC-31) ---


@then(parsers.parse('the snapshot mapping has exactly the keys "{keys}"'))
def _mapping_keys(history_ctx: _HistoryCtx, keys: str) -> None:
    expected = [key.strip() for key in keys.split(",")]
    assert list(_latest(history_ctx).as_mapping()) == expected


@then("the snapshot mapping survives a JSON round trip")
def _mapping_json(history_ctx: _HistoryCtx) -> None:
    mapping = _latest(history_ctx).as_mapping()
    assert json.loads(json.dumps(mapping)) == mapping


@then("the snapshot mapping loads back as an equal snapshot")
def _mapping_loads_back(history_ctx: _HistoryCtx) -> None:
    snapshot = _latest(history_ctx)
    assert IntensitySnapshot.from_mapping(json.loads(json.dumps(snapshot.as_mapping()))) == snapshot


@then(parsers.parse('the snapshot mapping records cutoff "{cutoff}" as an ISO-8601 string'))
def _mapping_cutoff(history_ctx: _HistoryCtx, cutoff: str) -> None:
    assert _latest(history_ctx).as_mapping()["cutoff"] == cutoff


@then("the snapshot source_hash is a 64-character hexadecimal string")
def _hash_shape(history_ctx: _HistoryCtx) -> None:
    source_hash = _latest(history_ctx).source_hash
    assert len(source_hash) == 64
    assert set(source_hash) <= set("0123456789abcdef")
