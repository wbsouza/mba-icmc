"""Steps for f6_capital_mgmt.feature — the F6 filter's own synthetic `state.features` contract."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.f6_capital_mgmt import (
    CapitalMgmtFilter,
    load_capital_mgmt_config,
)
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_core.config import ConfigError, MissingTradingParameter
from algo_core.config.paths import ENV_CONF_DIR
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
    loaded_risk_per_trade: float | None = None
    load_error: Exception | None = None


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


@pytest.fixture
def f6_conf_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Clean ALGO_ env + isolated conf dir so capital-mgmt config loading is deterministic."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    conf = tmp_path / "conf"
    conf.mkdir()
    monkeypatch.setenv(ENV_CONF_DIR, str(conf))
    return conf


@given(parsers.parse("a capital_mgmt config with risk_per_trade={risk_per_trade:g}"))
def _config_with_risk(f6_ctx: _F6Ctx, f6_conf_dir: Path, risk_per_trade: float) -> None:
    (f6_conf_dir / "backtest.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "capital_mgmt": {"risk_per_trade": risk_per_trade}})
    )


@given("a capital_mgmt config missing risk_per_trade")
def _config_missing_risk(f6_ctx: _F6Ctx, f6_conf_dir: Path) -> None:
    (f6_conf_dir / "backtest.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "capital_mgmt": {}})
    )


@when("I load the capital-mgmt config")
def _load(f6_ctx: _F6Ctx) -> None:
    try:
        f6_ctx.loaded_risk_per_trade = load_capital_mgmt_config().risk_per_trade
    except ConfigError as exc:
        f6_ctx.load_error = exc


@then(parsers.parse("the loaded risk_per_trade is {expected:g}"))
def _loaded_risk(f6_ctx: _F6Ctx, expected: float) -> None:
    assert f6_ctx.load_error is None, f"unexpected error: {f6_ctx.load_error}"
    assert f6_ctx.loaded_risk_per_trade == pytest.approx(expected)


@then(parsers.parse('loading fails with a missing-trading-parameter error naming "{param}"'))
def _missing_param(f6_ctx: _F6Ctx, param: str) -> None:
    assert isinstance(f6_ctx.load_error, MissingTradingParameter)
    assert param in str(f6_ctx.load_error)
