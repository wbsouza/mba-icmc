"""Steps for f5_risk_guard.feature — the F5 filter's own synthetic `state.features` contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.f5_risk_guard import RiskGuardFilter
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from algo_backtest.rules.risk_guard import RiskGuardCaps
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f5_risk_guard.feature")

_ALL_ACCOUNT_KEYS = {
    "account_portfolio_at_risk": 0.05,
    "account_daily_pnl_fraction": -0.01,
    "account_weekly_pnl_fraction": -0.02,
    "account_open_trade_count": 1,
    "account_leverage": 5.0,
}


def _parse_cap(raw: str) -> object:
    return yaml.safe_load(raw)


@dataclass
class _F5Ctx:
    """Per-scenario `state.features` + caps + the outcome of applying F5."""

    features: dict[str, Any] = field(default_factory=dict)
    caps: RiskGuardCaps | None = None
    result: FilterResult | None = None
    error: Exception | None = None


@pytest.fixture
def f5_ctx() -> _F5Ctx:
    return _F5Ctx()


@given(
    parsers.parse(
        "synthetic account features: portfolio-at-risk {par:g}, daily P&L {daily:g}, "
        "weekly P&L {weekly:g}, open trades {open_trades:d}, leverage {leverage:g}"
    )
)
def _account_features(
    f5_ctx: _F5Ctx, par: float, daily: float, weekly: float, open_trades: int, leverage: float
) -> None:
    f5_ctx.features = {
        "account_portfolio_at_risk": par,
        "account_daily_pnl_fraction": daily,
        "account_weekly_pnl_fraction": weekly,
        "account_open_trade_count": open_trades,
        "account_leverage": leverage,
    }


@given(parsers.parse('synthetic account features missing "{missing_key}"'))
def _account_features_missing(f5_ctx: _F5Ctx, missing_key: str) -> None:
    f5_ctx.features = {k: v for k, v in _ALL_ACCOUNT_KEYS.items() if k != missing_key}


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
    f5_ctx: _F5Ctx,
    portfolio_at_risk_cap: str,
    daily_drawdown_limit: str,
    weekly_drawdown_limit: str,
    max_concurrent_trades_per_account: str,
    max_leverage: str,
) -> None:
    f5_ctx.caps = RiskGuardCaps(
        portfolio_at_risk_cap=_parse_cap(portfolio_at_risk_cap),
        daily_drawdown_limit=_parse_cap(daily_drawdown_limit),
        weekly_drawdown_limit=_parse_cap(weekly_drawdown_limit),
        max_concurrent_trades_per_account=_parse_cap(max_concurrent_trades_per_account),
        max_leverage=_parse_cap(max_leverage),
    )


@when("F5 applies to the state")
def _apply(f5_ctx: _F5Ctx) -> None:
    assert f5_ctx.caps is not None
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair="EURUSD", features=dict(f5_ctx.features)
    )
    risk_filter = RiskGuardFilter(caps=f5_ctx.caps)
    try:
        f5_ctx.result = risk_filter.apply(state)
    except (KeyError, ValueError) as exc:
        f5_ctx.error = exc


@then("F5's result does not veto")
def _no_veto(f5_ctx: _F5Ctx) -> None:
    assert f5_ctx.error is None, f"unexpected error: {f5_ctx.error}"
    assert f5_ctx.result is not None
    assert f5_ctx.result.veto is False


@then("F5's result vetoes")
def _veto(f5_ctx: _F5Ctx) -> None:
    assert f5_ctx.error is None, f"unexpected error: {f5_ctx.error}"
    assert f5_ctx.result is not None
    assert f5_ctx.result.veto is True


@then(parsers.parse('F5\'s recommendation is "{reco}"'))
def _recommendation(f5_ctx: _F5Ctx, reco: str) -> None:
    assert f5_ctx.result is not None
    assert f5_ctx.result.recommendation == Recommendation(reco)


@then(parsers.parse('F5\'s reason mentions "{fragment}"'))
def _reason_mentions(f5_ctx: _F5Ctx, fragment: str) -> None:
    assert f5_ctx.result is not None
    assert fragment in f5_ctx.result.reason


@then(parsers.parse('F5\'s filter name is "{name}"'))
def _filter_name(f5_ctx: _F5Ctx, name: str) -> None:
    assert f5_ctx.result is not None
    assert f5_ctx.result.filter_name == name


@then(parsers.parse('F5\'s reason joins breaches with "{separator}"'))
def _reason_joins_with(f5_ctx: _F5Ctx, separator: str) -> None:
    assert f5_ctx.result is not None
    assert f5_ctx.result.reason.count(separator) >= 1


@then(parsers.parse('applying F5 fails naming "{missing_key}"'))
def _apply_fails(f5_ctx: _F5Ctx, missing_key: str) -> None:
    assert f5_ctx.error is not None
    assert missing_key in str(f5_ctx.error)
