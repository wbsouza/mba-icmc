"""Steps for f1_trend.feature — the F1 trend-regime filter.

Follows the fixture-per-scenario context + parsers.parse pattern established in
`test_filter_chain_mechanics.py` (Spec 04b).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from algo_backtest.chain.filters.f1_trend import F1TrendFilter
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f1_trend.feature")


@dataclass
class _F1Ctx:
    """Per-scenario fixture context: the state under test plus the result or error seen."""

    features: dict[str, object] = field(default_factory=dict)
    result: FilterResult | None = None
    error: Exception | None = None


@pytest.fixture
def f1_ctx() -> _F1Ctx:
    """A fresh per-scenario F1 context."""
    return _F1Ctx()


@given(
    parsers.parse(
        "trend_direction {trend_direction:g}, trend_strength {trend_strength:g} "
        "and higher_tf_trend_direction {higher_tf_trend_direction:g}"
    )
)
def _given_trend_features(
    f1_ctx: _F1Ctx,
    trend_direction: float,
    trend_strength: float,
    higher_tf_trend_direction: float,
) -> None:
    """Stage the three F1 feature keys on the context's feature dict."""
    f1_ctx.features = {
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
        "higher_tf_trend_direction": higher_tf_trend_direction,
    }


@given(parsers.parse('a state missing "{key}"'))
def _given_missing_key(f1_ctx: _F1Ctx, key: str) -> None:
    """Stage a feature dict that omits the named required key."""
    f1_ctx.features = {
        "trend_direction": 0.5,
        "trend_strength": 20.0,
        "higher_tf_trend_direction": 0.5,
    }
    del f1_ctx.features[key]


@when("F1 is applied")
def _apply_f1(f1_ctx: _F1Ctx) -> None:
    """Run `F1TrendFilter.apply()` against the staged features, capturing any error."""
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f1_ctx.features)
    )
    try:
        f1_ctx.result = F1TrendFilter().apply(state)
    except ValueError as exc:
        f1_ctx.error = exc


@then(parsers.parse('F1 vetoes with reason mentioning "{fragment}"'))
def _vetoes_with_reason(f1_ctx: _F1Ctx, fragment: str) -> None:
    """The result is a veto whose reason mentions the given fragment."""
    assert f1_ctx.result is not None
    assert f1_ctx.result.veto is True
    assert fragment in f1_ctx.result.reason


@then(parsers.parse('F1 recommends "{recommendation}" with no veto'))
def _recommends_with_no_veto(f1_ctx: _F1Ctx, recommendation: str) -> None:
    """The result carries the given recommendation and no veto."""
    assert f1_ctx.result is not None
    assert f1_ctx.result.recommendation == Recommendation(recommendation)
    assert f1_ctx.result.veto is False


@then(parsers.parse('F1 recommends "{recommendation}" with veto'))
def _recommends_with_veto(f1_ctx: _F1Ctx, recommendation: str) -> None:
    """The result carries the given recommendation and is a veto."""
    assert f1_ctx.result is not None
    assert f1_ctx.result.recommendation == Recommendation(recommendation)
    assert f1_ctx.result.veto is True


@then(parsers.parse('F1\'s filter_name is "{name}"'))
def _filter_name_is(f1_ctx: _F1Ctx, name: str) -> None:
    """The result's `filter_name` matches exactly."""
    assert f1_ctx.result is not None
    assert f1_ctx.result.filter_name == name


@then("F1's reason is non-empty")
def _reason_non_empty(f1_ctx: _F1Ctx) -> None:
    """The result carries a non-empty reason string."""
    assert f1_ctx.result is not None
    assert f1_ctx.result.reason


@then(parsers.parse('F1 enriches "{key}" with value {value:g}'))
def _enriches_with_value(f1_ctx: _F1Ctx, key: str, value: float) -> None:
    """The result's enrichment carries the given key at the given value (approx)."""
    assert f1_ctx.result is not None
    assert key in f1_ctx.result.enrichment
    assert f1_ctx.result.enrichment[key] == pytest.approx(value)


@then(parsers.parse('F1 raises an error naming "{name}"'))
def _raises_naming(f1_ctx: _F1Ctx, name: str) -> None:
    """Construction/application raised, and the message names the missing key."""
    assert isinstance(f1_ctx.error, ValueError)
    assert name in str(f1_ctx.error)
