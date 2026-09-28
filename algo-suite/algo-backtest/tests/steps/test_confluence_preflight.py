"""Steps for confluence_preflight.feature — population and availability preflight
(story 21, T9).

`experiments/confluence-chain/preflight.py` is a standalone script outside the
`algo_backtest` package, loaded here by file path (same pattern as
`test_confluence_horizon_units.py`'s T8 steps). A single context serves both the
plain population-ledger scenarios (one or two staged clocks) and the per-arm
scenarios (mutually exclusive in practice — no scenario stages both).
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_preflight.feature")

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "experiments" / "confluence-chain" / "preflight.py"
)


def _load_script(path: Path) -> ModuleType:
    """Load a standalone script file as an importable module, by file path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pf = _load_script(_SCRIPT_PATH)
_CLOCK_LABELS = {"H1": 60, "H4": 240}


def _utc(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


@dataclass
class _StagedLedger:
    """One staged (pair, clock, window) population-ledger input."""

    pair: str
    clock_minutes: int
    window_start: datetime
    window_end: datetime
    warmup_bars: int = 0
    missing_bars: set[datetime] = field(default_factory=set)
    partition_exists: bool = True


@dataclass
class _StagedArm:
    """One staged (arm, clock, window) arm-ledger input."""

    arm: str
    clock_minutes: int
    window_start: datetime
    window_end: datetime
    sidecar: object = None


@dataclass
class _PreflightCtx:
    """Per-scenario context: staged population ledger(s) or one staged arm, plus results."""

    ledgers: dict[int, _StagedLedger] = field(default_factory=dict)
    arm: _StagedArm | None = None
    results: dict[int, object] = field(default_factory=dict)
    arm_result: object | None = None
    error: Exception | None = None


@pytest.fixture
def preflight_ctx() -> _PreflightCtx:
    """A fresh per-scenario preflight context."""
    return _PreflightCtx()


# --- Staging a population ledger ---


@given(
    parsers.parse(
        'a preflight ledger for pair "{pair}" clock {clock:d} minutes over "{start}".."{end}"'
    )
)
def _stage_population(
    preflight_ctx: _PreflightCtx, pair: str, clock: int, start: str, end: str
) -> None:
    window_start, window_end = pf.date_window(start, end)
    preflight_ctx.ledgers[clock] = _StagedLedger(
        pair=pair, clock_minutes=clock, window_start=window_start, window_end=window_end
    )


@given(
    parsers.parse(
        "the declared H1 collection begins {n:d} completed bars before the momentum window is ready"
    )
)
def _warmup_h1(preflight_ctx: _PreflightCtx, n: int) -> None:
    preflight_ctx.ledgers[60].warmup_bars = n


@given(
    parsers.parse(
        "the declared H4 collection begins {n:d} completed bars before the momentum window is ready"
    )
)
def _warmup_h4(preflight_ctx: _PreflightCtx, n: int) -> None:
    preflight_ctx.ledgers[240].warmup_bars = n


@given(parsers.parse('the source has no H1 bar at "{time}", an otherwise-open trading hour'))
def _missing_one(preflight_ctx: _PreflightCtx, time: str) -> None:
    preflight_ctx.ledgers[60].missing_bars.add(_utc(time))


@given(parsers.parse('the source has no H1 bars from "{first}" through "{last}"'))
def _missing_range(preflight_ctx: _PreflightCtx, first: str, last: str) -> None:
    t, end = _utc(first), _utc(last)
    while t <= end:
        preflight_ctx.ledgers[60].missing_bars.add(t)
        t += timedelta(hours=1)


@given("the source partition file exists, has a plausible size, and carries a .done marker")
def _plausible_file(preflight_ctx: _PreflightCtx) -> None:
    assert 60 in preflight_ctx.ledgers, "documents intent: no ledger field reads file presence"


@given(parsers.parse('the source partition for "{month}" does not exist'))
def _partition_absent(preflight_ctx: _PreflightCtx, month: str) -> None:
    del month
    preflight_ctx.ledgers[60].partition_exists = False


# --- Staging an arm ledger ---


@given(
    parsers.parse(
        'a preflight ledger for the "{arm}" arm on clock {clock:d} minutes over "{start}".."{end}"'
    )
)
def _stage_arm(preflight_ctx: _PreflightCtx, arm: str, clock: int, start: str, end: str) -> None:
    window_start, window_end = pf.date_window(start, end)
    preflight_ctx.arm = _StagedArm(
        arm=arm, clock_minutes=clock, window_start=window_start, window_end=window_end
    )


@given("no availability provenance sidecar exists for that window")
def _no_sidecar(preflight_ctx: _PreflightCtx) -> None:
    assert preflight_ctx.arm is not None
    preflight_ctx.arm.sidecar = None


@given(
    "an availability provenance sidecar for that window whose every observation's "
    "available_at precedes its decision timestamp"
)
def _valid_sidecar(preflight_ctx: _PreflightCtx) -> None:
    assert preflight_ctx.arm is not None
    decision = preflight_ctx.arm.window_start + timedelta(hours=1)
    preflight_ctx.arm.sidecar = pf.AvailabilitySidecar(
        observations=[
            pf.AvailabilityObservation(
                decision_time=decision, available_at=decision - timedelta(minutes=5)
            )
        ]
    )


@given(
    "an availability provenance sidecar for that window with one observation whose "
    "available_at is after its decision timestamp"
)
def _invalid_sidecar(preflight_ctx: _PreflightCtx) -> None:
    assert preflight_ctx.arm is not None
    decision = preflight_ctx.arm.window_start + timedelta(hours=1)
    preflight_ctx.arm.sidecar = pf.AvailabilitySidecar(
        observations=[
            pf.AvailabilityObservation(
                decision_time=decision, available_at=decision + timedelta(minutes=5)
            )
        ]
    )


# --- Running ---


def _compute_one(preflight_ctx: _PreflightCtx) -> None:
    if preflight_ctx.arm is not None:
        arm = preflight_ctx.arm
        preflight_ctx.arm_result = pf.compute_arm_ledger(
            arm.arm,
            clock_minutes=arm.clock_minutes,
            window_start=arm.window_start,
            window_end=arm.window_end,
            sidecar=arm.sidecar,
        )
        return
    ((clock, staged),) = preflight_ctx.ledgers.items()
    preflight_ctx.results[clock] = pf.compute_population_ledger(
        pair=staged.pair,
        clock_minutes=staged.clock_minutes,
        window_start=staged.window_start,
        window_end=staged.window_end,
        warmup_bars=staged.warmup_bars,
        missing_bars=staged.missing_bars,
        partition_exists=staged.partition_exists,
    )


@when("the population ledger is computed")
def _compute(preflight_ctx: _PreflightCtx) -> None:
    _compute_one(preflight_ctx)


@when("the population ledger is computed for both clocks")
def _compute_both(preflight_ctx: _PreflightCtx) -> None:
    for clock, staged in preflight_ctx.ledgers.items():
        preflight_ctx.results[clock] = pf.compute_population_ledger(
            pair=staged.pair,
            clock_minutes=staged.clock_minutes,
            window_start=staged.window_start,
            window_end=staged.window_end,
            warmup_bars=staged.warmup_bars,
            missing_bars=staged.missing_bars,
            partition_exists=staged.partition_exists,
        )


@when("the population ledger is computed and fails")
def _compute_fails(preflight_ctx: _PreflightCtx) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _compute_one(preflight_ctx)
    preflight_ctx.error = exc_info.value


# --- Assertions: population ledger ---


@then(parsers.parse("the ledger's {field:w} is {value:d}"))
def _field_eq(preflight_ctx: _PreflightCtx, field: str, value: int) -> None:
    (result,) = preflight_ctx.results.values()
    assert getattr(result, field) == value


@then(parsers.parse("the {label:w} ledger's {field:w} is {value:d}"))
def _field_eq_labeled(preflight_ctx: _PreflightCtx, label: str, field: str, value: int) -> None:
    result = preflight_ctx.results[_CLOCK_LABELS[label]]
    assert getattr(result, field) == value


@then("the ledger's calendar_expanded_count equals market_closure_count plus expected_valid_count")
def _reconcile_calendar(preflight_ctx: _PreflightCtx) -> None:
    (result,) = preflight_ctx.results.values()
    assert (
        result.calendar_expanded_count == result.market_closure_count + result.expected_valid_count
    )


@then("the ledger's expected_valid_count equals warmup_count plus missing_count plus ready_count")
def _reconcile_valid(preflight_ctx: _PreflightCtx) -> None:
    (result,) = preflight_ctx.results.values()
    assert (
        result.expected_valid_count
        == result.warmup_count + result.missing_count + result.ready_count
    )


@then(
    "the H4 ledger's expected_valid_count times 4 does not exceed the H1 ledger's "
    "expected_valid_count"
)
def _h4_times4(preflight_ctx: _PreflightCtx) -> None:
    assert (
        preflight_ctx.results[240].expected_valid_count * 4
        <= preflight_ctx.results[60].expected_valid_count
    )


@then("the ledger status is not a failure")
def _not_failure(preflight_ctx: _PreflightCtx) -> None:
    assert preflight_ctx.error is None


@then("the ledger's warmup_count is disjoint from its missing_count")
def _disjoint(preflight_ctx: _PreflightCtx) -> None:
    (result,) = preflight_ctx.results.values()
    assert result.warmup_count > 0
    assert result.missing_count == 0


@then(parsers.parse('the preflight failure names "{fragment}"'))
def _failure_names(preflight_ctx: _PreflightCtx, fragment: str) -> None:
    assert preflight_ctx.error is not None, "expected a failure but none was raised"
    assert fragment in str(preflight_ctx.error), str(preflight_ctx.error)


@then("the preflight failure names the exact missing partition path")
def _names_path(preflight_ctx: _PreflightCtx) -> None:
    (staged,) = preflight_ctx.ledgers.values()
    month = f"{staged.window_start:%Y-%m}"
    expected_path = pf.partition_path(staged.pair, staged.clock_minutes, month)
    assert preflight_ctx.error is not None
    assert expected_path in str(preflight_ctx.error)


@then("the preflight failure names how to materialize it")
def _names_remediation(preflight_ctx: _PreflightCtx) -> None:
    assert preflight_ctx.error is not None
    assert "materialize" in str(preflight_ctx.error)


# --- Assertions: arm ledger ---


@then(parsers.parse("the ledger's news_availability_required is {value}"))
def _news_required(preflight_ctx: _PreflightCtx, value: str) -> None:
    assert preflight_ctx.arm_result is not None
    assert preflight_ctx.arm_result.news_availability_required == (value == "true")


@then(parsers.parse('the ledger\'s status for "{arm}" is "{status}"'))
def _arm_status(preflight_ctx: _PreflightCtx, arm: str, status: str) -> None:
    assert preflight_ctx.arm_result is not None
    assert preflight_ctx.arm_result.arm == arm
    assert preflight_ctx.arm_result.status == status


@then(parsers.parse('the ledger names the reason "{reason}"'))
def _arm_reason(preflight_ctx: _PreflightCtx, reason: str) -> None:
    assert preflight_ctx.arm_result is not None
    assert preflight_ctx.arm_result.reason == reason


@then(parsers.parse('the "{arm}" cell is still listed in the ledger, not dropped'))
def _arm_listed(preflight_ctx: _PreflightCtx, arm: str) -> None:
    assert preflight_ctx.arm_result is not None
    assert preflight_ctx.arm_result.arm == arm


@then(parsers.parse('the ledger\'s status for "{arm}" is not "{status}"'))
def _arm_status_not(preflight_ctx: _PreflightCtx, arm: str, status: str) -> None:
    assert preflight_ctx.arm_result is not None
    assert preflight_ctx.arm_result.arm == arm
    assert preflight_ctx.arm_result.status != status
