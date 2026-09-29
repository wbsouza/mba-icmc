"""Steps for confluence_capital_plan.feature — the optional F6 `exit_after_bars` horizon
(story 21, T5). Mirrors `test_f6_capital_mgmt.py`'s section / execution / account
staging so the time plan is proven through the same real `CapitalMgmtFilter`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters import f6_capital_mgmt
from algo_backtest.chain.filters.f6_capital_mgmt import (
    CapitalMgmtConfig,
    CapitalMgmtFilter,
    capital_mgmt_mapping,
    parse_capital_mgmt_config,
)
from algo_backtest.chain.model import ExecutionState, FilterResult
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_capital_plan.feature")

_SECTION_KEYS = (
    "risk_per_trade",
    "stop_loss_pips",
    "pip_value_per_lot",
    "lot_notional_units",
    "assumed_leverage",
)
_SECTION_DEFAULTS: dict[str, Any] = dict(
    zip(_SECTION_KEYS, (0.03, 20.0, 10.0, 100_000, 30), strict=True)
)
# The Examples cell that means "this market feature is absent from the bar".
_ABSENT = "-"


@dataclass
class _PlanCtx:
    """Per-scenario section + execution values + `state.features`, and F6's outcome."""

    section: dict[str, Any] = field(default_factory=dict)
    features: dict[str, Any] = field(default_factory=dict)
    spread_pips: float = 0.0
    broker_stop_level_pips: float = 0.0
    result: FilterResult | None = None
    error: Exception | None = None
    parsed_config: CapitalMgmtConfig | None = None
    parse_error: Exception | None = None


@pytest.fixture
def plan_ctx() -> _PlanCtx:
    """A fresh per-scenario F6 time-plan context."""
    return _PlanCtx()


# --- Staging ---


@given("a complete five-key capital_mgmt section")
def _five_key_section(plan_ctx: _PlanCtx) -> None:
    """The pre-story-12 section: the five sizing keys, no trade-plan key."""
    plan_ctx.section = dict(_SECTION_DEFAULTS)


@given(parsers.parse("the capital_mgmt section sets {key:w} to {value}"))
def _section_sets(plan_ctx: _PlanCtx, key: str, value: str) -> None:
    """Add or override one key; the cell is flow-style YAML (lists, mappings, null, bool)."""
    plan_ctx.section[key] = yaml.safe_load(value)


@given(
    parsers.parse(
        "account features: balance {balance:g}, pip value {pip_value:g}, "
        "margin per lot {margin_per_lot:g}, available margin {available_margin:g}"
    )
)
def _account_features(
    plan_ctx: _PlanCtx,
    balance: float,
    pip_value: float,
    margin_per_lot: float,
    available_margin: float,
) -> None:
    plan_ctx.features.update(
        account_balance=balance,
        pip_value=pip_value,
        margin_per_lot=margin_per_lot,
        available_margin=available_margin,
    )


@given(
    parsers.parse(
        "market features atr_pips {atr}, swing_low_pips {swing_low}, swing_high_pips {swing_high}"
    )
)
def _market_features(plan_ctx: _PlanCtx, atr: str, swing_low: str, swing_high: str) -> None:
    """The source-specific features; a `-` cell leaves that key out of the bar entirely."""
    for key, cell in (
        ("atr_pips", atr),
        ("swing_low_pips", swing_low),
        ("swing_high_pips", swing_high),
    ):
        if cell != _ABSENT:
            plan_ctx.features[key] = float(cell)


@given(
    parsers.parse(
        "an execution spread of {spread:g} pips and a broker stop level of {broker:g} pips"
    )
)
def _execution_values(plan_ctx: _PlanCtx, spread: float, broker: float) -> None:
    plan_ctx.spread_pips, plan_ctx.broker_stop_level_pips = spread, broker


# --- Parsing ---


@when(parsers.parse('the capital-mgmt config is parsed for strategy "{strategy}"'))
def _parse_config(plan_ctx: _PlanCtx, strategy: str) -> None:
    plan_ctx.parsed_config = parse_capital_mgmt_config(plan_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the capital-mgmt config for strategy "{strategy}" fails'))
def _parse_config_fails(plan_ctx: _PlanCtx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_capital_mgmt_config(plan_ctx.section, strategy=strategy)
    plan_ctx.parse_error = exc_info.value


def _config(plan_ctx: _PlanCtx) -> CapitalMgmtConfig:
    """The parsed config, which a When must have produced."""
    assert plan_ctx.parsed_config is not None
    return plan_ctx.parsed_config


def _mapping(plan_ctx: _PlanCtx) -> dict[str, Any]:
    """The effective values of the parsed config, as the loader writes them back."""
    return capital_mgmt_mapping(_config(plan_ctx))


@then(parsers.parse("the parsed capital-mgmt config has exit_after_bars {value}"))
def _parsed_exit(plan_ctx: _PlanCtx, value: str) -> None:
    assert _config(plan_ctx).exit_after_bars == yaml.safe_load(value)


@then(parsers.parse("the capital-mgmt mapping records {key:w} {value}"))
def _mapping_records(plan_ctx: _PlanCtx, key: str, value: str) -> None:
    assert _mapping(plan_ctx)[key] == yaml.safe_load(value)


@then(parsers.parse('the capital-mgmt mapping has no key "{key}"'))
def _mapping_lacks(plan_ctx: _PlanCtx, key: str) -> None:
    assert key not in _mapping(plan_ctx)


@then("parsing the capital-mgmt mapping again yields an equal config")
def _mapping_round_trips(plan_ctx: _PlanCtx) -> None:
    assert parse_capital_mgmt_config(_mapping(plan_ctx), strategy="rt") == _config(plan_ctx)


@then("the capital-mgmt mapping survives a YAML safe_dump round trip")
def _mapping_yaml_safe(plan_ctx: _PlanCtx) -> None:
    """`yaml.safe_dump` must not need python-specific tags (tuples), or safe_load breaks."""
    mapping = _mapping(plan_ctx)
    assert yaml.safe_load(yaml.safe_dump(mapping)) == mapping


@then(parsers.parse('the capital-mgmt config failure names "{fragment}"'))
def _parse_failure_names(plan_ctx: _PlanCtx, fragment: str) -> None:
    assert plan_ctx.parse_error is not None
    assert fragment in str(plan_ctx.parse_error), str(plan_ctx.parse_error)


@then(parsers.parse('the capital-mgmt config failure is exactly "{message}"'))
def _parse_failure_exactly(plan_ctx: _PlanCtx, message: str) -> None:
    """The whole remediation text, not just its leading fragment."""
    assert plan_ctx.parse_error is not None
    assert str(plan_ctx.parse_error) == message


# --- Applying ---


@when("F6 applies to the state")
def _apply(plan_ctx: _PlanCtx) -> None:
    """Parse the scenario's section (a failure there is a bug in the scenario, not F6),
    build the filter as wiring does, apply it to the bar."""
    config = parse_capital_mgmt_config(plan_ctx.section, strategy="scenario")
    state = ExecutionState(
        timestamp=datetime(2016, 4, 5, 10, tzinfo=UTC),
        pair="EURUSD",
        features=dict(plan_ctx.features),
    )
    capital_filter = CapitalMgmtFilter(
        config=config,
        spread_pips=plan_ctx.spread_pips,
        broker_stop_level_pips=plan_ctx.broker_stop_level_pips,
    )
    try:
        plan_ctx.result = capital_filter.apply(state)
    except (KeyError, ValueError) as exc:
        plan_ctx.error = exc


def _result(plan_ctx: _PlanCtx) -> FilterResult:
    """The applied result, failing loudly if F6 raised instead."""
    assert plan_ctx.error is None, f"unexpected error: {plan_ctx.error}"
    assert plan_ctx.result is not None
    return plan_ctx.result


def _plan(plan_ctx: _PlanCtx) -> dict[str, Any]:
    """The `trade_plan` enrichment."""
    plan = _result(plan_ctx).enrichment["trade_plan"]
    assert isinstance(plan, dict)
    return plan


def _side(plan_ctx: _PlanCtx, side: str) -> dict[str, Any]:
    """The plan's `long` / `short` sub-dict."""
    sub = _plan(plan_ctx)[side]
    assert isinstance(sub, dict)
    return sub


@then("F6's result does not veto")
def _no_veto(plan_ctx: _PlanCtx) -> None:
    assert _result(plan_ctx).veto is False, _result(plan_ctx).reason


@then("F6's result vetoes")
def _veto(plan_ctx: _PlanCtx) -> None:
    assert _result(plan_ctx).veto is True, _result(plan_ctx).reason


@then(parsers.parse('F6\'s trade plan has no key "{key}"'))
def _plan_lacks(plan_ctx: _PlanCtx, key: str) -> None:
    assert key not in _plan(plan_ctx)


@then(parsers.parse('F6\'s trade plan has exactly the keys "{keys}"'))
def _plan_keys(plan_ctx: _PlanCtx, keys: str) -> None:
    assert list(_plan(plan_ctx)) == [key.strip() for key in keys.split(",")]


@then(parsers.parse("F6's trade plan has {key:w} {expected:g}"))
def _plan_has(plan_ctx: _PlanCtx, key: str, expected: float) -> None:
    assert _plan(plan_ctx)[key] == pytest.approx(expected)


@then(parsers.parse("F6's {side:w} plan has stop_pips {expected:g}"))
def _side_stop(plan_ctx: _PlanCtx, side: str, expected: float) -> None:
    assert _side(plan_ctx, side)["stop_pips"] == pytest.approx(expected)


@then(parsers.parse("F6's {side:w} plan has reward_risk {expected:S}"))
def _side_reward_risk(plan_ctx: _PlanCtx, side: str, expected: str) -> None:
    """`null` = no target to measure against; otherwise a ratio compared approximately."""
    value = _side(plan_ctx, side)["reward_risk"]
    wanted = yaml.safe_load(expected)
    assert value == (pytest.approx(wanted) if wanted is not None else None)


@then(parsers.parse("F6's {side:w} plan has no targets and no trail_stops"))
def _side_no_targets(plan_ctx: _PlanCtx, side: str) -> None:
    assert _side(plan_ctx, side)["targets"] == []
    assert _side(plan_ctx, side)["trail_stops"] == []


@then(parsers.parse('F6\'s reason mentions "{fragment}"'))
def _reason_mentions(plan_ctx: _PlanCtx, fragment: str) -> None:
    assert fragment in _result(plan_ctx).reason, _result(plan_ctx).reason


# --- Rule: the accepted timing contract is recorded where the option is defined (D5) ---


@then(parsers.parse('the F6 module docstring mentions "{fragment}"'))
def _docstring_mentions(fragment: str) -> None:
    assert f6_capital_mgmt.__doc__ is not None
    assert fragment in f6_capital_mgmt.__doc__
