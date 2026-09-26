"""Steps for chain_wiring.feature — the LEAN-free half of the chain-driven algorithms."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

import pytest
from algo_backtest.chain.filters.f4_news_context import NewsContextIndex
from algo_backtest.chain.filters.f5_risk_guard import RiskGuardFilter
from algo_backtest.chain.filters.f7_meta_learner import TrainedMetaLearner
from algo_backtest.chain.model import ExecutionState, Filter, FilterResult
from algo_backtest.chain.wiring import (
    RISK_GUARD_CAPS,
    AccountSnapshot,
    PnlWindows,
    account_features,
    build_filters,
    price_features,
)
from algo_backtest.rules.risk_guard import RiskGuardCaps
from algo_backtest.strategies import load_strategy_chain_config
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/chain_wiring.feature")

# F7MetaLearnerFilter only stores the model at construction; predict() is never called.
_UNUSED_MODEL = cast(TrainedMetaLearner, object())
_EMPTY_NEWS = NewsContextIndex(
    event_intensity={}, sentiment_polarity={}, sentiment_source_present=False
)


@dataclass
class _WiringCtx:
    """Per-scenario fixture context."""

    features: dict[str, object] = field(default_factory=dict)
    account: AccountSnapshot | None = None
    windows: PnlWindows = field(default_factory=PnlWindows)
    fractions: tuple[float, float] = (0.0, 0.0)
    filters: list[Filter] = field(default_factory=list)
    error: ValueError | None = None
    f5_result: FilterResult | None = None


@pytest.fixture
def wiring_ctx() -> _WiringCtx:
    """A fresh per-scenario context."""
    return _WiringCtx()


def _account(invested: bool, value: float, holdings: float, unrealized: float) -> AccountSnapshot:
    """An AccountSnapshot with the fields these scenarios don't vary held fixed."""
    return AccountSnapshot(
        invested=invested, portfolio_value=value, unrealized_profit=unrealized,
        holdings_value=holdings, cash=value, margin_remaining=value,
        daily_pnl_fraction=0.0, weekly_pnl_fraction=0.0,
    )


@when(
    parsers.parse(
        "price features are built for price {price:g}, fast EMA {fast:g}, "
        "slow EMA {slow:g}, HTF EMA {htf:g}"
    )
)
def _price_features(
    wiring_ctx: _WiringCtx, price: float, fast: float, slow: float, htf: float
) -> None:
    wiring_ctx.features = price_features(
        price=price, ema_fast=fast, ema_slow=slow, ema_htf=htf, rsi=50.0, macd_hist=0.0
    )


@given(
    parsers.parse(
        "an invested account worth {value:g} holding {holdings:g} with unrealized profit "
        "{unrealized:g}"
    )
)
def _invested_account(
    wiring_ctx: _WiringCtx, value: float, holdings: float, unrealized: float
) -> None:
    wiring_ctx.account = _account(True, value, holdings, unrealized)


@given(parsers.parse("a flat account worth {value:g}"))
def _flat_account(wiring_ctx: _WiringCtx, value: float) -> None:
    wiring_ctx.account = _account(False, value, 0.0, 0.0)


@when(parsers.parse("account features are built at price {price:g}"))
def _account_features(wiring_ctx: _WiringCtx, price: float) -> None:
    assert wiring_ctx.account is not None
    wiring_ctx.features = account_features(wiring_ctx.account, price)


@then(parsers.parse('feature "{name}" is {value:g}'))
def _feature_is(wiring_ctx: _WiringCtx, name: str, value: float) -> None:
    assert wiring_ctx.features[name] == pytest.approx(value)


@then(parsers.parse('feature "{name}" is missing'))
def _feature_missing(wiring_ctx: _WiringCtx, name: str) -> None:
    assert name in wiring_ctx.features and wiring_ctx.features[name] is None


@given(parsers.parse('PnL windows anchored at equity {equity:g} on "{ts}"'))
def _anchor(wiring_ctx: _WiringCtx, equity: float, ts: str) -> None:
    wiring_ctx.windows.update(datetime.fromisoformat(ts), equity)


@when(parsers.parse('equity {equity:g} is observed on "{ts}"'))
def _observe(wiring_ctx: _WiringCtx, equity: float, ts: str) -> None:
    wiring_ctx.fractions = wiring_ctx.windows.update(datetime.fromisoformat(ts), equity)


@then(
    parsers.parse(
        "the daily PnL fraction is {daily:g} and the weekly PnL fraction is {weekly:g}"
    )
)
def _fractions(wiring_ctx: _WiringCtx, daily: float, weekly: float) -> None:
    assert wiring_ctx.fractions == pytest.approx((daily, weekly))


def _build(wiring_ctx: _WiringCtx, names: list[str], news: NewsContextIndex | None) -> None:
    """Build filters, capturing a fail-fast ValueError for the Then step."""
    try:
        wiring_ctx.filters = build_filters(names, meta_learner=_UNUSED_MODEL, news_index=news)
    except ValueError as exc:
        wiring_ctx.error = exc


@when("the hybrid config's filters are built with a news index")
def _hybrid_with_news(wiring_ctx: _WiringCtx) -> None:
    _build(wiring_ctx, list(load_strategy_chain_config("hybrid").filters), _EMPTY_NEWS)


@when("the hybrid config's filters are built without a news index")
def _hybrid_without_news(wiring_ctx: _WiringCtx) -> None:
    _build(wiring_ctx, list(load_strategy_chain_config("hybrid").filters), None)


@when(parsers.parse('filters "{names}" are built'))
def _named_filters(wiring_ctx: _WiringCtx, names: str) -> None:
    _build(wiring_ctx, [name.strip() for name in names.split(",")], None)


@then(parsers.parse('the chain\'s filters are "{names}"'))
def _chain_filters(wiring_ctx: _WiringCtx, names: str) -> None:
    assert wiring_ctx.error is None, wiring_ctx.error
    expected = [name.strip() for name in names.split(",")]
    built = [type(f).__module__.rsplit(".", 1)[-1] for f in wiring_ctx.filters]
    assert built == expected


@then(parsers.parse('building fails naming "{fragment}"'))
def _fails(wiring_ctx: _WiringCtx, fragment: str) -> None:
    assert wiring_ctx.error is not None
    assert fragment in str(wiring_ctx.error)


@when("F5 evaluates the account under the wiring's placeholder caps")
def _f5_placeholder(wiring_ctx: _WiringCtx) -> None:
    assert wiring_ctx.account is not None
    state = ExecutionState(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        pair="EURUSD",
        features=account_features(wiring_ctx.account, 1.1),
    )
    wiring_ctx.f5_result = RiskGuardFilter(caps=RISK_GUARD_CAPS).apply(state)


@then("F5 does not veto")
def _f5_no_veto(wiring_ctx: _WiringCtx) -> None:
    assert wiring_ctx.f5_result is not None
    assert not wiring_ctx.f5_result.veto, wiring_ctx.f5_result.reason


@when(parsers.parse("risk-guard caps are built with daily_drawdown_limit {limit:g}"))
def _positive_limit(wiring_ctx: _WiringCtx, limit: float) -> None:
    try:
        RiskGuardCaps(
            portfolio_at_risk_cap=None, daily_drawdown_limit=limit, weekly_drawdown_limit=None,
            max_concurrent_trades_per_account=None, max_leverage=None,
        )
    except ValueError as exc:
        wiring_ctx.error = exc
