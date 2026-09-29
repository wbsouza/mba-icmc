# Integration probe (trade_grouping.feature): replays a scale-in, partial exits and a
# reversal through the production ledger policy + DecisionRecorder, logging the
# recorder's current trade id after every fill and LEAN's closed trades at the end.
from algo_backtest.chain.decision_recorder import DecisionRecorder
from AlgorithmImports import *  # noqa: F403
from engine.chain_algorithm import use_flat_to_flat_trades  # noqa: E402

_ORDERS = [10_000, 5_000, -10_000, -5_000, 10_000, -20_000, 10_000]


class main(QCAlgorithm):  # noqa: F405, N801
    """Place `_ORDERS` one per bar; log recorder state and the closed-trade ledger."""

    def initialize(self) -> None:
        """Single-day EURUSD minute run with the production trade-grouping policy."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        use_flat_to_flat_trades(self)
        day = self.get_parameter("day")
        self.set_start_date(int(day[:4]), int(day[4:6]), int(day[6:8]))
        self.set_end_date(int(day[:4]), int(day[4:6]), int(day[6:8]))
        self._symbol = self.add_forex("EURUSD", Resolution.MINUTE, Market.OANDA).symbol  # noqa: F405
        self._step = 0
        self._recorder = DecisionRecorder()

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """One order per bar while orders remain."""
        if self._symbol not in data.quote_bars or self._step >= len(_ORDERS):
            return
        prior = self.portfolio[self._symbol].quantity
        ticket = self.market_order(self._symbol, _ORDERS[self._step])
        self._step += 1
        self._recorder.on_fill(
            str(ticket.order_id), prior, self.portfolio[self._symbol].quantity
        )
        self.debug(
            f"GROUPING_STEP|{self.utc_time}|{ticket.order_id}|"
            f"{self._recorder.current_trade_id}"
        )

    def on_end_of_algorithm(self) -> None:
        """Log every closed trade's order ids and entry/exit instants."""
        for trade in self.trade_builder.closed_trades:
            ids = ",".join(str(i) for i in trade.order_ids)
            self.debug(f"GROUPING_TRADE|{ids}|{trade.entry_time}|{trade.exit_time}")
