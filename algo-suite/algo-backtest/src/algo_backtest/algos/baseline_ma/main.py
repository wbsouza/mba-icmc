# Baseline strategy: a simple fast/slow SMA crossover on one Forex pair, minute bars.
# Long-only, single position, fixed sizing. Deliberately minimal — the price-only
# baseline against which the hybrid (news/sentiment) strategy is compared. Parameters
# (symbol, window, fast/slow periods, sizing, brokerage adapter) come from the run via
# get_parameter(). Order placement goes through OrderExecutor (Spec 04a), not a raw
# set_holdings/liquidate call, so every fill is normalized and every rejection recorded.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)

from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision, SizingContext  # noqa: E402


class main(ExecutionAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Enter long when fast SMA > slow SMA; exit when it crosses back below."""

    strategy_name = "baseline-ma"

    def initialize(self) -> None:
        """Read run parameters; subscribe to the pair; wire the two SMAs (UTC clock).

        Parameters are required (no silent defaults) so a runner regression that drops
        one fails loudly rather than backtesting a different, hidden configuration.
        Defaults live in the CLI, not here.
        """
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        symbol = self._required("symbol")
        start = self._required("start")
        end = self._required("end")
        fast = int(self._required("fast"))
        slow = int(self._required("slow"))
        self._size = float(self._required("size"))
        broker_adapter = self._required("broker_adapter")

        self.set_start_date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        self.set_end_date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        self.set_cash(100_000)
        self._symbol = self.add_forex(
            symbol, Resolution.MINUTE, Market.OANDA, False  # noqa: F405
        ).symbol
        self._fast = self.sma(self._symbol, fast, Resolution.MINUTE)  # noqa: F405
        self._slow = self.sma(self._symbol, slow, Resolution.MINUTE)  # noqa: F405
        self.init_execution(broker_adapter)

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """On each bar: cross up -> enter long (fixed size); cross down -> exit."""
        if not (self._fast.is_ready and self._slow.is_ready):
            return
        if self._symbol not in data.quote_bars:
            return
        fast_above = self._fast.current.value > self._slow.current.value
        if fast_above and not self.portfolio.invested:
            self.order_executor.execute(self._symbol, Decision.BUY, SizingContext(size=self._size))
        elif not fast_above and self.portfolio.invested:
            self.order_executor.close(self._symbol)

    def on_end_of_algorithm(self) -> None:
        """Emit the closed-trade count for log-based assertions."""
        self.debug(f"BASELINE_CLOSED_TRADES={len(self.trade_builder.closed_trades)}")
