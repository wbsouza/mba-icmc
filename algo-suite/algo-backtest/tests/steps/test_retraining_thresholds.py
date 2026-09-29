"""Steps for retraining_thresholds.feature: separate-span threshold calibration."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from algo_backtest.chain.filters.f7_meta_learner import F7Config, F7MetaLearnerFilter
from algo_backtest.chain.model import ExecutionState
from algo_backtest.retraining.schedule import Span
from algo_backtest.retraining.thresholds import (
    ScoredRow,
    ThresholdResult,
    calibrate_thresholds,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/retraining_thresholds.feature")


@dataclass
class _StubMetaLearner:
    """A `TrainedMetaLearner`-shaped test double with a fixed p_hat."""

    p_hat: float

    def predict(self, features: dict[str, object]) -> float:
        return self.p_hat


@dataclass
class _ThresholdCtx:
    """Per-scenario state: the span, the scored rows, the result and any failure."""

    span: Span | None = None
    rows: list[ScoredRow] = field(default_factory=list)
    result: ThresholdResult | None = None
    error: Exception | None = None
    recommendation: str | None = None


@pytest.fixture
def th_ctx() -> _ThresholdCtx:
    return _ThresholdCtx()


def _iso(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _cells(datatable: list[list[str]]) -> list[dict[str, str]]:
    header, *rows = datatable
    return [dict(zip(header, row, strict=True)) for row in rows]


# --- Given ---------------------------------------------------------------------------------


@given(parsers.parse("the threshold span [{start}, {end})"))
def _span(th_ctx: _ThresholdCtx, start: str, end: str) -> None:
    th_ctx.span = Span(_iso(start), _iso(end))


@given("the scored rows in the span")
def _explicit_rows(th_ctx: _ThresholdCtx, datatable: list[list[str]]) -> None:
    for cell in _cells(datatable):
        th_ctx.rows.append(
            ScoredRow(
                key=cell["key"],
                available_at=_iso(cell["available_at"]),
                label_time=_iso(cell["label_time"]),
                score=float(cell["score"]),
            )
        )


@given("the extra scored rows")
def _extra_rows(th_ctx: _ThresholdCtx, datatable: list[list[str]]) -> None:
    for cell in _cells(datatable):
        th_ctx.rows.append(
            ScoredRow(
                key=cell["key"],
                available_at=_iso(cell["available_at"]),
                label_time=_iso(cell["label_time"]),
                score=float(cell["score"]),
            )
        )


@given(parsers.parse("the scored rows in the span with scores {scores}"))
def _rows_with_scores(th_ctx: _ThresholdCtx, scores: str) -> None:
    assert th_ctx.span is not None
    values = [float(part.strip()) for part in scores.split(",")]
    for i, value in enumerate(values):
        available_at = th_ctx.span.start + timedelta(hours=i)
        th_ctx.rows.append(
            ScoredRow(
                key=f"row-{i}",
                available_at=available_at,
                label_time=available_at + timedelta(minutes=30),
                score=value,
            )
        )


@given(
    parsers.parse(
        "{rows:d} scored rows in the span with evenly spread scores between {low:g} and {high:g}"
    )
)
def _evenly_spread_rows(th_ctx: _ThresholdCtx, rows: int, low: float, high: float) -> None:
    assert th_ctx.span is not None
    values = np.linspace(low, high, rows) if rows > 0 else []
    for i, value in enumerate(values):
        available_at = th_ctx.span.start + timedelta(hours=i)
        th_ctx.rows.append(
            ScoredRow(
                key=f"row-{i}",
                available_at=available_at,
                label_time=available_at + timedelta(minutes=30),
                score=float(value),
            )
        )


@given(parsers.parse("{rows:d} scored rows in the span all scoring {value:g}"))
def _all_same_score(th_ctx: _ThresholdCtx, rows: int, value: float) -> None:
    assert th_ctx.span is not None
    for i in range(rows):
        available_at = th_ctx.span.start + timedelta(hours=i)
        th_ctx.rows.append(
            ScoredRow(
                key=f"row-{i}",
                available_at=available_at,
                label_time=available_at + timedelta(minutes=30),
                score=value,
            )
        )


@given(parsers.parse("the thresholds are calibrated with a minimum of {minimum:d} rows"))
def _calibrate_with_minimum_given(th_ctx: _ThresholdCtx, minimum: int) -> None:
    assert th_ctx.span is not None
    th_ctx.result = calibrate_thresholds(th_ctx.rows, th_ctx.span, minimum_rows=minimum)


# --- When ------------------------------------------------------------------------------------


@when(parsers.parse("the thresholds are calibrated with a minimum of {minimum:d} rows"))
def _calibrate_with_minimum(th_ctx: _ThresholdCtx, minimum: int) -> None:
    assert th_ctx.span is not None
    th_ctx.result = calibrate_thresholds(th_ctx.rows, th_ctx.span, minimum_rows=minimum)


@when("the thresholds are calibrated with the registered minimum")
def _calibrate_with_registered(th_ctx: _ThresholdCtx) -> None:
    assert th_ctx.span is not None
    th_ctx.result = calibrate_thresholds(th_ctx.rows, th_ctx.span)


@when(
    parsers.re(
        r"^calibrating the thresholds(?: with (?:the registered minimum|a minimum of "
        r"(?P<minimum>\d+) rows))? fails$"
    )
)
def _calibrate_fails(th_ctx: _ThresholdCtx, minimum: str | None) -> None:
    assert th_ctx.span is not None
    kwargs = {} if minimum is None else {"minimum_rows": int(minimum)}
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        calibrate_thresholds(th_ctx.rows, th_ctx.span, **kwargs)
    th_ctx.error = exc_info.value


@when(
    parsers.parse(
        "a p_hat of {p_hat:g} is decided by F7 with the calibrated thresholds and the regime "
        "gate off"
    )
)
def _decide(th_ctx: _ThresholdCtx, p_hat: float) -> None:
    assert th_ctx.result is not None
    config = F7Config(
        theta_high=th_ctx.result.theta_high, theta_low=th_ctx.result.theta_low, regime_gate=False
    )
    filter_ = F7MetaLearnerFilter(
        meta_learner=_StubMetaLearner(p_hat),
        config=config,  # type: ignore[arg-type]
    )
    state = ExecutionState(
        timestamp=datetime(2016, 3, 1, tzinfo=UTC), pair="EURUSD", features={}, filter_results=[]
    )
    result = filter_.apply(state)
    th_ctx.recommendation = result.recommendation.name


# --- Then ----------------------------------------------------------------------------------


@then(parsers.parse("theta_low is {value:g}"))
def _theta_low(th_ctx: _ThresholdCtx, value: float) -> None:
    assert th_ctx.result is not None
    assert math.isclose(th_ctx.result.theta_low, value, rel_tol=1e-9, abs_tol=1e-12)


@then(parsers.parse("theta_high is {value:g}"))
def _theta_high(th_ctx: _ThresholdCtx, value: float) -> None:
    assert th_ctx.result is not None
    assert math.isclose(th_ctx.result.theta_high, value, rel_tol=1e-9, abs_tol=1e-12)


@then("theta_low is below theta_high")
def _theta_low_below_high(th_ctx: _ThresholdCtx) -> None:
    assert th_ctx.result is not None
    assert th_ctx.result.theta_low < th_ctx.result.theta_high


@then(parsers.parse("the calibration used {rows:d} rows"))
def _calibration_used(th_ctx: _ThresholdCtx, rows: int) -> None:
    assert th_ctx.result is not None
    assert th_ctx.result.rows == rows


@then(parsers.parse('the calibrated row keys do not include "{keys}"'))
def _keys_excluded(th_ctx: _ThresholdCtx, keys: str) -> None:
    assert th_ctx.result is not None
    excluded = {key.strip() for key in keys.split(",")}
    assert excluded.isdisjoint(th_ctx.result.row_keys)


@then(parsers.parse('the calibrated row keys include "{keys}"'))
def _keys_included(th_ctx: _ThresholdCtx, keys: str) -> None:
    assert th_ctx.result is not None
    included = {key.strip() for key in keys.split(",")}
    assert included.issubset(th_ctx.result.row_keys)


@then(parsers.parse("the calibration's span is [{start}, {end})"))
def _calibration_span(th_ctx: _ThresholdCtx, start: str, end: str) -> None:
    assert th_ctx.result is not None
    assert th_ctx.result.span == Span(_iso(start), _iso(end))


@then(parsers.parse('F7 recommends "{recommendation}"'))
def _recommends(th_ctx: _ThresholdCtx, recommendation: str) -> None:
    assert th_ctx.recommendation == recommendation


@then(parsers.parse('the threshold failure names "{fragment}"'))
def _failure_names(th_ctx: _ThresholdCtx, fragment: str) -> None:
    assert th_ctx.error is not None
    assert fragment in str(th_ctx.error)
