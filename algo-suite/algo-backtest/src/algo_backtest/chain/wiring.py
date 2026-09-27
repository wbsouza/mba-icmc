"""LEAN-free wiring shared by the chain-driven algorithms and their F7 training scripts.

`algos/baseline/main.py` and `algos/hybrid/main.py` differ only in their strategy name
and in whether F4/news is wired; everything else they do per bar — build the filter
chain from `config.yaml`, turn LEAN indicator/portfolio readings into the
`ExecutionState.features` contract, track day/week PnL anchors — lives here, once,
type-checked and unit-tested (the `algos/` tree itself is excluded from mypy/Ruff because
it star-imports LEAN's injected API). `scripts/train_*_meta_learner.py` build their
training features through the same `price_features()` so train and serve cannot drift.

The placeholder values below are SMOKE-TEST values, not methodology results (see
`docs/technical-debt.md` TD-51/TD-43): nothing mounts the host's `conf/` into the LEAN
container, so the filters' own `load_*_config()` defaults would fail fast in there.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from algo_backtest.chain.filters.f1_trend import F1TrendFilter
from algo_backtest.chain.filters.f2_indicator import F2IndicatorFilter
from algo_backtest.chain.filters.f3_pattern import F3PatternFilter
from algo_backtest.chain.filters.f4_news_context import (
    F4NewsContextFilter,
    NewsContextConfig,
    NewsContextIndex,
)
from algo_backtest.chain.filters.f5_risk_guard import RiskGuardFilter
from algo_backtest.chain.filters.f6_capital_mgmt import CapitalMgmtFilter
from algo_backtest.chain.filters.f7_meta_learner import (
    F7Config,
    F7MetaLearnerFilter,
    TrainedMetaLearner,
)
from algo_backtest.chain.model import Filter
from algo_backtest.rules.risk_guard import RiskGuardCaps

# Indicator periods: the LEAN indicators in algos/*/main.py and the plain-Python
# re-implementation in scripts/train_*_meta_learner.py must agree.
EMA_FAST_PERIOD = 3
EMA_SLOW_PERIOD = 8
EMA_HTF_PERIOD = 60
RSI_PERIOD = 14
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9

RISK_GUARD_CAPS = RiskGuardCaps(
    portfolio_at_risk_cap=0.10,
    # Negative: PnL fractions a day/week may not fall below (RiskGuardCaps' contract).
    daily_drawdown_limit=-0.05,
    weekly_drawdown_limit=-0.15,
    max_concurrent_trades_per_account=5,
    max_leverage=30,
)
RISK_PER_TRADE = 0.03  # specs.md Sec 14.5/14.7: 3% legacy reference value (Strategy A05)
F7_CONFIG = F7Config(theta_high=0.55, theta_low=0.45)
NEWS_CONTEXT_CONFIG = NewsContextConfig(
    event_intensity_veto_threshold=-0.5,
    sentiment_direction_threshold=0.15,
)
# No ATR indicator is wired yet (f6_capital_mgmt.py's documented gap), so the stop
# distance and per-lot economics are fixed placeholders, not derived from volatility.
STOP_LOSS_PIPS = 20.0
PIP_VALUE_PER_LOT = 10.0  # standard EURUSD convention: ~$10/pip per 100k-unit lot
LOT_NOTIONAL_UNITS = 100_000.0
ASSUMED_LEVERAGE = 30.0  # matches RISK_GUARD_CAPS.max_leverage above

# F1 hard-requires trend_strength in [0, 100] (an ADX-style reading); the EMA-gap proxy
# below is in basis points and can exceed that on a volatile bar, so it is clamped.
_TREND_STRENGTH_CAP = 100.0
_BASIS_POINTS = 10_000.0

_PRICE_AND_RISK_FILTERS: dict[str, Callable[[], Filter]] = {
    "f1_trend": F1TrendFilter,
    "f2_indicator": F2IndicatorFilter,
    "f3_pattern": F3PatternFilter,
    "f5_risk_guard": lambda: RiskGuardFilter(caps=RISK_GUARD_CAPS),
    "f6_capital_mgmt": lambda: CapitalMgmtFilter(risk_per_trade=RISK_PER_TRADE),
}


def _sign(delta: float) -> float:
    """-1.0 / 0.0 / 1.0 by the sign of ``delta``."""
    if delta > 0:
        return 1.0
    if delta < 0:
        return -1.0
    return 0.0


def price_features(
    *,
    price: float,
    ema_fast: float,
    ema_slow: float,
    ema_htf: float,
    rsi: float,
    macd_hist: float,
) -> dict[str, object]:
    """The F1/F2/F3 (and F7 TREND/INDICATOR/PATTERN family) inputs for one bar.

    `candlestick_pattern` is always `None`: no real detector is wired yet
    (`f3_pattern.py`'s documented gap) — deliberately missing, not fabricated.
    """
    trend_strength = (
        min(abs(ema_fast - ema_slow) / price * _BASIS_POINTS, _TREND_STRENGTH_CAP) if price else 0.0
    )
    return {
        "trend_direction": _sign(ema_fast - ema_slow),
        "trend_strength": trend_strength,
        "higher_tf_trend_direction": _sign(price - ema_htf),
        "rsi": rsi,
        "macd_hist": macd_hist,
        "candlestick_pattern": None,
    }


@dataclass(frozen=True)
class AccountSnapshot:
    """The LEAN portfolio readings F5/F6 need, captured once per bar."""

    invested: bool
    portfolio_value: float
    unrealized_profit: float
    holdings_value: float
    cash: float
    margin_remaining: float
    daily_pnl_fraction: float
    weekly_pnl_fraction: float


def account_features(account: AccountSnapshot, price: float) -> dict[str, object]:
    """The F5 (risk guard) and F6 (capital management) inputs for one bar.

    `account_leverage` uses the *unsigned* holdings value: LEAN's is negative for a net
    short, and F5's cap check is a magnitude comparison, so a signed value would never
    trip the leverage cap on a short.
    """
    value = account.portfolio_value
    portfolio_at_risk = (
        abs(account.unrealized_profit) / value if account.invested and value else 0.0
    )
    return {
        "account_portfolio_at_risk": portfolio_at_risk,
        "account_daily_pnl_fraction": account.daily_pnl_fraction,
        "account_weekly_pnl_fraction": account.weekly_pnl_fraction,
        "account_open_trade_count": 1 if account.invested else 0,
        "account_leverage": abs(account.holdings_value) / value if value else 0.0,
        "account_balance": account.cash,
        "pip_value": PIP_VALUE_PER_LOT,
        "stop_loss_pips": STOP_LOSS_PIPS,
        "margin_per_lot": (LOT_NOTIONAL_UNITS * price) / ASSUMED_LEVERAGE if price else 0.0,
        "available_margin": account.margin_remaining,
    }


def _fraction(equity: float, anchor: float | None) -> float:
    """PnL of ``equity`` relative to ``anchor`` as a fraction; 0.0 without an anchor."""
    return (equity - anchor) / anchor if anchor else 0.0


class PnlWindows:
    """Day- and ISO-week-start equity anchors, reset on the first bar of each period."""

    def __init__(self) -> None:
        self._day: date | None = None
        self._week: tuple[int, int] | None = None
        self._day_equity: float | None = None
        self._week_equity: float | None = None

    def update(self, now: datetime, equity: float) -> tuple[float, float]:
        """Roll the anchors forward to ``now`` and return (daily, weekly) PnL fractions."""
        today = now.date()
        iso = today.isocalendar()
        week = (iso.year, iso.week)
        if self._day != today:
            self._day, self._day_equity = today, equity
        if self._week != week:
            self._week, self._week_equity = week, equity
        return _fraction(equity, self._day_equity), _fraction(equity, self._week_equity)


def build_filters(
    names: Sequence[str],
    *,
    meta_learner: TrainedMetaLearner,
    news_index: NewsContextIndex | None = None,
) -> list[Filter]:
    """Instantiate a strategy's `config.yaml` filter list, in declared order.

    Raises:
        ValueError: on an unknown filter name, or `f4_news_context` requested without a
            `news_index` (the strategy is missing `StrategySpec.needs_news_data`).
    """
    return [_build_filter(name, meta_learner, news_index) for name in names]


def _build_filter(
    name: str, meta_learner: TrainedMetaLearner, news_index: NewsContextIndex | None
) -> Filter:
    """One filter by its `config.yaml` name."""
    if name == "f7_meta_learner":
        return F7MetaLearnerFilter(meta_learner=meta_learner, config=F7_CONFIG)
    if name == "f4_news_context":
        if news_index is None:
            raise ValueError(
                "f4_news_context needs a NewsContextIndex; register the strategy with "
                "StrategySpec(needs_news_data=True) so the news Parquet is mounted"
            )
        return F4NewsContextFilter(index=news_index, config=NEWS_CONTEXT_CONFIG)
    factory = _PRICE_AND_RISK_FILTERS.get(name)
    if factory is None:
        known = sorted([*_PRICE_AND_RISK_FILTERS, "f4_news_context", "f7_meta_learner"])
        raise ValueError(f"unknown filter {name!r} in strategy config; known: {known}")
    return factory()


def parse_yyyymmdd(raw: str) -> date:
    """A LEAN backtest parameter date (``YYYYMMDD``) as a `date`."""
    return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))


def file_sha256(path: Path) -> str:
    """Hex SHA-256 of a file's bytes — ties a run's log to the exact model it loaded."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
