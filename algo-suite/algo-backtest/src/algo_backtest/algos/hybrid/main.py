# AlgorithmImports (LEAN's injected API bridge) forces star-imports and post-import
# locals -- see engine/algorithm.py's docstring; every order goes through OrderExecutor's
# execute/close, plus a debug()/log() line per fill/close, so every fill is normalized
# and every rejection recorded, and every decision is grep-able from container logs the
# same way order_execution.feature already asserts on baseline_ma/main.py.
from datetime import UTC, date  # noqa: E402
from pathlib import Path  # noqa: E402

import joblib  # noqa: E402
from algo_backtest.chain.decision_recorder import DecisionRecorder  # noqa: E402
from algo_backtest.chain.filters.f1_trend import F1TrendFilter  # noqa: E402
from algo_backtest.chain.filters.f2_indicator import F2IndicatorFilter  # noqa: E402
from algo_backtest.chain.filters.f3_pattern import F3PatternFilter  # noqa: E402
from algo_backtest.chain.filters.f4_news_context import (  # noqa: E402
    F4NewsContextFilter,
    NewsContextConfig,
    NewsContextIndex,
    load_news_context_index,
)
from algo_backtest.chain.filters.f5_risk_guard import RiskGuardFilter  # noqa: E402
from algo_backtest.chain.filters.f6_capital_mgmt import CapitalMgmtFilter  # noqa: E402
from algo_backtest.chain.filters.f7_meta_learner import F7Config, F7MetaLearnerFilter  # noqa: E402
from algo_backtest.chain.model import ExecutionState, FilterChain  # noqa: E402
from algo_backtest.chain.terminal import (  # noqa: E402
    F7TerminalDecision,
    decision_to_order_action,
)
from algo_backtest.rules.risk_guard import RiskGuardCaps  # noqa: E402
from algo_backtest.strategies import load_strategy_chain_config  # noqa: E402
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)
from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision as OrderDecision  # noqa: E402
from engine.order_executor import FillStatus, SizingContext  # noqa: E402

_DECISIONS_PATH = Path("/Results") / "decisions.parquet"  # matches lean_runner.py's _RESULTS_MNT

# SMOKE-TEST placeholders (2026-09-26, docs/stories/planned/04h-.../progress.md and
# technical-debt.md TD-51/TD-43) -- not real methodology values. Identical to
# algos/baseline/main.py's own placeholders (see that module's docstring for the full
# rationale): `algo_core.config.resolve` needs a `conf/backtest.yaml` reachable from
# wherever it runs, and nothing mounts the host's conf/ tree into the LEAN container, so
# every filter's own `load_*_config()` default factory would fail fast inside the
# container. Constructing them explicitly sidesteps that gap for this smoke test.
_RISK_GUARD_CAPS = RiskGuardCaps(
    portfolio_at_risk_cap=0.10,
    daily_drawdown_limit=0.05,
    weekly_drawdown_limit=0.15,
    max_concurrent_trades_per_account=5,
    max_leverage=30,
)
_RISK_PER_TRADE = 0.03  # specs.md Sec 14.5/14.7: 3% legacy reference value (Strategy A05)
_F7_CONFIG = F7Config(theta_high=0.55, theta_low=0.45)  # f7_meta_learner.py's own test default
# f4_news_context.py's own test defaults (tests/steps/test_f4_news_context.py) -- same
# placeholder reasoning as F5/F6/F7 above, not a real methodology-calibrated threshold.
_NEWS_CONTEXT_CONFIG = NewsContextConfig(
    event_intensity_veto_threshold=-0.5,
    sentiment_direction_threshold=0.15,
)

_FILTER_FACTORIES = {
    "f1_trend": F1TrendFilter,
    "f2_indicator": F2IndicatorFilter,
    "f3_pattern": F3PatternFilter,
    "f5_risk_guard": lambda: RiskGuardFilter(caps=_RISK_GUARD_CAPS),
    "f6_capital_mgmt": lambda: CapitalMgmtFilter(risk_per_trade=_RISK_PER_TRADE),
}

# No ATR indicator is wired yet (f6_capital_mgmt.py's own docstring already documents
# this as its known contract gap), so the stop distance and per-lot economics below are
# fixed placeholders, not derived from real volatility.
_STOP_LOSS_PIPS = 20.0
_PIP_VALUE_PER_LOT = 10.0  # standard EURUSD convention: ~$10/pip per 100k-unit lot
_LOT_NOTIONAL_UNITS = 100_000.0
_ASSUMED_LEVERAGE = 30.0  # matches _RISK_GUARD_CAPS.max_leverage above


def _month_range(start: date, end: date) -> list[tuple[int, int]]:
    """Every (year, month) the inclusive [start, end] window touches, in calendar order."""
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        month += 1
        if month == 13:
            month, year = 1, year + 1
    return months


def _merged_news_context_index(
    data_root: Path, pair: str, start: date, end: date
) -> NewsContextIndex:
    """Merge each calendar month the run window touches into one `NewsContextIndex`.

    F4's own loader (`load_news_context_index`) is scoped to a single (year, month)
    partition; a backtest window may span a month boundary, so this merges every
    touched month's real event/sentiment Parquet into the single index F4 needs for
    the whole run. `sentiment_source_present` is true if *any* touched month had real
    sentiment data materialized (an OR, not last-month-wins), matching F4's own
    per-audit-row semantics of "was there ever a real sentiment source to consult".
    """
    event_intensity: dict[object, float] = {}
    sentiment_polarity: dict[object, float] = {}
    sentiment_source_present = False
    for year, month in _month_range(start, end):
        index = load_news_context_index(data_root, pair, year, month)
        event_intensity.update(index.event_intensity)
        sentiment_polarity.update(index.sentiment_polarity)
        sentiment_source_present = sentiment_source_present or index.sentiment_source_present
    return NewsContextIndex(
        event_intensity=event_intensity,  # type: ignore[arg-type]
        sentiment_polarity=sentiment_polarity,  # type: ignore[arg-type]
        sentiment_source_present=sentiment_source_present,
    )


class main(ExecutionAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Runs the "hybrid" F1+F2+F3+F4+F5+F6+F7 chain (adds news) each bar.

    SMOKE TEST, not a methodology result (see this repo's technical-debt.md TD-51 and
    docs/stories/planned/04h-algo-backtest-hybrid-integration/progress.md) -- identical
    caveats to ``algos/baseline/main.py`` (F3's candlestick pattern never populated,
    F5/F6's account-risk features use fixed placeholder economics, F7's meta-learner
    trained on a short window), plus F4's own documented gap: real GDELT event-intensity
    veto input, but per-symbol sentiment is best-effort/ABSTAIN pending TD-48 (no real
    sentiment Parquet materialized yet). This class exists to prove the full F1-F7 chain
    *including* F4/news is wired correctly end to end against the real pinned LEAN
    container, nothing more.
    """

    strategy_name = "hybrid"

    def initialize(self) -> None:
        """Read backtest parameters, subscribe, build indicators + the filter chain."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        symbol = self._required("symbol")
        start = self._required("start")
        end = self._required("end")
        self._size = float(self._required("size"))
        broker_adapter = self._required("broker_adapter")
        news_data_root = self._required("news_data_root")

        self.set_start_date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        self.set_end_date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        self._symbol = self.add_forex(  # noqa: F405
            symbol, Resolution.MINUTE, Market.OANDA  # noqa: F405
        ).symbol

        self._ema_fast = self.ema(self._symbol, 3, Resolution.MINUTE)  # noqa: F405
        self._ema_slow = self.ema(self._symbol, 8, Resolution.MINUTE)  # noqa: F405
        self._ema_htf = self.ema(self._symbol, 60, Resolution.MINUTE)  # noqa: F405
        self._rsi = self.rsi(self._symbol, 14, MovingAverageType.WILDERS, Resolution.MINUTE)  # noqa: F405
        self._macd = self.macd(  # noqa: F405
            self._symbol, 12, 26, 9, MovingAverageType.EXPONENTIAL, Resolution.MINUTE  # noqa: F405
        )

        # joblib.load: safe here -- this file is a static asset shipped in this same
        # directory, committed by us via scripts/train_hybrid_meta_learner.py, never
        # user/network input, same trust boundary as importing this module's own code.
        model_path = Path(__file__).parent / "f7_meta_learner.joblib"
        meta_learner = joblib.load(model_path)

        start_date = date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        end_date = date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        news_index = _merged_news_context_index(
            Path(news_data_root), symbol, start_date, end_date
        )

        config = load_strategy_chain_config("hybrid")
        filters = []
        for name in config.filters:
            if name == "f7_meta_learner":
                filters.append(F7MetaLearnerFilter(meta_learner=meta_learner, config=_F7_CONFIG))
            elif name == "f4_news_context":
                filters.append(
                    F4NewsContextFilter(index=news_index, config=_NEWS_CONTEXT_CONFIG)
                )
            else:
                filters.append(_FILTER_FACTORIES[name]())
        self._chain = FilterChain(filters=filters, terminal=F7TerminalDecision())
        self._decisions = DecisionRecorder()

        self._day_start_equity = None
        self._week_start_equity = None
        self._current_day = None
        self._current_week = None

        self.init_execution(broker_adapter)

    def _track_pnl_windows(self) -> tuple[float, float]:
        """Update/read the day- and week-start equity anchors; return their PnL fractions."""
        equity = self.portfolio.total_portfolio_value
        today = self.time.date()
        week = today.isocalendar()[:2]
        if self._current_day != today:
            self._current_day = today
            self._day_start_equity = equity
        if self._current_week != week:
            self._current_week = week
            self._week_start_equity = equity
        daily_fraction = (
            (equity - self._day_start_equity) / self._day_start_equity
            if self._day_start_equity
            else 0.0
        )
        weekly_fraction = (
            (equity - self._week_start_equity) / self._week_start_equity
            if self._week_start_equity
            else 0.0
        )
        return daily_fraction, weekly_fraction

    def _build_features(self) -> dict[str, object]:
        """Compute this bar's full state.features contract for the F1+F2+F3+F5+F6+F7 chain.

        F4's own inputs (news_event_intensity/news_sentiment_score) are not part of this
        dict -- F4NewsContextFilter reads its `NewsContextIndex` directly, keyed by
        `state.timestamp`/`state.pair`, and enriches `state.features` itself during
        `chain.run()` (see chain/model.py's accumulation contract), the same pattern F1-F3
        already use for their own enrichment.
        """
        price = self.securities[self._symbol].price
        fast = self._ema_fast.current.value
        slow = self._ema_slow.current.value
        htf = self._ema_htf.current.value
        trend_direction = 1.0 if fast > slow else (-1.0 if fast < slow else 0.0)
        # F1TrendFilter hard-requires trend_strength in [0, 100] (an ADX-style reading)
        # and raises ValueError outside that range -- an unclamped basis-point EMA gap
        # can exceed 100 on a volatile bar and abort the whole backtest (2026-09-26 PR
        # #33 review). Clamped here since this is a proxy metric, not real ADX, which is
        # bounded [0, 100] by construction.
        trend_strength = min(abs(fast - slow) / price * 10_000.0, 100.0) if price else 0.0
        higher_tf_trend_direction = 1.0 if price > htf else (-1.0 if price < htf else 0.0)
        macd_hist = self._macd.current.value - self._macd.signal.current.value

        invested = self.portfolio.invested
        portfolio_value = self.portfolio.total_portfolio_value
        daily_fraction, weekly_fraction = self._track_pnl_windows()
        portfolio_at_risk = (
            abs(self.portfolio.total_unrealized_profit) / portfolio_value
            if invested and portfolio_value
            else 0.0
        )
        # abs(): LEAN's total_holdings_value is signed (negative for a net-short
        # portfolio), but RiskGuardFilter's cap check is `leverage > max_leverage` --
        # an unsigned magnitude comparison. Leaving it signed made the leverage cap
        # never trip for short positions (2026-09-26 PR #33 review: asymmetric risk-guard
        # hole).
        leverage = (
            abs(self.portfolio.total_holdings_value) / portfolio_value
            if portfolio_value
            else 0.0
        )
        margin_per_lot = (_LOT_NOTIONAL_UNITS * price) / _ASSUMED_LEVERAGE if price else 0.0

        return {
            "trend_direction": trend_direction,
            "trend_strength": trend_strength,
            "higher_tf_trend_direction": higher_tf_trend_direction,
            "rsi": self._rsi.current.value,
            "macd_hist": macd_hist,
            "candlestick_pattern": None,  # no real detector wired yet -- f3_pattern.py's own gap
            "account_portfolio_at_risk": portfolio_at_risk,
            "account_daily_pnl_fraction": daily_fraction,
            "account_weekly_pnl_fraction": weekly_fraction,
            "account_open_trade_count": 1 if invested else 0,
            "account_leverage": leverage,
            "account_balance": self.portfolio.cash,
            "pip_value": _PIP_VALUE_PER_LOT,
            "stop_loss_pips": _STOP_LOSS_PIPS,
            "margin_per_lot": margin_per_lot,
            "available_margin": self.portfolio.margin_remaining,
        }

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """Each bar: run the F1-F7 chain, execute/manage/stand-aside per its Decision."""
        if not (
            self._ema_fast.is_ready
            and self._ema_slow.is_ready
            and self._ema_htf.is_ready
            and self._rsi.is_ready
            and self._macd.is_ready
        ):
            return
        if self._symbol not in data.quote_bars:
            return

        state = ExecutionState(
            timestamp=self.time.replace(tzinfo=UTC),
            pair=str(self._symbol),
            features=self._build_features(),
        )
        outcome = self._chain.run(state)
        action = decision_to_order_action(outcome.decision)
        self.debug(f"HYBRID_DECISION|decision={outcome.decision}|action={action}")  # noqa: F405

        if action == "execute":
            # Explicit cross-boundary conversion (chain.model.Decision -> engine.order_
            # executor.Decision), per chain/terminal.py's own docstring: they're separate
            # StrEnum classes with the same values, and OrderExecutor.execute() must
            # receive its own class, not rely on == vs is alone (2026-09-26 PR #33 review).
            sizing = SizingContext(size=self._size)
            order_decision = OrderDecision(outcome.decision.value)
            fill = self.order_executor.execute(self._symbol, order_decision, sizing)
            # order_id, not the trade's UUID (chain/audit.py's DecisionRow.trade_id is the
            # foreign key SPEC.md Sec 6.2 defines): LEAN's own closed-trade ledger
            # (trades.json) records each trade's `orderIds`, whose first entry is this same
            # entry order id -- the real, verifiable join key between the two files (Spec
            # 04h, "decisions.parquet joins trades.json by trade_id").
            if fill.status == FillStatus.FILLED and fill.order_id is not None:
                self._decisions.open_trade(str(fill.order_id))
        elif action == "stand_aside" and self.portfolio.invested:
            self.order_executor.close(self._symbol)
            self._decisions.close_trade()
        # action == "manage" (HOLD): leave any open position (and its trade_id) alone.
        self._decisions.record(outcome)

    def on_end_of_algorithm(self) -> None:
        """Emit the closed-trade count for log-based assertions; persist decisions.parquet."""
        closed = sum(1 for trade in self.trade_builder.closed_trades)
        self.debug(f"HYBRID_CLOSED_TRADES={closed}")  # noqa: F405
        self._decisions.write(_DECISIONS_PATH)
