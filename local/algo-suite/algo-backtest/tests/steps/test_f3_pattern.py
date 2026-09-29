"""Steps for f3_pattern.feature — the F3 candlestick pattern filter."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
import yaml
from algo_backtest.chain.filters.f3_pattern import (
    F3PatternFilter,
    PatternConfig,
    parse_pattern_config,
)
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f3_pattern.feature")


@dataclass
class _F3Ctx:
    """Per-scenario fixture context: the staged features plus the result or error seen."""

    features: dict[str, object] = field(default_factory=dict)
    result: FilterResult | None = None
    error: Exception | None = None
    section: dict[str, object] = field(default_factory=dict)
    config: PatternConfig | None = None


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
        f3_ctx.result = F3PatternFilter(config=PatternConfig()).apply(state)
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


@given(parsers.parse("a pattern section {section}"))
def _pattern_section(f3_ctx: _F3Ctx, section: str) -> None:
    """The raw YAML `pattern:` mapping, straight from the table (flow style)."""
    f3_ctx.section = yaml.safe_load(section)


@given(parsers.parse('a detected candlestick pattern "{pattern}"'))
def _detected(f3_ctx: _F3Ctx, pattern: str) -> None:
    f3_ctx.features["candlestick_pattern"] = pattern


@when(parsers.parse('the pattern config is parsed for strategy "{strategy}"'))
def _parse_pattern(f3_ctx: _F3Ctx, strategy: str) -> None:
    f3_ctx.config = parse_pattern_config(f3_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the pattern config for strategy "{strategy}" fails'))
def _parse_pattern_fails(f3_ctx: _F3Ctx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_pattern_config(f3_ctx.section, strategy=strategy)
    f3_ctx.error = exc_info.value


@when("F3 is applied with that pattern config")
def _apply_with_config(f3_ctx: _F3Ctx) -> None:
    config = parse_pattern_config(f3_ctx.section, strategy="scenario")
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f3_ctx.features)
    )
    f3_ctx.result = F3PatternFilter(config=config).apply(state)


def _names(raw: str) -> frozenset[str]:
    return frozenset(name.strip() for name in raw.split(","))


@then(parsers.parse('the parsed bullish patterns are "{names}"'))
def _bullish(f3_ctx: _F3Ctx, names: str) -> None:
    assert f3_ctx.config is not None
    assert f3_ctx.config.bullish_patterns == _names(names)


@then(parsers.parse('the parsed enabled_rules are "{names}"'))
def _enabled_rules(f3_ctx: _F3Ctx, names: str) -> None:
    assert f3_ctx.config is not None
    assert f3_ctx.config.enabled_rules == _names(names)


@then("the parsed enabled_rules are unset")
def _enabled_rules_unset(f3_ctx: _F3Ctx) -> None:
    assert f3_ctx.config is not None
    assert f3_ctx.config.enabled_rules is None


@then(parsers.parse('the parsed bearish patterns are "{names}"'))
def _bearish(f3_ctx: _F3Ctx, names: str) -> None:
    assert f3_ctx.config is not None
    assert f3_ctx.config.bearish_patterns == _names(names)


@then(parsers.parse('the pattern config failure names "{fragment}"'))
def _pattern_failure(f3_ctx: _F3Ctx, fragment: str) -> None:
    assert f3_ctx.error is not None
    assert fragment in str(f3_ctx.error)
