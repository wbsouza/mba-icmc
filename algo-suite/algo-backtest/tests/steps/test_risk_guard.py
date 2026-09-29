"""Steps for risk_guard.feature — cap evaluation + config-driven loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
import yaml
from algo_backtest.rules.risk_guard import (
    AccountState,
    RiskCap,
    RiskGuardCaps,
    RiskGuardVerdict,
    evaluate_risk_guard,
    parse_risk_guard_caps,
)
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
    section: dict[str, Any] = field(default_factory=dict)
    parsed_caps: RiskGuardCaps | None = None
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


_SECTION_DEFAULTS: dict[str, Any] = dict(
    zip(_RISK_GUARD_KEYS, (0.1, -0.05, -0.1, 2, 10.0), strict=True)
)


@given(
    parsers.parse(
        "a risk_guard section with portfolio_at_risk_cap={par}, daily_drawdown_limit={daily}, "
        "weekly_drawdown_limit={weekly}, max_concurrent_trades_per_account={trades}, "
        "max_leverage={lev}"
    )
)
def _risk_guard_section(
    rg_ctx: _RiskGuardCtx, par: str, daily: str, weekly: str, trades: str, lev: str
) -> None:
    """Build the raw YAML section; `null` disables a cap, strings stay strings."""
    values = [_parse_cap(token) for token in (par, daily, weekly, trades, lev)]
    rg_ctx.section = dict(zip(_RISK_GUARD_KEYS, values, strict=True))


@given(parsers.parse('a risk_guard section missing "{missing_key}"'))
def _risk_guard_section_missing(rg_ctx: _RiskGuardCtx, missing_key: str) -> None:
    rg_ctx.section = {k: v for k, v in _SECTION_DEFAULTS.items() if k != missing_key}


@when(parsers.parse('the risk-guard caps are parsed for strategy "{strategy}"'))
def _parse_caps(rg_ctx: _RiskGuardCtx, strategy: str) -> None:
    rg_ctx.parsed_caps = parse_risk_guard_caps(rg_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the risk-guard caps for strategy "{strategy}" fails'))
def _parse_caps_fails(rg_ctx: _RiskGuardCtx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_risk_guard_caps(rg_ctx.section, strategy=strategy)
    rg_ctx.error = exc_info.value


@then(
    parsers.parse(
        "the parsed caps have portfolio_at_risk_cap {par}, daily_drawdown_limit {daily}, "
        "weekly_drawdown_limit {weekly}, max_concurrent_trades_per_account {trades} and "
        "max_leverage {lev}"
    )
)
def _parsed_caps(
    rg_ctx: _RiskGuardCtx, par: str, daily: str, weekly: str, trades: str, lev: str
) -> None:
    assert rg_ctx.parsed_caps is not None
    expected = RiskGuardCaps(
        portfolio_at_risk_cap=_parse_cap(par),  # type: ignore[arg-type]
        daily_drawdown_limit=_parse_cap(daily),  # type: ignore[arg-type]
        weekly_drawdown_limit=_parse_cap(weekly),  # type: ignore[arg-type]
        max_concurrent_trades_per_account=_parse_cap(trades),  # type: ignore[arg-type]
        max_leverage=_parse_cap(lev),  # type: ignore[arg-type]
    )
    assert rg_ctx.parsed_caps == expected


@then(parsers.parse('the risk-guard config failure names "{fragment}"'))
def _parse_failure_names(rg_ctx: _RiskGuardCtx, fragment: str) -> None:
    assert rg_ctx.error is not None
    assert fragment in str(rg_ctx.error)
