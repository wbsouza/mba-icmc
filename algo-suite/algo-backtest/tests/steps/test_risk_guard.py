"""Steps for risk_guard.feature — cap evaluation + config-driven loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_backtest.rules.risk_guard import (
    AccountState,
    RiskCap,
    RiskGuardCaps,
    RiskGuardVerdict,
    evaluate_risk_guard,
    load_risk_guard_caps,
)
from algo_core.config import ConfigError, MissingTradingParameter
from algo_core.config.paths import ENV_CONF_DIR
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/risk_guard.feature")

_RISK_GUARD_KEYS = (
    "portfolio_at_risk_cap",
    "daily_drawdown_limit",
    "weekly_drawdown_limit",
    "max_concurrent_trades_per_account",
    "max_leverage",
)


def _parse_cap(raw: str) -> object:
    """Parse one `key=value` cap token: `null` -> None, else float/int via YAML."""
    return yaml.safe_load(raw)


@dataclass
class _RiskGuardCtx:
    """Per-scenario account state, caps, and the outcome of evaluation or config loading."""

    account: AccountState | None = None
    caps: RiskGuardCaps | None = None
    verdict: RiskGuardVerdict | None = None
    loaded_caps: RiskGuardCaps | None = None
    error: Exception | None = None


@pytest.fixture
def rg_ctx() -> _RiskGuardCtx:
    return _RiskGuardCtx()


@given(
    parsers.parse(
        "an account with portfolio-at-risk {par:g}, daily P&L {daily:g}, weekly P&L {weekly:g}, "
        "an open-trade count of {open_trades:d} and leverage {leverage:g}"
    )
)
def _account(
    rg_ctx: _RiskGuardCtx,
    par: float,
    daily: float,
    weekly: float,
    open_trades: int,
    leverage: float,
) -> None:
    rg_ctx.account = AccountState(
        portfolio_at_risk=par,
        daily_pnl_fraction=daily,
        weekly_pnl_fraction=weekly,
        open_trade_count=open_trades,
        leverage=leverage,
    )


@given(
    parsers.parse(
        "risk-guard caps: portfolio_at_risk_cap={portfolio_at_risk_cap}, "
        "daily_drawdown_limit={daily_drawdown_limit}, "
        "weekly_drawdown_limit={weekly_drawdown_limit}, "
        "max_concurrent_trades_per_account={max_concurrent_trades_per_account}, "
        "max_leverage={max_leverage}"
    )
)
def _caps(
    rg_ctx: _RiskGuardCtx,
    portfolio_at_risk_cap: str,
    daily_drawdown_limit: str,
    weekly_drawdown_limit: str,
    max_concurrent_trades_per_account: str,
    max_leverage: str,
) -> None:
    rg_ctx.caps = RiskGuardCaps(
        portfolio_at_risk_cap=_parse_cap(portfolio_at_risk_cap),
        daily_drawdown_limit=_parse_cap(daily_drawdown_limit),
        weekly_drawdown_limit=_parse_cap(weekly_drawdown_limit),
        max_concurrent_trades_per_account=_parse_cap(max_concurrent_trades_per_account),
        max_leverage=_parse_cap(max_leverage),
    )


@when("I evaluate the risk guard")
def _evaluate(rg_ctx: _RiskGuardCtx) -> None:
    assert rg_ctx.account is not None
    assert rg_ctx.caps is not None
    rg_ctx.verdict = evaluate_risk_guard(rg_ctx.account, rg_ctx.caps)


@then("the risk guard reports no breach")
def _no_breach(rg_ctx: _RiskGuardCtx) -> None:
    assert rg_ctx.verdict is not None
    assert not rg_ctx.verdict.breached, rg_ctx.verdict.breaches


@then(parsers.parse('the risk guard reports a breach of "{cap_name}"'))
def _breach_of(rg_ctx: _RiskGuardCtx, cap_name: str) -> None:
    assert rg_ctx.verdict is not None
    assert rg_ctx.verdict.breached
    wanted = RiskCap(cap_name)
    matching = [b for b in rg_ctx.verdict.breaches if b.cap == wanted]
    assert matching, f"no breach reported for {cap_name}"
    assert isinstance(matching[0].reason, str) and matching[0].reason


@pytest.fixture
def rg_conf_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Clean ALGO_ env + isolated conf dir so risk-guard config loading is deterministic."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    conf = tmp_path / "conf"
    conf.mkdir()
    monkeypatch.setenv(ENV_CONF_DIR, str(conf))
    return conf


def _write_backtest_yaml(conf_dir: Path, risk_guard: dict[str, Any]) -> None:
    (conf_dir / "backtest.yaml").write_text(
        yaml.safe_dump({"schema_version": 1, "risk_guard": risk_guard})
    )


@given(
    parsers.parse(
        "a risk_guard config with portfolio_at_risk_cap={portfolio_at_risk_cap}, "
        "daily_drawdown_limit={daily_drawdown_limit}, "
        "weekly_drawdown_limit={weekly_drawdown_limit}, "
        "max_concurrent_trades_per_account={max_concurrent_trades_per_account}, "
        "max_leverage={max_leverage}"
    )
)
def _config_with_all_caps(
    rg_ctx: _RiskGuardCtx,
    rg_conf_dir: Path,
    portfolio_at_risk_cap: str,
    daily_drawdown_limit: str,
    weekly_drawdown_limit: str,
    max_concurrent_trades_per_account: str,
    max_leverage: str,
) -> None:
    _write_backtest_yaml(
        rg_conf_dir,
        {
            "portfolio_at_risk_cap": _parse_cap(portfolio_at_risk_cap),
            "daily_drawdown_limit": _parse_cap(daily_drawdown_limit),
            "weekly_drawdown_limit": _parse_cap(weekly_drawdown_limit),
            "max_concurrent_trades_per_account": _parse_cap(max_concurrent_trades_per_account),
            "max_leverage": _parse_cap(max_leverage),
        },
    )


@given(parsers.parse('a risk_guard config missing "{missing_key}"'))
def _config_missing_key(rg_ctx: _RiskGuardCtx, rg_conf_dir: Path, missing_key: str) -> None:
    defaults = {
        "portfolio_at_risk_cap": 0.1,
        "daily_drawdown_limit": -0.05,
        "weekly_drawdown_limit": -0.1,
        "max_concurrent_trades_per_account": 2,
        "max_leverage": 10.0,
    }
    del defaults[missing_key]
    _write_backtest_yaml(rg_conf_dir, defaults)


@when("I load the risk-guard config")
def _load(rg_ctx: _RiskGuardCtx) -> None:
    try:
        rg_ctx.loaded_caps = load_risk_guard_caps()
    except ConfigError as exc:
        rg_ctx.error = exc


@then(parsers.parse("the loaded caps have portfolio_at_risk_cap {expected:g}"))
def _loaded_par(rg_ctx: _RiskGuardCtx, expected: float) -> None:
    assert rg_ctx.error is None, f"unexpected error: {rg_ctx.error}"
    assert rg_ctx.loaded_caps is not None
    assert rg_ctx.loaded_caps.portfolio_at_risk_cap == pytest.approx(expected)


@then(parsers.parse("the loaded caps have max_leverage {expected:g}"))
def _loaded_leverage(rg_ctx: _RiskGuardCtx, expected: float) -> None:
    assert rg_ctx.error is None, f"unexpected error: {rg_ctx.error}"
    assert rg_ctx.loaded_caps is not None
    assert rg_ctx.loaded_caps.max_leverage == pytest.approx(expected)


@then(parsers.parse("the loaded caps have daily_drawdown_limit {expected:g}"))
def _loaded_daily(rg_ctx: _RiskGuardCtx, expected: float) -> None:
    assert rg_ctx.error is None, f"unexpected error: {rg_ctx.error}"
    assert rg_ctx.loaded_caps is not None
    assert rg_ctx.loaded_caps.daily_drawdown_limit == pytest.approx(expected)


@then(parsers.parse("the loaded caps have weekly_drawdown_limit {expected:g}"))
def _loaded_weekly(rg_ctx: _RiskGuardCtx, expected: float) -> None:
    assert rg_ctx.error is None, f"unexpected error: {rg_ctx.error}"
    assert rg_ctx.loaded_caps is not None
    assert rg_ctx.loaded_caps.weekly_drawdown_limit == pytest.approx(expected)


@then(parsers.parse("the loaded caps have max_concurrent_trades_per_account {expected:d}"))
def _loaded_max_concurrent(rg_ctx: _RiskGuardCtx, expected: int) -> None:
    assert rg_ctx.error is None, f"unexpected error: {rg_ctx.error}"
    assert rg_ctx.loaded_caps is not None
    assert rg_ctx.loaded_caps.max_concurrent_trades_per_account == expected


@then("the loaded caps have max_leverage disabled")
def _loaded_leverage_disabled(rg_ctx: _RiskGuardCtx) -> None:
    assert rg_ctx.error is None, f"unexpected error: {rg_ctx.error}"
    assert rg_ctx.loaded_caps is not None
    assert rg_ctx.loaded_caps.max_leverage is None


@then(parsers.parse('loading fails with a missing-trading-parameter error naming "{param}"'))
def _missing_param(rg_ctx: _RiskGuardCtx, param: str) -> None:
    assert isinstance(rg_ctx.error, MissingTradingParameter)
    assert param in str(rg_ctx.error)
