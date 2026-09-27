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

Story 12 (execution realism, item D): a BUY/SELL while flat becomes the trade F6 planned
(``state.features["trade_plan"]``, ``engine/trade_plan.py``): a market order sized from
the plan's lot size, a stop-market order at the stop distance and one limit order per
target; each later bar applies the trailing steps, an opposite signal closes only after
``execution.min_hold_bars``, a veto closes only when ``execution.close_on_veto``, and the
stop and targets are one-cancels-the-others (``on_order_event``). Every planned entry is
recorded to ``trade-plans.json`` next to ``decisions.parquet``.
"""

from __future__ import annotations

from datetime import UTC, date
from pathlib import Path

from algo_core.atomicio import write_text_atomic
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)
from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision as OrderDecision  # noqa: E402
from engine.order_executor import FillStatus  # noqa: E402

from algo_backtest.artifacts import write_strategy_config
from algo_backtest.chain.decision_recorder import DecisionRecorder
from algo_backtest.chain.filters.f4_news_context import NewsContextIndex
from algo_backtest.chain.filters.f7_model_io import load_model, require_families
from algo_backtest.chain.model import ChainOutcome, ExecutionState, FilterChain
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
from algo_backtest.container_paths import DECISIONS_FILE, TRADE_PLANS_FILE
from algo_backtest.engine.trade_plan import (
    PlannedPosition,
    TradePlanRecord,
    build_record,
    hold_elapsed,
    order_quantity,
    orders_to_cancel,
    parse_trade_plan,
    plans_json,
    round_to_lot_step,
    stop_price,
    stop_quantity_for,
    target_prices,
    target_quantities,
    trail_update,
)
from algo_backtest.perception.config import PerceptionConfig
from algo_backtest.rules.trail_stop import Direction
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
        if self._economics is None:
            raise ValueError(
                f"{self.strategy_name}: the executor sizes every order from F6's trade plan, "
                "so a chain strategy needs f6_capital_mgmt in filters: and a capital_mgmt: "
                "section in its config.yaml — add both (see strategies/baseline/config.yaml)"
            )
        self._execution = config.execution
        properties = self.securities[self._symbol].symbol_properties
        self._pip = self._pip_size()  # E's helper: ten pipettes per pip, from symbol properties
        self._lot_step = float(properties.lot_size)
        self._bar_index = 0
        self._position: PlannedPosition | None = None
        self._plans: list[TradePlanRecord] = []
        filters = build_filters(
            config,
            meta_learner=meta_learner,
            news_index=self._news_index(symbol, start, end),
        )
        self._chain = FilterChain(filters=filters, terminal=F7TerminalDecision())
        self._decisions = DecisionRecorder()
        self._pnl = PnlWindows()

        self.init_execution(
            broker_adapter,
            spread_pips=self._execution.spread_pips,
            commission_per_lot=self._execution.commission_per_lot,
            lot_notional_units=self._economics.lot_notional_units,
        )

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
        """Each bar: run the chain, manage the open plan, act on the Decision, record a row."""
        if self._symbol not in data.quote_bars:
            return
        if self._trend_perception is not None:
            self._trend_perception.update(data.quote_bars[self._symbol])
        if not self._indicators_ready():
            return
        self._bar_index += 1
        outcome = self._chain.run(self._state())
        action = decision_to_order_action(outcome.decision)
        self.debug(f"{self.log_tag}_DECISION|decision={outcome.decision}|action={action}")

        self._manage_open(self.securities[self._symbol].price)
        if action == "execute":
            self._on_signal(outcome)
        elif action == "stand_aside" and self.portfolio.invested and self._execution.close_on_veto:
            self._close_open("veto")
        # action == "manage" (HOLD): the plan's own orders and trailing steps run the trade.
        self._decisions.record(outcome)

    def on_order_event(self, order_event: OrderEvent) -> None:  # noqa: F405
        """Every fill: thread the audit trade id, then reconcile the plan's working orders.

        LEAN applies a fill to the portfolio before raising its event, so the position
        after the fill is the portfolio's and the position before it is that minus the
        signed fill quantity. Stop/target fills arrive between bars; the entry's own fill
        arrives synchronously inside `execute_quantity`, before the plan is remembered.
        """
        super().on_order_event(order_event)
        if order_event.status != OrderStatus.FILLED:  # noqa: F405
            return
        position = float(self.portfolio[self._symbol].quantity)
        prior = position - float(order_event.fill_quantity)
        self._decisions.on_fill(str(order_event.order_id), prior, position)
        self._reconcile_working_orders(int(order_event.order_id), position)

    def _on_signal(self, outcome: ChainOutcome) -> None:
        """A BUY/SELL: open the planned trade when flat; reverse only after the minimum hold."""
        direction = Direction(outcome.decision.value)
        if not self.portfolio.invested:
            self._open_planned(outcome, direction)
            return
        if self._position is not None and self._position.direction is direction:
            return  # same-side signal: one planned position at a time, manage only
        if self._position is not None and not hold_elapsed(
            self._position.entry_bar_index, self._bar_index, self._execution.min_hold_bars
        ):
            self.debug(
                f"{self.log_tag}_HOLD_GUARD|signal={direction}|since_entry="
                f"{self._bar_index - self._position.entry_bar_index}|"
                f"min_hold_bars={self._execution.min_hold_bars}"
            )
            return
        self._close_open("reversal")
        self._open_planned(outcome, direction)

    def _open_planned(self, outcome: ChainOutcome, direction: Direction) -> None:
        """Market entry sized from the plan, then its stop and take-profit orders."""
        plan = parse_trade_plan(outcome.state.features)
        side = plan.for_direction(direction)
        quantity = round_to_lot_step(
            order_quantity(plan.lot_size, self._economics.lot_notional_units, direction),
            self._lot_step,
        )
        if quantity == 0:
            raise ValueError(
                f"{self.strategy_name}: the plan's {plan.lot_size} lots round to zero units at "
                f"lot step {self._lot_step}; raise capital_mgmt.risk_per_trade or lower the stop"
            )
        fill = self.order_executor.execute_quantity(
            self._symbol, OrderDecision(direction.value), quantity
        )
        if fill.status != FillStatus.FILLED or fill.fill_price is None or fill.order_id is None:
            self.debug(f"{self.log_tag}_PLAN_REJECTED|reason={fill.rejection_reason}")
            return
        position = float(self.portfolio[self._symbol].quantity)
        entry = fill.fill_price
        stop = stop_price(entry, side.stop_pips, self._pip, direction)
        stop_id = self.order_executor.place_stop(
            self._symbol, stop_quantity_for(position), stop, "plan-stop"
        )
        levels = target_prices(entry, side.targets, self._pip, direction)
        exits = target_quantities(position, side.targets, self._lot_step)
        placed = [
            (price, fraction, exit_quantity)
            for (price, fraction), exit_quantity in zip(levels, exits, strict=True)
        ]
        target_ids = tuple(
            self.order_executor.place_limit(self._symbol, qty, price, f"plan-target-{i + 1}")
            for i, (price, _fraction, qty) in enumerate(placed)
        )
        self._position = PlannedPosition(
            direction=direction, plan=side, entry_price=entry, entry_bar_index=self._bar_index,
            entry_order_id=fill.order_id, stop_order_id=stop_id, target_order_ids=target_ids,
            current_stop=stop,
        )
        self._plans.append(
            build_record(
                entry_order_id=fill.order_id, entry_time=self.utc_time.isoformat(),
                direction=direction, lots=plan.lot_size, quantity=position, entry_price=entry,
                stop_loss=stop, targets=placed, plan=side, pip_size=self._pip,
                spread_pips=plan.spread_pips,
            )
        )
        self.debug(
            f"{self.log_tag}_PLAN|entry={entry}|lots={plan.lot_size}|quantity={position}|"
            f"stop={stop}|targets={[(price, qty) for price, _f, qty in placed]}"
        )

    def _manage_open(self, price: float) -> None:
        """Apply the trailing steps to the open planned position (if any) at `price`."""
        position = self._position
        if position is None or not self.portfolio.invested:
            return
        move = trail_update(
            position.entry_price, price, position.current_stop, position.plan.trail_stops,
            self._pip, position.direction, fired=position.fired,
        )
        if move is None:
            return
        previous = position.current_stop
        position.apply(move)
        if move.new_stop is not None:
            self.order_executor.update_stop_price(position.stop_order_id, move.new_stop)
            self.debug(
                f"{self.log_tag}_TRAIL|entry={position.entry_price}|from={previous}|"
                f"to={move.new_stop}|steps={list(move.fired)}"
            )

    def _close_open(self, reason: str) -> None:
        """Cancel the plan's working orders, then liquidate the position."""
        working = [order.order_id for order in self.order_executor.open_orders(self._symbol)]
        if working:
            self.order_executor.cancel(working)
            self.debug(f"{self.log_tag}_OCO_CANCEL|reason={reason}|orders={working}")
        self._position = None
        self.order_executor.close(self._symbol)

    def _reconcile_working_orders(self, order_id: int, position: float) -> None:
        """OCO emulation after a stop/target fill: flat cancels the rest, a partial exit
        resizes the stop to what is still open."""
        planned = self._position
        if planned is None or order_id == planned.entry_order_id:
            return
        if position == 0:
            to_cancel = orders_to_cancel(position, self.order_executor.open_orders(self._symbol))
            if to_cancel:
                self.order_executor.cancel(to_cancel)
                self.debug(f"{self.log_tag}_OCO_CANCEL|reason=flat|orders={list(to_cancel)}")
            self._position = None
            return
        if order_id in planned.target_order_ids:
            resized = stop_quantity_for(position)
            self.order_executor.update_quantity(planned.stop_order_id, resized)
            self.debug(f"{self.log_tag}_STOP_RESIZE|order={planned.stop_order_id}|quantity={resized}")

    def on_end_of_algorithm(self) -> None:
        """Log closed-trade count + any still-open trade id; persist decisions.parquet and
        trade-plans.json (one record per planned entry).

        A trade still open when the backtest ends has no entry in LEAN's closed-trade
        ledger (trades.json), so its id is logged to keep every decisions.parquet
        trade_id accounted for.
        """
        closed = sum(1 for _ in self.trade_builder.closed_trades)
        self.debug(f"{self.log_tag}_CLOSED_TRADES={closed}")
        self.debug(f"{self.log_tag}_OPEN_TRADE_AT_END={self._decisions.current_trade_id}")
        self._decisions.write(Path(DECISIONS_FILE))
        write_text_atomic(Path(TRADE_PLANS_FILE), plans_json(self._plans))
