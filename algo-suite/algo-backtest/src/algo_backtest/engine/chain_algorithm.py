"""ChainAlgorithm: the shared LEAN glue for every config.yaml-driven F1-F7 strategy.

Container-only, like ``engine/algorithm.py`` (it subclasses ``ExecutionAlgorithm`` and
uses LEAN's injected API), so it is not type-checked; everything that *can* live outside
LEAN — filter construction, the features contract, PnL anchors, placeholder economics —
is in the type-checked, unit-tested ``algo_backtest.chain.wiring`` instead. A strategy's
``main.py`` only names itself, points at its model, and (for news-driven strategies)
supplies a ``NewsContextIndex`` via :meth:`_news_index`.

Every bar: build ``ExecutionState`` (``self.time`` is the bar's *end*, the decision time
the F7 training scripts also key their news lookups on), run the chain, map its
``Decision`` to execute/manage/stand-aside through ``self.order_executor``, and record one
``decisions.parquet`` row whose ``trade_id`` identifies the LEAN trade open at that
moment — the ledger is explicitly configured flat-to-flat (``use_flat_to_flat_trades``)
to match ``DecisionRecorder.on_fill`` — written once at end of algorithm.
"""

from __future__ import annotations

import json
from datetime import UTC, date
from pathlib import Path

from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)
from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision as OrderDecision  # noqa: E402
from engine.order_executor import FillStatus, SizingContext  # noqa: E402

from algo_backtest.chain.decision_recorder import DecisionRecorder
from algo_backtest.chain.filters.f4_news_context import NewsContextIndex
from algo_backtest.chain.filters.f7_model_io import load_model, require_families
from algo_backtest.chain.model import ExecutionState, FilterChain
from algo_backtest.chain.terminal import F7TerminalDecision, decision_to_order_action
from algo_backtest.chain.wiring import (
    EMA_FAST_PERIOD,
    EMA_HTF_PERIOD,
    EMA_SLOW_PERIOD,
    MACD_FAST_PERIOD,
    MACD_SIGNAL_PERIOD,
    MACD_SLOW_PERIOD,
    RSI_PERIOD,
    AccountSnapshot,
    PnlWindows,
    account_features,
    build_filters,
    file_sha256,
    parse_yyyymmdd,
    price_features,
)
from algo_backtest.container_paths import DECISIONS_FILE
from algo_backtest.perception.config import PerceptionConfig
from algo_backtest.strategies import load_strategy_chain_config


def use_flat_to_flat_trades(algorithm: QCAlgorithm) -> None:  # noqa: F405
    """Group fills into LEAN trades flat-to-flat (FIFO matching).

    LEAN's default trade builder groups fill-to-fill, which splits a scale-in or a
    partial exit into several overlapping "trades" (e.g. fills +10k, +5k, -10k, -5k ->
    trades [1, 3] and [2, 4]). The audit trail's contract is one trade per flat-to-flat
    position episode — ``DecisionRecorder.on_fill`` tracks exactly that — so the
    ledger LEAN writes (``trades.json``) must use the same policy for
    ``decisions.parquet.trade_id`` to identify the right trade at every timestamp.
    """
    algorithm.set_trade_builder(
        TradeBuilder(FillGroupingMethod.FLAT_TO_FLAT, FillMatchingMethod.FIFO)  # noqa: F405
    )


class ChainAlgorithm(ExecutionAlgorithm):
    """Base for chain-driven strategies; subclasses set the three class attributes below.

    - ``strategy_name``: the ``strategies/<name>/config.yaml`` to load (also labels
      ``_required`` failures).
    - ``log_tag``: prefix of the grep-able ``<TAG>_DECISION|...`` / ``<TAG>_MODEL_SHA256``
      / ``<TAG>_CLOSED_TRADES`` log lines the integration scenarios assert on.
    - ``model_path``: the F7 model JSON next to the strategy's ``main.py`` (portable,
      pickle-free, provenance embedded — ``chain/filters/f7_model_io.py``), written by
      ``scripts/train_*_meta_learner.py`` or replaced for one run via ``run --model``.
    """

    log_tag: str = ""
    model_path: Path

    def _news_index(self, symbol: str, start: date, end: date) -> NewsContextIndex | None:
        """The F4 news index for the run window; ``None`` for a strategy without F4."""
        return None

    def initialize(self) -> None:
        """Read backtest parameters, subscribe, build indicators + the filter chain."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        use_flat_to_flat_trades(self)
        symbol = self._required("symbol")
        start = parse_yyyymmdd(self._required("start"))
        end = parse_yyyymmdd(self._required("end"))
        self._size = float(self._required("size"))
        broker_adapter = self._required("broker_adapter")

        self.set_start_date(start.year, start.month, start.day)
        self.set_end_date(end.year, end.month, end.day)
        self._symbol = self.add_forex(symbol, Resolution.MINUTE, Market.OANDA).symbol  # noqa: F405
        config = load_strategy_chain_config(
            self.get_parameter("chain_config") or self.strategy_name
        )
        self._subscribe_indicators(config.perception)
        self.debug(f"{self.log_tag}_PERCEPTION_SOURCE={config.perception.source}")
        Path(DECISIONS_FILE).with_name("strategy-config.json").write_text(
            json.dumps(dict(config.raw), indent=2)
        )

        meta_learner = load_model(self.model_path)
        self.debug(f"{self.log_tag}_MODEL_SHA256={file_sha256(self.model_path)}")
        require_families(
            meta_learner.families, config.meta_learner_families, where=str(self.model_path)
        )
        filters = build_filters(
            config.filters,
            meta_learner=meta_learner,
            news_index=self._news_index(symbol, start, end),
        )
        self._chain = FilterChain(filters=filters, terminal=F7TerminalDecision())
        self._decisions = DecisionRecorder()
        self._pnl = PnlWindows()

        self.init_execution(broker_adapter)

    def _subscribe_indicators(self, perception: PerceptionConfig | None = None) -> None:
        """Subscribe EMA/RSI/MACD and, when selected, construct the native HA perception."""
        perception = perception if perception is not None else PerceptionConfig()
        self._trend_perception = None
        if perception.source == "double_smoothed_heikin_ashi":
            from algo_backtest.perception.multi_timeframe import MultiTimeframeHeikinAshi

            self._trend_perception = MultiTimeframeHeikinAshi(
                period1=perception.period1, period2=perception.period2,
                higher_tf_minutes=perception.higher_tf_minutes,
            )
        minute = Resolution.MINUTE  # noqa: F405
        self._ema_fast = self.ema(self._symbol, EMA_FAST_PERIOD, minute)
        self._ema_slow = self.ema(self._symbol, EMA_SLOW_PERIOD, minute)
        self._ema_htf = self.ema(self._symbol, EMA_HTF_PERIOD, minute)
        self._rsi = self.rsi(self._symbol, RSI_PERIOD, MovingAverageType.WILDERS, minute)  # noqa: F405
        self._macd = self.macd(
            self._symbol, MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD,
            MovingAverageType.EXPONENTIAL, minute,  # noqa: F405
        )

    def _indicators_ready(self) -> bool:
        """Whether every indicator the features contract reads has warmed up."""
        indicators = (self._ema_fast, self._ema_slow, self._ema_htf, self._rsi, self._macd)
        return all(indicator.is_ready for indicator in indicators) and (
            self._trend_perception is None or self._trend_perception.is_ready
        )

    def _features(self) -> dict[str, object]:
        """This bar's ``ExecutionState.features``, via the shared wiring contract."""
        price = self.securities[self._symbol].price
        portfolio = self.portfolio
        daily, weekly = self._pnl.update(self.time, portfolio.total_portfolio_value)
        account = AccountSnapshot(
            invested=portfolio.invested,
            portfolio_value=portfolio.total_portfolio_value,
            unrealized_profit=portfolio.total_unrealized_profit,
            holdings_value=portfolio.total_holdings_value,
            cash=portfolio.cash,
            margin_remaining=portfolio.margin_remaining,
            daily_pnl_fraction=daily,
            weekly_pnl_fraction=weekly,
        )
        market = price_features(
            price=price,
            ema_fast=self._ema_fast.current.value,
            ema_slow=self._ema_slow.current.value,
            ema_htf=self._ema_htf.current.value,
            rsi=self._rsi.current.value,
            macd_hist=self._macd.current.value - self._macd.signal.current.value,
        )
        if self._trend_perception is not None:
            market.update(self._trend_perception.features())
        return {**market, **account_features(account, price)}

    def _state(self) -> ExecutionState:
        """This bar's chain input: decision time (the bar's end), pair, features.

        The single place the live timestamp F4 keys its news lookup on is built — the
        F7 training scripts key theirs on the same bar end (`training.py`), and
        `feature_parity.feature` checks the two agree per bar in real LEAN.
        """
        return ExecutionState(
            timestamp=self.time.replace(tzinfo=UTC),
            pair=str(self._symbol),
            features=self._features(),
        )

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """Each bar: run the chain, act on its Decision, record one audit row."""
        if self._symbol not in data.quote_bars:
            return
        if self._trend_perception is not None:
            self._trend_perception.update(data.quote_bars[self._symbol])
        if not self._indicators_ready():
            return
        outcome = self._chain.run(self._state())
        action = decision_to_order_action(outcome.decision)
        self.debug(f"{self.log_tag}_DECISION|decision={outcome.decision}|action={action}")

        prior_quantity = self.portfolio[self._symbol].quantity
        fill = None
        if action == "execute":
            # Explicit chain.model.Decision -> engine.order_executor.Decision conversion:
            # separate StrEnum classes with the same values (chain/terminal.py).
            order_decision = OrderDecision(outcome.decision.value)
            fill = self.order_executor.execute(
                self._symbol, order_decision, SizingContext(size=self._size)
            )
        elif action == "stand_aside" and self.portfolio.invested:
            fill = self.order_executor.close(self._symbol)
        # action == "manage" (HOLD): leave any open position (and its trade_id) alone.
        if fill is not None and fill.status == FillStatus.FILLED and fill.order_id is not None:
            self._decisions.on_fill(
                str(fill.order_id), prior_quantity, self.portfolio[self._symbol].quantity
            )
        self._decisions.record(outcome)

    def on_end_of_algorithm(self) -> None:
        """Log closed-trade count + any still-open trade id; persist decisions.parquet.

        A trade still open when the backtest ends has no entry in LEAN's closed-trade
        ledger (trades.json), so its id is logged to keep every decisions.parquet
        trade_id accounted for.
        """
        closed = sum(1 for _ in self.trade_builder.closed_trades)
        self.debug(f"{self.log_tag}_CLOSED_TRADES={closed}")
        self.debug(f"{self.log_tag}_OPEN_TRADE_AT_END={self._decisions.current_trade_id}")
        self._decisions.write(Path(DECISIONS_FILE))
