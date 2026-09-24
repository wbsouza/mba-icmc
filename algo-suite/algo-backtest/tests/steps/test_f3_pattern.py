"""Steps for f3_pattern.feature — the F3 candlestick pattern filter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from algo_backtest.chain.filters.f3_pattern import F3PatternFilter
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f3_pattern.feature")


@dataclass
class _F3Ctx:
    """Per-scenario fixture context: the staged features plus the result or error seen."""

    features: dict[str, object] = field(default_factory=dict)
    result: FilterResult | None = None
    error: Exception | None = None


@pytest.fixture
def f3_ctx() -> _F3Ctx:
    """A fresh per-scenario F3 context."""
    return _F3Ctx()


@given("no candlestick pattern is present")
def _no_pattern(f3_ctx: _F3Ctx) -> None:
    """Stage a state with no `candlestick_pattern` key at all."""
    f3_ctx.features = {}


@given(parsers.parse('candlestick pattern "{pattern}"'))
def _pattern(f3_ctx: _F3Ctx, pattern: str) -> None:
    """Stage a state with the named `candlestick_pattern` value."""
    f3_ctx.features = {"candlestick_pattern": pattern}


@when("F3 is applied")
def _apply_f3(f3_ctx: _F3Ctx) -> None:
    """Run `F3PatternFilter.apply()` against the staged features, capturing any error."""
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f3_ctx.features)
    )
    try:
        f3_ctx.result = F3PatternFilter().apply(state)
    except ValueError as exc:
        f3_ctx.error = exc


@then(parsers.parse('F3 abstains with reason mentioning "{fragment}"'))
def _abstains_with_reason(f3_ctx: _F3Ctx, fragment: str) -> None:
    """The result recommends ABSTAIN, carries no veto, and names the fragment."""
    assert f3_ctx.result is not None
    assert f3_ctx.result.recommendation == Recommendation.ABSTAIN
    assert f3_ctx.result.veto is False
    assert fragment in f3_ctx.result.reason


@then(parsers.parse('F3 recommends "{recommendation}" with reason mentioning "{fragment}"'))
def _recommends_with_reason(f3_ctx: _F3Ctx, recommendation: str, fragment: str) -> None:
    """The result carries the given recommendation, no veto, and names the fragment."""
    assert f3_ctx.result is not None
    assert f3_ctx.result.recommendation == Recommendation(recommendation)
    assert f3_ctx.result.veto is False
    assert fragment in f3_ctx.result.reason


@then(parsers.parse('F3\'s filter_name is "{name}"'))
def _filter_name_is(f3_ctx: _F3Ctx, name: str) -> None:
    """The result's `filter_name` matches exactly."""
    assert f3_ctx.result is not None
    assert f3_ctx.result.filter_name == name


@then(parsers.parse('F3 raises an error naming "{name}"'))
def _raises_naming(f3_ctx: _F3Ctx, name: str) -> None:
    """Construction/application raised, and the message names the unrecognized pattern."""
    assert isinstance(f3_ctx.error, ValueError)
    assert name in str(f3_ctx.error)
