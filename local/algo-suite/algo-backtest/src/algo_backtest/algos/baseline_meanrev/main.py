# Baseline strategy: SMA mean-reversion on one Forex pair, minute bars. Long-only, single
# position, fixed sizing. Counter-trend (the structural opposite of baseline-ma's crossover):
# buy when price dips a band below its SMA, exit when it reverts to the SMA. A second
# price-only baseline for the multi-strategy comparison — no news/sentiment signal.
# Parameters (symbol, window, band, sizing, starting cash, brokerage adapter) come from
# the run via get_parameter(). Order placement goes through OrderExecutor (Spec 04a), not a
# raw set_holdings/liquidate call, so every fill is normalized and every rejection recorded.
#
# Known limitation (deliberate, for an honest baseline): no stop-loss or time exit, so in a
# sustained downtrend the position can stay open until the window ends — the metrics expose
# that weakness rather than hiding it behind a protective exit.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)

from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision, SizingContext  # noqa: E402


class main(ExecutionAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Enter long when price < SMA*(1 - band); exit when price reverts to >= SMA."""

    strategy_name = "baseline-meanrev"

    def initialize(self) -> None:
        """Read run parameters; subscribe to the pair; wire the SMA (UTC clock).

        Parameters are required (no silent defaults) so a runner regression that drops one
        fails loudly rather than backtesting a different, hidden configuration.
        """
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        symbol = self._required("symbol")
        start = self._required("start")
        end = self._required("end")
        window = int(self._required("window"))
        self._band = float(self._required("band"))
        self._size = float(self._required("size"))
        cash = float(self._required("cash"))
        if cash <= 0:
            raise ValueError(
                f"{self.strategy_name}: cash ({cash}) must be positive — the account's starting "
                "deposit; run.py validates this on the host, so a non-positive value here means "
                "the algorithm was launched outside `algo-backtest run`"
            )
        broker_adapter = self._required("broker_adapter")

        self.set_start_date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        self.set_end_date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        self.set_cash(cash)
        self.debug(f"BASELINE_MEANREV_STARTING_CASH={cash}")
        self._symbol = self.add_forex(
            symbol, Resolution.MINUTE, Market.OANDA, False  # noqa: F405
        ).symbol
        self._sma = self.sma(self._symbol, window, Resolution.MINUTE)  # noqa: F405
        self.init_execution(broker_adapter)

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """On each bar: price below the lower band -> enter long; back at/above SMA -> exit."""
        if not self._sma.is_ready:
            return
        if self._symbol not in data.quote_bars:
            return
        price = data.quote_bars[self._symbol].close
        mean = self._sma.current.value
        if price < mean * (1 - self._band) and not self.portfolio.invested:
            self.order_executor.execute(self._symbol, Decision.BUY, SizingContext(size=self._size))
        elif price >= mean and self.portfolio.invested:
            self.order_executor.close(self._symbol)

    def on_end_of_algorithm(self) -> None:
        """Emit the closed-trade count for log-based assertions."""
        self.debug(f"BASELINE_CLOSED_TRADES={len(self.trade_builder.closed_trades)}")
