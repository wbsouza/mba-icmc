"""Steps for f2_indicator.feature — the F2 indicator (oscillator confirmation) filter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from algo_backtest.chain.filters.f2_indicator import F2IndicatorFilter
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f2_indicator.feature")


@dataclass
class _F2Ctx:
    """Per-scenario fixture context: the staged features plus the result seen."""

    features: dict[str, object] = field(default_factory=dict)
    result: FilterResult | None = None


@pytest.fixture
def f2_ctx() -> _F2Ctx:
    """A fresh per-scenario F2 context."""
    return _F2Ctx()


@given(parsers.parse("rsi is absent and macd_hist {macd_hist:g}"))
def _rsi_absent(f2_ctx: _F2Ctx, macd_hist: float) -> None:
    """Stage a state with no `rsi` key at all."""
    f2_ctx.features = {"macd_hist": macd_hist}


@given(parsers.parse("rsi {rsi:g} and macd_hist is absent"))
def _macd_absent(f2_ctx: _F2Ctx, rsi: float) -> None:
    """Stage a state with no `macd_hist` key at all."""
    f2_ctx.features = {"rsi": rsi}


@given(parsers.parse("rsi {rsi:g} and macd_hist {macd_hist:g}"))
def _both_present(f2_ctx: _F2Ctx, rsi: float, macd_hist: float) -> None:
    """Stage both oscillator readings."""
    f2_ctx.features = {"rsi": rsi, "macd_hist": macd_hist}


@when("F2 is applied")
def _apply_f2(f2_ctx: _F2Ctx) -> None:
    """Run `F2IndicatorFilter.apply()` against the staged features."""
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f2_ctx.features)
    )
    f2_ctx.result = F2IndicatorFilter().apply(state)


@then(parsers.parse('F2 abstains with reason mentioning "{fragment}"'))
def _abstains_with_reason(f2_ctx: _F2Ctx, fragment: str) -> None:
    """The result recommends ABSTAIN, carries no veto, and names the fragment."""
    assert f2_ctx.result is not None
    assert f2_ctx.result.recommendation == Recommendation.ABSTAIN
    assert f2_ctx.result.veto is False
    assert fragment in f2_ctx.result.reason


@then(parsers.parse('F2 recommends "{recommendation}"'))
def _recommends(f2_ctx: _F2Ctx, recommendation: str) -> None:
    """The result carries the given recommendation and no veto."""
    assert f2_ctx.result is not None
    assert f2_ctx.result.recommendation == Recommendation(recommendation)
    assert f2_ctx.result.veto is False


@then(parsers.parse('F2\'s filter_name is "{name}"'))
def _filter_name_is(f2_ctx: _F2Ctx, name: str) -> None:
    """The result's `filter_name` matches exactly."""
    assert f2_ctx.result is not None
    assert f2_ctx.result.filter_name == name


@then("F2's reason is non-empty")
def _reason_non_empty(f2_ctx: _F2Ctx) -> None:
    """The result carries a non-empty reason string."""
    assert f2_ctx.result is not None
    assert f2_ctx.result.reason
