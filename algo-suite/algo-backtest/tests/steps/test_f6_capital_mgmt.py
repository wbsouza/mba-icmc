"""Steps for f6_capital_mgmt.feature — the F6 trade plan from a `capital_mgmt` section, an
`execution` spread / broker stop level and the bar's account + market features."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.f6_capital_mgmt import (
    CapitalMgmtConfig,
    CapitalMgmtFilter,
    capital_mgmt_mapping,
    parse_capital_mgmt_config,
)
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f6_capital_mgmt.feature")

_ACCOUNT_FEATURES = {
    "account_balance": 10000.0,
    "pip_value": 1.0,
    "margin_per_lot": 100.0,
    "available_margin": 2000.0,
}
# The Examples cell that means "this market feature is absent from the bar".
_ABSENT = "-"


@dataclass
class _F6Ctx:
    """Per-scenario section + execution values + `state.features`, and F6's outcome."""

    features: dict[str, Any] = field(default_factory=dict)
    spread_pips: float = 0.0
    broker_stop_level_pips: float = 0.0
    result: FilterResult | None = None
    error: Exception | None = None
    section: dict[str, Any] = field(default_factory=dict)
    parsed_config: CapitalMgmtConfig | None = None
    parse_error: Exception | None = None


@pytest.fixture
def f6_ctx() -> _F6Ctx:
    return _F6Ctx()


@given(
    parsers.parse(
        "account features: balance {balance:g}, pip value {pip_value:g}, "
        "margin per lot {margin_per_lot:g}, available margin {available_margin:g}"
    )
)
def _account_features(
    f6_ctx: _F6Ctx,
    balance: float,
    pip_value: float,
    margin_per_lot: float,
    available_margin: float,
) -> None:
    f6_ctx.features.update(
        account_balance=balance, pip_value=pip_value, margin_per_lot=margin_per_lot,
        available_margin=available_margin,
    )


@given(parsers.parse('account features missing "{missing_key}"'))
def _account_features_missing(f6_ctx: _F6Ctx, missing_key: str) -> None:
    f6_ctx.features.update({k: v for k, v in _ACCOUNT_FEATURES.items() if k != missing_key})


@given(
    parsers.parse(
        "market features atr_pips {atr}, swing_low_pips {swing_low}, swing_high_pips {swing_high}"
    )
)
def _market_features(f6_ctx: _F6Ctx, atr: str, swing_low: str, swing_high: str) -> None:
    """The source-specific features; a `-` cell leaves that key out of the bar entirely."""
    for key, cell in (
        ("atr_pips", atr), ("swing_low_pips", swing_low), ("swing_high_pips", swing_high)
    ):
        if cell != _ABSENT:
            f6_ctx.features[key] = float(cell)


@given(
    parsers.parse(
        "an execution spread of {spread:g} pips and a broker stop level of {broker:g} pips"
    )
)
def _execution_values(f6_ctx: _F6Ctx, spread: float, broker: float) -> None:
    f6_ctx.spread_pips, f6_ctx.broker_stop_level_pips = spread, broker


@when("F6 applies to the state")
def _apply(f6_ctx: _F6Ctx) -> None:
    """Parse the scenario's section (fail fast there is a bug in the scenario, not F6),
    build the filter as wiring does, apply it to the bar."""
    config = parse_capital_mgmt_config(f6_ctx.section, strategy="scenario")
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f6_ctx.features)
    )
    capital_filter = CapitalMgmtFilter(
        config=config, spread_pips=f6_ctx.spread_pips,
        broker_stop_level_pips=f6_ctx.broker_stop_level_pips,
    )
    try:
        f6_ctx.result = capital_filter.apply(state)
    except (KeyError, ValueError) as exc:
        f6_ctx.error = exc


def _result(f6_ctx: _F6Ctx) -> FilterResult:
    """The applied result, failing loudly if F6 raised instead."""
    assert f6_ctx.error is None, f"unexpected error: {f6_ctx.error}"
    assert f6_ctx.result is not None
    return f6_ctx.result


def _plan(f6_ctx: _F6Ctx) -> dict[str, Any]:
    """The `trade_plan` enrichment."""
    plan = _result(f6_ctx).enrichment["trade_plan"]
    assert isinstance(plan, dict)
    return plan


def _side(f6_ctx: _F6Ctx, side: str) -> dict[str, Any]:
    """The plan's `long` / `short` sub-dict."""
    sub = _plan(f6_ctx)[side]
    assert isinstance(sub, dict)
    return sub


@then("F6's result does not veto")
def _no_veto(f6_ctx: _F6Ctx) -> None:
    assert _result(f6_ctx).veto is False, _result(f6_ctx).reason


@then("F6's result vetoes")
def _veto(f6_ctx: _F6Ctx) -> None:
    assert _result(f6_ctx).veto is True


@then(parsers.parse("F6's veto flag is {flag}"))
def _veto_flag(f6_ctx: _F6Ctx, flag: str) -> None:
    assert _result(f6_ctx).veto is yaml.safe_load(flag), _result(f6_ctx).reason


@then(parsers.parse('F6 enriches "{key}" with {expected:g}'))
def _enriches(f6_ctx: _F6Ctx, key: str, expected: float) -> None:
    assert _result(f6_ctx).enrichment[key] == pytest.approx(expected)


@then(parsers.parse("F6's trade plan has {key} {expected:g}"))
def _plan_has(f6_ctx: _F6Ctx, key: str, expected: float) -> None:
    assert _plan(f6_ctx)[key] == pytest.approx(expected)


@then(parsers.parse("F6's {side} plan has stop_pips {expected:g}"))
def _side_stop(f6_ctx: _F6Ctx, side: str, expected: float) -> None:
    assert _side(f6_ctx, side)["stop_pips"] == pytest.approx(expected)


@then(parsers.parse("F6's {side} plan has reward_risk {expected}"))
def _side_reward_risk(f6_ctx: _F6Ctx, side: str, expected: str) -> None:
    """`null` = no target to measure against; otherwise a ratio compared approximately."""
    value = _side(f6_ctx, side)["reward_risk"]
    wanted = yaml.safe_load(expected)
    assert value == (pytest.approx(wanted) if wanted is not None else None)


@then(
    parsers.parse(
        "F6's {side} plan target {index:d} is {pips:g} pips closing {fraction:g} of the position"
    )
)
def _side_target(f6_ctx: _F6Ctx, side: str, index: int, pips: float, fraction: float) -> None:
    target = _side(f6_ctx, side)["targets"][index - 1]
    assert target == {"pips": pytest.approx(pips), "close_fraction": pytest.approx(fraction)}


@then(
    parsers.parse(
        "F6's {side} plan trail {index:d} arms at {at_pips:g} pips and moves the stop to "
        "{to_pips:g} pips"
    )
)
def _side_trail(f6_ctx: _F6Ctx, side: str, index: int, at_pips: float, to_pips: float) -> None:
    step = _side(f6_ctx, side)["trail_stops"][index - 1]
    assert step == {"at_pips": pytest.approx(at_pips), "to_pips": pytest.approx(to_pips)}


@then("F6's trade plan is JSON-serialisable")
def _plan_json_safe(f6_ctx: _F6Ctx) -> None:
    """The executor and the decisions audit trail carry the plan as plain JSON."""
    plan = _plan(f6_ctx)
    assert json.loads(json.dumps(plan)) == plan
    assert set(plan) == {"lot_size", "spread_pips", "long", "short"}
    for side in ("long", "short"):
        assert set(plan[side]) == {"stop_pips", "targets", "trail_stops", "reward_risk"}


@then(parsers.parse('F6\'s reason mentions "{fragment}"'))
def _reason_mentions(f6_ctx: _F6Ctx, fragment: str) -> None:
    assert fragment in _result(f6_ctx).reason, _result(f6_ctx).reason


@then(parsers.parse('F6\'s filter name is "{name}"'))
def _filter_name(f6_ctx: _F6Ctx, name: str) -> None:
    assert _result(f6_ctx).filter_name == name


@then(parsers.parse('F6\'s recommendation is "{reco}"'))
def _recommendation(f6_ctx: _F6Ctx, reco: str) -> None:
    assert _result(f6_ctx).recommendation == Recommendation(reco)


@then(parsers.parse('applying F6 fails naming "{fragment}"'))
def _apply_fails(f6_ctx: _F6Ctx, fragment: str) -> None:
    assert f6_ctx.error is not None, "F6 did not fail"
    assert fragment in str(f6_ctx.error), str(f6_ctx.error)


_SECTION_KEYS = (
    "risk_per_trade", "stop_loss_pips", "pip_value_per_lot", "lot_notional_units",
    "assumed_leverage",
)
_SECTION_DEFAULTS: dict[str, Any] = dict(
    zip(_SECTION_KEYS, (0.03, 20.0, 10.0, 100_000, 30), strict=True)
)


@given(
    parsers.parse(
        "a capital_mgmt section with risk_per_trade={risk}, stop_loss_pips={stop}, "
        "pip_value_per_lot={pip}, lot_notional_units={lot}, assumed_leverage={lev}"
    )
)
def _capital_mgmt_section(
    f6_ctx: _F6Ctx, risk: str, stop: str, pip: str, lot: str, lev: str
) -> None:
    """Build the raw YAML section; values go through YAML so the table can carry strings."""
    values = [yaml.safe_load(token) for token in (risk, stop, pip, lot, lev)]
    f6_ctx.section = dict(zip(_SECTION_KEYS, values, strict=True))


@given(parsers.parse('a capital_mgmt section missing "{missing_key}"'))
def _capital_mgmt_section_missing(f6_ctx: _F6Ctx, missing_key: str) -> None:
    f6_ctx.section = {k: v for k, v in _SECTION_DEFAULTS.items() if k != missing_key}


@when(parsers.parse('the capital-mgmt config is parsed for strategy "{strategy}"'))
def _parse_config(f6_ctx: _F6Ctx, strategy: str) -> None:
    f6_ctx.parsed_config = parse_capital_mgmt_config(f6_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the capital-mgmt config for strategy "{strategy}" fails'))
def _parse_config_fails(f6_ctx: _F6Ctx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_capital_mgmt_config(f6_ctx.section, strategy=strategy)
    f6_ctx.parse_error = exc_info.value


@then(
    parsers.parse(
        "the parsed capital-mgmt config has risk_per_trade {risk:g}, stop_loss_pips {stop:g}, "
        "pip_value_per_lot {pip:g}, lot_notional_units {lot:g} and assumed_leverage {lev:g}"
    )
)
def _parsed_config(
    f6_ctx: _F6Ctx, risk: float, stop: float, pip: float, lot: float, lev: float
) -> None:
    assert f6_ctx.parsed_config is not None
    assert f6_ctx.parsed_config == CapitalMgmtConfig(
        risk_per_trade=risk, stop_loss_pips=stop, pip_value_per_lot=pip,
        lot_notional_units=lot, assumed_leverage=lev,
    )


@then(parsers.parse('the capital-mgmt config failure names "{fragment}"'))
def _parse_failure_names(f6_ctx: _F6Ctx, fragment: str) -> None:
    assert f6_ctx.parse_error is not None
    assert fragment in str(f6_ctx.parse_error)


@given("a complete five-key capital_mgmt section")
def _five_key_section(f6_ctx: _F6Ctx) -> None:
    """The pre-story-12 section: the five sizing keys, no trade-plan key."""
    f6_ctx.section = dict(_SECTION_DEFAULTS)


@given(parsers.parse("the capital_mgmt section sets {key} to {value}"))
def _section_sets(f6_ctx: _F6Ctx, key: str, value: str) -> None:
    """Add or override one key; the table cell is flow-style YAML (lists, mappings, null)."""
    f6_ctx.section[key] = yaml.safe_load(value)


def _mapping(f6_ctx: _F6Ctx) -> dict[str, Any]:
    """The effective values of the parsed config, as the loader writes them back."""
    assert f6_ctx.parsed_config is not None
    return capital_mgmt_mapping(f6_ctx.parsed_config)


@then(parsers.parse("the capital-mgmt mapping records {key} {value}"))
def _mapping_records(f6_ctx: _F6Ctx, key: str, value: str) -> None:
    assert _mapping(f6_ctx)[key] == yaml.safe_load(value)


@then("parsing the capital-mgmt mapping again yields an equal config")
def _mapping_round_trips(f6_ctx: _F6Ctx) -> None:
    assert parse_capital_mgmt_config(_mapping(f6_ctx), strategy="rt") == f6_ctx.parsed_config


@then("the capital-mgmt mapping survives a YAML safe_dump round trip")
def _mapping_yaml_safe(f6_ctx: _F6Ctx) -> None:
    """`yaml.safe_dump` must not need python-specific tags (tuples), or safe_load breaks."""
    mapping = _mapping(f6_ctx)
    assert yaml.safe_load(yaml.safe_dump(mapping)) == mapping
