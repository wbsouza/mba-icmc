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
``decisions.parquet`` row whose ``trade_id`` follows LEAN's own trade grouping
(``DecisionRecorder.on_fill``), written once at end of algorithm.
"""

from __future__ import annotations

from datetime import UTC, date
from pathlib import Path

from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)
from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision as OrderDecision  # noqa: E402
from engine.order_executor import FillStatus, SizingContext  # noqa: E402

from algo_backtest.chain.decision_recorder import DecisionRecorder
from algo_backtest.chain.filters.f4_news_context import NewsContextIndex
from algo_backtest.chain.filters.f7_model_io import load_model
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
from algo_backtest.strategies import load_strategy_chain_config


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
        symbol = self._required("symbol")
        start = parse_yyyymmdd(self._required("start"))
        end = parse_yyyymmdd(self._required("end"))
        self._size = float(self._required("size"))
        broker_adapter = self._required("broker_adapter")

        self.set_start_date(start.year, start.month, start.day)
        self.set_end_date(end.year, end.month, end.day)
        self._symbol = self.add_forex(symbol, Resolution.MINUTE, Market.OANDA).symbol  # noqa: F405
        self._subscribe_indicators()

        meta_learner = load_model(self.model_path)
        self.debug(f"{self.log_tag}_MODEL_SHA256={file_sha256(self.model_path)}")
        filters = build_filters(
            load_strategy_chain_config(self.strategy_name).filters,
            meta_learner=meta_learner,
            news_index=self._news_index(symbol, start, end),
        )
        self._chain = FilterChain(filters=filters, terminal=F7TerminalDecision())
        self._decisions = DecisionRecorder()
        self._pnl = PnlWindows()

        self.init_execution(broker_adapter)

    def _subscribe_indicators(self) -> None:
        """The minute indicators behind ``wiring.price_features``."""
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
        return all(indicator.is_ready for indicator in indicators)

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
        return {**market, **account_features(account, price)}

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """Each bar: run the chain, act on its Decision, record one audit row."""
        if not self._indicators_ready() or self._symbol not in data.quote_bars:
            return
        state = ExecutionState(
            timestamp=self.time.replace(tzinfo=UTC),
            pair=str(self._symbol),
            features=self._features(),
        )
        outcome = self._chain.run(state)
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
