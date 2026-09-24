# One-shot algorithm: forces a single round-trip trade on EUR/USD so the harness can
# prove the run -> /Results path end to end (one closed trade), independent of any
# real strategy logic. Enters on the first bar, liquidates a few bars later.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)


class main(QCAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Buy EUR/USD on the first bar, liquidate after a few bars -> one closed trade."""

    def initialize(self) -> None:
        """Span a single sample day; subscribe to EUR/USD minute (UTC algo clock)."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        self.set_start_date(2014, 5, 7)
        self.set_end_date(2014, 5, 8)
        self.set_cash(100_000)
        self._symbol = self.add_forex(
            "EURUSD", Resolution.MINUTE, Market.OANDA, False  # noqa: F405
        ).symbol
        self._bars = 0
        self._entered = False

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """Enter on the first bar; liquidate on the fifth (one closed round-trip)."""
        if self._symbol not in data.quote_bars:
            return
        self._bars += 1
        if self._bars == 1:
            self.set_holdings(self._symbol, 0.5)
            self._entered = True
        elif self._bars == 5 and self.portfolio.invested:
            self.liquidate(self._symbol)

    def on_end_of_algorithm(self) -> None:
        """Emit the closed-trade count; flag explicitly if no bar ever arrived to trade on."""
        if not self._entered:
            self.debug("ONESHOT_ERROR=never_entered (no EURUSD bars in the run window)")
        stats = self.trade_builder.closed_trades
        self.debug(f"ONESHOT_CLOSED_TRADES={len(stats)}")
