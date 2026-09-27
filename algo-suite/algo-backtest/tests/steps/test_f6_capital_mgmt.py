"""Steps for f6_capital_mgmt.feature — the F6 filter's own synthetic `state.features` contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.f6_capital_mgmt import (
    CapitalMgmtConfig,
    CapitalMgmtFilter,
    parse_capital_mgmt_config,
)
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f6_capital_mgmt.feature")

_ALL_FEATURE_KEYS = {
    "account_balance": 10000.0,
    "pip_value": 1.0,
    "stop_loss_pips": 20.0,
    "margin_per_lot": 100.0,
    "available_margin": 2000.0,
}


@dataclass
class _F6Ctx:
    """Per-scenario `state.features` + risk_per_trade + the outcome of applying F6."""

    features: dict[str, Any] = field(default_factory=dict)
    risk_per_trade: float | None = None
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
        "synthetic capital-mgmt features: balance {balance:g}, pip value {pip_value:g}, "
        "stop-loss {stop_loss_pips:g} pips, margin per lot {margin_per_lot:g}, "
        "available margin {available_margin:g}"
    )
)
def _features(
    f6_ctx: _F6Ctx,
    balance: float,
    pip_value: float,
    stop_loss_pips: float,
    margin_per_lot: float,
    available_margin: float,
) -> None:
    f6_ctx.features = {
        "account_balance": balance,
        "pip_value": pip_value,
        "stop_loss_pips": stop_loss_pips,
        "margin_per_lot": margin_per_lot,
        "available_margin": available_margin,
    }


@given(parsers.parse('synthetic capital-mgmt features missing "{missing_key}"'))
def _features_missing(f6_ctx: _F6Ctx, missing_key: str) -> None:
    f6_ctx.features = {k: v for k, v in _ALL_FEATURE_KEYS.items() if k != missing_key}


@given(parsers.parse("a risk per trade of {risk:g}"))
def _risk_per_trade(f6_ctx: _F6Ctx, risk: float) -> None:
    f6_ctx.risk_per_trade = risk


@when("F6 applies to the state")
def _apply(f6_ctx: _F6Ctx) -> None:
    assert f6_ctx.risk_per_trade is not None
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f6_ctx.features)
    )
    capital_filter = CapitalMgmtFilter(risk_per_trade=f6_ctx.risk_per_trade)
    try:
        f6_ctx.result = capital_filter.apply(state)
    except (KeyError, ValueError) as exc:
        f6_ctx.error = exc


@then("F6's result does not veto")
def _no_veto(f6_ctx: _F6Ctx) -> None:
    assert f6_ctx.error is None, f"unexpected error: {f6_ctx.error}"
    assert f6_ctx.result is not None
    assert f6_ctx.result.veto is False


@then("F6's result vetoes")
def _veto(f6_ctx: _F6Ctx) -> None:
    assert f6_ctx.error is None, f"unexpected error: {f6_ctx.error}"
    assert f6_ctx.result is not None
    assert f6_ctx.result.veto is True


@then(parsers.parse('F6 enriches "{key}" with {expected:g}'))
def _enriches(f6_ctx: _F6Ctx, key: str, expected: float) -> None:
    assert f6_ctx.result is not None
    assert f6_ctx.result.enrichment[key] == pytest.approx(expected)


@then(parsers.parse('F6\'s reason mentions "{fragment}"'))
def _reason_mentions(f6_ctx: _F6Ctx, fragment: str) -> None:
    assert f6_ctx.result is not None
    assert fragment in f6_ctx.result.reason


@then(parsers.parse('F6\'s filter name is "{name}"'))
def _filter_name(f6_ctx: _F6Ctx, name: str) -> None:
    assert f6_ctx.result is not None
    assert f6_ctx.result.filter_name == name


@then(parsers.parse('F6\'s recommendation is "{reco}"'))
def _recommendation(f6_ctx: _F6Ctx, reco: str) -> None:
    assert f6_ctx.result is not None
    assert f6_ctx.result.recommendation == Recommendation(reco)


@then(parsers.parse('applying F6 fails naming "{missing_key}"'))
def _apply_fails(f6_ctx: _F6Ctx, missing_key: str) -> None:
    assert f6_ctx.error is not None
    assert missing_key in str(f6_ctx.error)


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
