# Experiment 0 — engine sanity check (docs/experiments.md #0, Spec 04h): random entries.
# A seeded coin-flip decides direction on each bar where the algorithm is flat; a second
# seeded coin-flip (checked every bar while invested) decides when to exit. No edge, by
# construction — the point is to prove the backtester reports ~0 Sharpe and ~50% hit rate
# for a signal with no information content (docs/experiments.md #0's expected sanity
# bound), so a later F1-F7 strategy's Sharpe is judged against this floor, not against 0
# in the abstract. `seed` is a required parameter (not a silent default) so a sweep across
# seeds is reproducible per-run, per CLAUDE.md's fail-fast/reproducibility policy. The
# per-bar entry and exit probabilities and the long/short split (`entry_probability`,
# `exit_probability`, `long_probability`; 0.5 = unbiased coin) are run parameters too —
# every behaviour-affecting number is external (story 12), validated by run.py on the host.
#
# NOT VERIFIED against the real pinned LEAN container in the session that wrote this file
# (docs/technical-debt.md — see the Spec 04h entry): written to the same proven pattern as
# algos/baseline_ma and algos/baseline_meanrev (both real, already-run algorithms), but has
# not itself been run end-to-end. Treat a first real run as the acceptance step, not this
# code review alone.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)

import random  # noqa: E402

from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision, SizingContext  # noqa: E402

class main(ExecutionAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Seeded random long/short entries with no information content, by construction."""

    strategy_name = "random"

    def initialize(self) -> None:
        """Read run parameters (sizing, seed, cash, the three probabilities); subscribe to
        the pair; seed the RNG (UTC clock)."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        symbol = self._required("symbol")
        start = self._required("start")
        end = self._required("end")
        self._size = float(self._required("size"))
        seed = int(self._required("seed"))
        self._entry_probability = float(self._required("entry_probability"))
        self._exit_probability = float(self._required("exit_probability"))
        self._long_probability = float(self._required("long_probability"))
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
        self.debug(f"RANDOM_STARTING_CASH={cash}")
        self._symbol = self.add_forex(
            symbol, Resolution.MINUTE, Market.OANDA, False  # noqa: F405
        ).symbol
        self._rng = random.Random(seed)
        self.init_execution(broker_adapter)

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """Flat: enter with entry_probability, BUY with long_probability else SELL.
        Invested: exit with exit_probability."""
        if self._symbol not in data.quote_bars:
            return
        if not self.portfolio.invested:
            if self._rng.random() < self._entry_probability:
                long = self._rng.random() < self._long_probability
                direction = Decision.BUY if long else Decision.SELL
                self.order_executor.execute(self._symbol, direction, SizingContext(size=self._size))
        elif self._rng.random() < self._exit_probability:
            self.order_executor.close(self._symbol)

    def on_end_of_algorithm(self) -> None:
        """Emit the closed-trade count for log-based assertions."""
        self.debug(f"RANDOM_CLOSED_TRADES={len(self.trade_builder.closed_trades)}")
