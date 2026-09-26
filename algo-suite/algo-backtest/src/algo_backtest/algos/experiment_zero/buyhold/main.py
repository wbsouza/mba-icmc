# Experiment 0 — engine sanity check (docs/experiments.md #0, Spec 04h): buy-and-hold.
# Enter long once at the first available bar; never exit. This is not a trading strategy
# in the F1-F7 sense — it exists to validate the backtester itself before any F1-F7 number
# is trusted: FX pairs have no structural long-run drift, so buy-and-hold's Sharpe should
# land close to 0 (docs/experiments.md #0's expected sanity bound). A large positive or
# negative Sharpe here means the harness (fees, fills, metrics computation), not the
# strategy, is wrong.
#
# NOT VERIFIED against the real pinned LEAN container in the session that wrote this file
# (docs/technical-debt.md — see the Spec 04h entry): written to the same proven pattern as
# algos/baseline_ma and algos/baseline_meanrev (both real, already-run algorithms), but has
# not itself been run end-to-end. Treat a first real run as the acceptance step, not this
# code review alone.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)

from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision, SizingContext  # noqa: E402


class main(ExecutionAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Enter long on the first ready bar; hold to the end of the window (never exit)."""

    strategy_name = "buyhold"

    def initialize(self) -> None:
        """Read run parameters; subscribe to the pair (UTC clock)."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        symbol = self._required("symbol")
        start = self._required("start")
        end = self._required("end")
        self._size = float(self._required("size"))
        broker_adapter = self._required("broker_adapter")

        self.set_start_date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        self.set_end_date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        self.set_cash(100_000)
        self._symbol = self.add_forex(
            symbol, Resolution.MINUTE, Market.OANDA, False  # noqa: F405
        ).symbol
        self.init_execution(broker_adapter)

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """On the first bar with a quote for this symbol: enter long and never exit."""
        if self.portfolio.invested:
            return
        if self._symbol not in data.quote_bars:
            return
        self.order_executor.execute(self._symbol, Decision.BUY, SizingContext(size=self._size))

    def on_end_of_algorithm(self) -> None:
        """Emit the closed-trade count for log-based assertions (expected: 0 — never exits)."""
        self.debug(f"BUYHOLD_CLOSED_TRADES={len(self.trade_builder.closed_trades)}")
