"""Steps for f2_indicator.feature — the F2 indicator (oscillator confirmation) filter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
import yaml
from algo_backtest.chain.filters.f2_indicator import (
    F2IndicatorFilter,
    IndicatorConfig,
    parse_indicator_config,
)
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f2_indicator.feature")


@dataclass
class _F2Ctx:
    """Per-scenario fixture context: the staged features plus the result or error seen."""

    features: dict[str, object] = field(default_factory=dict)
    result: FilterResult | None = None
    error: Exception | None = None


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
    """Run `F2IndicatorFilter.apply()` against the staged features, capturing any error."""
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f2_ctx.features)
    )
    try:
        f2_ctx.result = F2IndicatorFilter(config=IndicatorConfig()).apply(state)
    except ValueError as exc:
        f2_ctx.error = exc


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


@then(parsers.parse('F2 raises an error naming "{name}"'))
def _raises_naming(f2_ctx: _F2Ctx, name: str) -> None:
    """Application raised, and the message names the out-of-range parameter."""
    assert isinstance(f2_ctx.error, ValueError)
    assert name in str(f2_ctx.error)


@given(parsers.parse("an indicator section {section}"))
def _indicator_section(f2_ctx: _F2Ctx, section: str) -> None:
    """The raw YAML `indicator:` mapping, straight from the table (flow style)."""
    f2_ctx.section = yaml.safe_load(section)


@when(parsers.parse('the indicator config is parsed for strategy "{strategy}"'))
def _parse_indicator(f2_ctx: _F2Ctx, strategy: str) -> None:
    f2_ctx.config = parse_indicator_config(f2_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the indicator config for strategy "{strategy}" fails'))
def _parse_indicator_fails(f2_ctx: _F2Ctx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_indicator_config(f2_ctx.section, strategy=strategy)
    f2_ctx.error = exc_info.value


@when("F2 is applied with that indicator config")
def _apply_with_config(f2_ctx: _F2Ctx) -> None:
    config = parse_indicator_config(f2_ctx.section, strategy="scenario")
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f2_ctx.features)
    )
    f2_ctx.result = F2IndicatorFilter(config=config).apply(state)


@then(
    parsers.parse(
        "the parsed indicator config has rsi_midline {midline:g} and macd_hist_threshold "
        "{threshold:g}"
    )
)
def _parsed_indicator(f2_ctx: _F2Ctx, midline: float, threshold: float) -> None:
    assert f2_ctx.config == IndicatorConfig(rsi_midline=midline, macd_hist_threshold=threshold)


@then(parsers.parse('the indicator config failure names "{fragment}"'))
def _indicator_failure(f2_ctx: _F2Ctx, fragment: str) -> None:
    assert f2_ctx.error is not None
    assert fragment in str(f2_ctx.error)
