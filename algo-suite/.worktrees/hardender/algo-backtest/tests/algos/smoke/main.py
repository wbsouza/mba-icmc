# Smoke algorithm: no data subscription — proves the testcontainers harness can run
# the pinned LEAN engine end to end and surface algorithm Debug() output in the logs.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)


class main(QCAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Minimal backtest that only spans a date range and emits sentinel log lines."""

    def initialize(self) -> None:
        """Set a tiny backtest window; subscribe to nothing."""
        self.set_start_date(2014, 5, 7)
        self.set_end_date(2014, 5, 8)
        self.set_cash(100_000)
        self.debug("SMOKE_INIT_OK")

    def on_end_of_algorithm(self) -> None:
        """Emit the sentinel the harness asserts on."""
        self.debug("SMOKE_END_OK")
