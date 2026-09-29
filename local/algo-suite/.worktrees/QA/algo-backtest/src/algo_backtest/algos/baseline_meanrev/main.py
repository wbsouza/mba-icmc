# Baseline strategy: SMA mean-reversion on one Forex pair, minute bars. Long-only, single
# position, fixed sizing. Counter-trend (the structural opposite of baseline-ma's crossover):
# buy when price dips a band below its SMA, exit when it reverts to the SMA. A second
# price-only baseline for the multi-strategy comparison — no news/sentiment signal.
# Parameters (symbol, window, band, sizing) come from the run via get_parameter().
#
# Known limitation (deliberate, for an honest baseline): no stop-loss or time exit, so in a
# sustained downtrend the position can stay open until the window ends — the metrics expose
# that weakness rather than hiding it behind a protective exit.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)


class main(QCAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Enter long when price < SMA*(1 - band); exit when price reverts to >= SMA."""

    def _required(self, name: str) -> str:
        """Fetch a required run parameter, failing fast if the runner didn't inject it."""
        value = self.get_parameter(name)
        if not value:
            raise ValueError(f"baseline-meanrev requires the '{name}' parameter (none supplied)")
        return value

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

        self.set_start_date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        self.set_end_date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        self.set_cash(100_000)
        self._symbol = self.add_forex(
            symbol, Resolution.MINUTE, Market.OANDA, False  # noqa: F405
        ).symbol
        self._sma = self.sma(self._symbol, window, Resolution.MINUTE)  # noqa: F405

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """On each bar: price below the lower band -> enter long; back at/above SMA -> exit."""
        if not self._sma.is_ready:
            return
        if self._symbol not in data.quote_bars:
            return
        price = data.quote_bars[self._symbol].close
        mean = self._sma.current.value
        if price < mean * (1 - self._band) and not self.portfolio.invested:
            self.set_holdings(self._symbol, self._size)
        elif price >= mean and self.portfolio.invested:
            self.liquidate(self._symbol)

    def on_end_of_algorithm(self) -> None:
        """Emit the closed-trade count for log-based assertions."""
        self.debug(f"BASELINE_CLOSED_TRADES={len(self.trade_builder.closed_trades)}")
