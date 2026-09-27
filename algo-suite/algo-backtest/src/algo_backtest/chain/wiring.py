"""LEAN-free wiring shared by the chain-driven algorithms and their F7 training scripts.

`algos/baseline/main.py` and `algos/hybrid/main.py` differ only in their strategy name
and in whether F4/news is wired; everything else they do per bar — build the filter
chain from the resolved `config.yaml` (filter list plus each filter's own parameter
section), turn LEAN indicator/portfolio readings into the `ExecutionState.features`
contract, track day/week PnL anchors — lives here, once, type-checked and unit-tested
(the `algos/` tree itself is excluded from mypy/Ruff because it star-imports LEAN's
injected API). `scripts/train_*_meta_learner.py` build their training features through
the same `price_features()` so train and serve cannot drift.

Since the 2026-09-27 amendment (story 09) no filter parameter lives here: F4/F5/F6/F7
read `StrategyChainConfig`'s typed sections, so the bundled `strategies/<name>/config.yaml`
travels into the LEAN container with the algorithm and is the single source of the run's
economics (closing `docs/technical-debt.md` TD-43). The F6 sizing inputs are still fixed
configured values — no ATR indicator is wired (TD-51), so the stop distance is not
volatility-derived.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TypeVar

from algo_backtest.chain.filters.f1_trend import F1TrendFilter
from algo_backtest.chain.filters.f2_indicator import F2IndicatorFilter
from algo_backtest.chain.filters.f3_pattern import F3PatternFilter
from algo_backtest.chain.filters.f4_news_context import F4NewsContextFilter, NewsContextIndex
from algo_backtest.chain.filters.f5_risk_guard import RiskGuardFilter
from algo_backtest.chain.filters.f6_capital_mgmt import CapitalMgmtConfig, CapitalMgmtFilter
from algo_backtest.chain.filters.f7_meta_learner import F7MetaLearnerFilter, TrainedMetaLearner
from algo_backtest.chain.model import Filter
from algo_backtest.strategies import KNOWN_FILTERS, StrategyChainConfig

# F1 hard-requires trend_strength in [0, 100] (an ADX-style reading); the EMA-gap proxy
# below is in basis points and can exceed that on a volatile bar, so it is clamped.
_TREND_STRENGTH_CAP = 100.0
_BASIS_POINTS = 10_000.0

_KNOWN_FILTERS = sorted(KNOWN_FILTERS)


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


def account_features(
    account: AccountSnapshot, price: float, economics: CapitalMgmtConfig | None
) -> dict[str, object]:
    """The F5 (risk guard) and F6 (capital management) inputs for one bar.

    `account_leverage` uses the *unsigned* holdings value: LEAN's is negative for a net
    short, and F5's cap check is a magnitude comparison, so a signed value would never
    trip the leverage cap on a short. `economics` is the strategy's `capital_mgmt`
    section; a strategy without F6 passes `None` and gets no sizing inputs at all rather
    than invented ones.
    """
    value = account.portfolio_value
    portfolio_at_risk = (
        abs(account.unrealized_profit) / value if account.invested and value else 0.0
    )
    features: dict[str, object] = {
        "account_portfolio_at_risk": portfolio_at_risk,
        "account_daily_pnl_fraction": account.daily_pnl_fraction,
        "account_weekly_pnl_fraction": account.weekly_pnl_fraction,
        "account_open_trade_count": 1 if account.invested else 0,
        "account_leverage": abs(account.holdings_value) / value if value else 0.0,
        "account_balance": account.cash,
        "available_margin": account.margin_remaining,
    }
    if economics is not None:
        features.update(_sizing_inputs(economics, price))
    return features


def _sizing_inputs(economics: CapitalMgmtConfig, price: float) -> dict[str, object]:
    """F6's per-lot economics for this bar from the strategy's `capital_mgmt` section."""
    notional = economics.lot_notional_units * price
    return {
        "pip_value": economics.pip_value_per_lot,
        "stop_loss_pips": economics.stop_loss_pips,
        "margin_per_lot": notional / economics.assumed_leverage,
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
    config: StrategyChainConfig,
    *,
    meta_learner: TrainedMetaLearner,
    news_index: NewsContextIndex | None = None,
) -> list[Filter]:
    """Instantiate a strategy's filter list in declared order, each with its own section.

    Raises:
        ValueError: on an unknown filter name, a configurable filter whose section the
            config does not carry, or `f4_news_context` requested without a `news_index`
            (the strategy is missing `StrategySpec.needs_news_data`).
    """
    return [_build_filter(name, config, meta_learner, news_index) for name in config.filters]


_T = TypeVar("_T")


def _section(value: _T | None, section: str, config: StrategyChainConfig) -> _T:
    """A configurable filter's parsed section, failing fast if the config lacks it."""
    if value is None:
        raise ValueError(
            f"strategy {config.name!r} has no parsed '{section}' section — load it through "
            "load_strategy_chain_config so the filter's parameters come from its config.yaml"
        )
    return value


def _build_f4(
    config: StrategyChainConfig, news_index: NewsContextIndex | None
) -> F4NewsContextFilter:
    """F4 needs the run's news index on top of its own section."""
    if news_index is None:
        raise ValueError(
            "f4_news_context needs a NewsContextIndex; register the strategy with "
            "StrategySpec(needs_news_data=True) so the news Parquet is mounted"
        )
    return F4NewsContextFilter(
        index=news_index, config=_section(config.news_context, "news_context", config)
    )


_Builder = Callable[[StrategyChainConfig, TrainedMetaLearner, NewsContextIndex | None], Filter]
_BUILDERS: dict[str, _Builder] = {
    "f1_trend": lambda c, m, n: F1TrendFilter(),
    "f2_indicator": lambda c, m, n: F2IndicatorFilter(
        config=_section(c.indicator, "indicator", c)
    ),
    "f3_pattern": lambda c, m, n: F3PatternFilter(config=_section(c.pattern, "pattern", c)),
    "f4_news_context": lambda c, m, n: _build_f4(c, n),
    "f5_risk_guard": lambda c, m, n: RiskGuardFilter(
        caps=_section(c.risk_guard, "risk_guard", c)
    ),
    "f6_capital_mgmt": lambda c, m, n: CapitalMgmtFilter(
        risk_per_trade=_section(c.capital_mgmt, "capital_mgmt", c).risk_per_trade
    ),
    "f7_meta_learner": lambda c, m, n: F7MetaLearnerFilter(
        meta_learner=m, config=_section(c.f7, "meta_learner", c)
    ),
}


def _build_filter(
    name: str,
    config: StrategyChainConfig,
    meta_learner: TrainedMetaLearner,
    news_index: NewsContextIndex | None,
) -> Filter:
    """One filter by its `config.yaml` name, parameterised from its own section."""
    builder = _BUILDERS.get(name)
    if builder is None:
        raise ValueError(f"unknown filter {name!r} in strategy config; known: {_KNOWN_FILTERS}")
    return builder(config, meta_learner, news_index)


def parse_yyyymmdd(raw: str) -> date:
    """A LEAN backtest parameter date (``YYYYMMDD``) as a `date`."""
    return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))


def file_sha256(path: Path) -> str:
    """Hex SHA-256 of a file's bytes — ties a run's log to the exact model it loaded."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
