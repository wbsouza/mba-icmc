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

from datetime import UTC, date
from pathlib import Path

from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)
from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision as OrderDecision  # noqa: E402
from engine.order_executor import FillStatus, SizingContext  # noqa: E402

from algo_backtest.artifacts import write_strategy_config
from algo_backtest.chain.decision_recorder import DecisionRecorder
from algo_backtest.chain.filters.f4_news_context import NewsContextIndex
from algo_backtest.chain.filters.f7_model_io import load_model, require_families
from algo_backtest.chain.model import ExecutionState, FilterChain
from algo_backtest.chain.price_features import PriceFeatureConfig
from algo_backtest.chain.terminal import F7TerminalDecision, decision_to_order_action
from algo_backtest.chain.wiring import (
    AccountSnapshot,
    PnlWindows,
    account_features,
    build_filters,
    file_sha256,
    parse_yyyymmdd,
    pip_size_from_price_variation,
    price_features,
)
from algo_backtest.container_paths import DECISIONS_FILE
from algo_backtest.perception.config import PerceptionConfig
from algo_backtest.strategies import load_resolved_strategy


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
        cash = float(self._required("cash"))
        if cash <= 0:
            raise ValueError(
                f"{self.strategy_name}: cash ({cash}) must be positive — the account's starting "
                "deposit; run.py validates this on the host, so a non-positive value here means "
                "the algorithm was launched outside `algo-backtest run`"
            )
        broker_adapter = self._required("broker_adapter")
        self.set_cash(cash)
        self.debug(f"{self.log_tag}_STARTING_CASH={cash}")

        self.set_start_date(start.year, start.month, start.day)
        self.set_end_date(end.year, end.month, end.day)
        self._symbol = self.add_forex(symbol, Resolution.MINUTE, Market.OANDA).symbol  # noqa: F405
        # The host run path ships the fully resolved strategy YAML next to main.py
        # (run.py `_RESOLVED_STRATEGY_FILE`), so the container never depends on the
        # package's bundled strategies/ or on an external --strategies-dir.
        config = load_resolved_strategy(
            self.model_path.parent / "strategy.yaml",
            name=self.get_parameter("chain_config") or self.strategy_name,
        )
        self._subscribe_indicators(config.perception, config.price_features)
        self.debug(f"{self.log_tag}_PERCEPTION_SOURCE={config.perception.source}")
        write_strategy_config(Path(DECISIONS_FILE).parent, config)

        meta_learner = load_model(self.model_path)
        self.debug(f"{self.log_tag}_MODEL_SHA256={file_sha256(self.model_path)}")
        require_families(
            meta_learner.families, config.meta_learner_families, where=str(self.model_path)
        )
        self._economics = config.capital_mgmt
        filters = build_filters(
            config,
            meta_learner=meta_learner,
            news_index=self._news_index(symbol, start, end),
        )
        self._chain = FilterChain(filters=filters, terminal=F7TerminalDecision())
        self._decisions = DecisionRecorder()
        self._pnl = PnlWindows()

        self.init_execution(broker_adapter)

    def _subscribe_indicators(
        self,
        perception: PerceptionConfig | None = None,
        price_features_config: PriceFeatureConfig | None = None,
    ) -> None:
        """Subscribe EMA/RSI/MACD/ATR and the swing Minimum/Maximum with the strategy's
        periods and, when selected, construct the native HA perception. Omitted arguments
        mean the documented defaults."""
        perception = perception if perception is not None else PerceptionConfig()
        periods = price_features_config or PriceFeatureConfig()
        self._trend_perception = None
        if perception.source == "double_smoothed_heikin_ashi":
            from algo_backtest.perception.multi_timeframe import MultiTimeframeHeikinAshi

            self._trend_perception = MultiTimeframeHeikinAshi(
                period1=perception.period1, period2=perception.period2,
                higher_tf_minutes=perception.higher_tf_minutes,
            )
        minute = Resolution.MINUTE  # noqa: F405
        self._ema_fast = self.ema(self._symbol, periods.ema_fast, minute)
        self._ema_slow = self.ema(self._symbol, periods.ema_slow, minute)
        self._ema_htf = self.ema(self._symbol, periods.ema_higher_tf, minute)
        self._rsi = self.rsi(self._symbol, periods.rsi_period, MovingAverageType.WILDERS, minute)  # noqa: F405
        self._macd = self.macd(
            self._symbol, periods.macd_fast, periods.macd_slow, periods.macd_signal,
            MovingAverageType.EXPONENTIAL, minute,  # noqa: F405
        )
        self._atr = self.atr(self._symbol, periods.atr_period, MovingAverageType.WILDERS, minute)  # noqa: F405
        # Field.LOW / Field.HIGH: a forex subscription is QuoteBars, for which LEAN's
        # default MIN/MAX selector would be the close (Value), not the bar's low/high.
        lookback = periods.swing_lookback_bars
        self._swing_low = self.min(self._symbol, lookback, minute, Field.LOW)  # noqa: F405
        self._swing_high = self.max(self._symbol, lookback, minute, Field.HIGH)  # noqa: F405

    def _pip_size(self) -> float:
        """The pair's pip in price units, from the security's symbol properties.

        LEAN's ``minimum_price_variation`` is the pipette (0.00001 on EURUSD, 0.001 on
        USDJPY); ``pip_size_from_price_variation`` applies the ten-pipettes-per-pip
        convention, giving the same value as the offline ``Instrument.unit_size`` that
        ``training.build_training_rows(instrument=...)`` uses.
        """
        properties = self.securities[self._symbol].symbol_properties
        return pip_size_from_price_variation(float(properties.minimum_price_variation))

    def _indicators_ready(self) -> bool:
        """Whether every indicator the features contract reads has warmed up."""
        indicators = (
            self._ema_fast, self._ema_slow, self._ema_htf, self._rsi, self._macd, self._atr,
            self._swing_low, self._swing_high,
        )
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
        pip = self._pip_size()
        market = price_features(
            price=price,
            ema_fast=self._ema_fast.current.value,
            ema_slow=self._ema_slow.current.value,
            ema_htf=self._ema_htf.current.value,
            rsi=self._rsi.current.value,
            macd_hist=self._macd.current.value - self._macd.signal.current.value,
            atr_pips=self._atr.current.value / pip,
            swing_low_pips=(price - self._swing_low.current.value) / pip,
            swing_high_pips=(self._swing_high.current.value - price) / pip,
        )
        if self._trend_perception is not None:
            market.update(self._trend_perception.features())
        return {**market, **account_features(account, price, self._economics)}

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
