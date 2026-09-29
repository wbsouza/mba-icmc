# Timezone-probe algorithm. Algo timezone is forced to UTC; for every EURUSD minute
# QuoteBar it reads back, it logs the bar's start (time) and end (end_time) so the
# integration test can assert the UTC round-trip against the original materialized bars.
# Date range comes from backtest parameters (start/end, YYYYMMDD) so one file serves
# both the summer and winter cases.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)


class main(QCAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Log algo-UTC start/end of each EURUSD minute bar, plus the algorithm timezone."""

    def initialize(self) -> None:
        """Force UTC algo tz, span the parameterized range, subscribe to EURUSD minute."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        start = self.get_parameter("start")
        end = self.get_parameter("end")
        if not start or not end:
            raise ValueError("PROBE requires 'start' and 'end' YYYYMMDD parameters")
        self.set_start_date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        self.set_end_date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        self.set_cash(100_000)
        self._symbol = self.add_forex(
            "EURUSD", Resolution.MINUTE, Market.OANDA, False  # noqa: F405
        ).symbol
        self._count = 0
        self.debug(f"PROBE_TZ|{self.time_zone}")

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """Emit one PROBE_BAR line per EURUSD minute bar.

        `utc` is the algorithm's UTC clock at delivery (= the bar's UTC EndTime — the
        authoritative round-trip observable). `bidc`/`askc` are the bid/ask close prices
        (payload fidelity: a column or bid/ask-side swap shows up here). `exch` is the
        bar's exchange-tz EndTime (New York for forex), logged to make the tz visible.
        """
        if self._symbol not in data.quote_bars:
            return
        bar = data.quote_bars[self._symbol]
        self._count += 1
        self.debug(
            f"PROBE_BAR|utc={self.utc_time.isoformat()}|exch={bar.end_time.isoformat()}"
            f"|bidc={bar.bid.close}|askc={bar.ask.close}"
        )

    def on_end_of_algorithm(self) -> None:
        """Emit the total bar count for a sanity assertion."""
        self.debug(f"PROBE_DONE|count={self._count}")
