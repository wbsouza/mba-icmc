# Experiment 0 — engine sanity check (docs/experiments.md #0, Spec 04h): perfect-foresight
# oracle. Deliberately cheats: at initialize() it pulls the *entire* backtest window's
# history up front via self.history(...) and, for every bar, precomputes whether the
# *next* bar's close is higher or lower — then on_data() trades that known-in-advance
# direction. This is not a strategy candidate; it exists to prove the backtester's upper
# bound (very high Sharpe, ~0 drawdown, docs/experiments.md #0's expected sanity bound) —
# a hybrid strategy's real Sharpe is judged against buyhold/random on the low end and this
# oracle on the high end, not against an abstract number. Looking at "future" data this way
# is legitimate *only* for this validation algorithm (self.history() reads canonical data
# for a concrete date range, independent of simulated clock, and this file's only job is a
# one-time sanity bound before any F1-F7 number is trusted) — never a pattern to copy into
# a real strategy, which must never see beyond the current bar.
#
# NOT VERIFIED against the real pinned LEAN container in the session that wrote this file
# (docs/technical-debt.md — see the Spec 04h entry): the self.history() DataFrame shape
# assumed below follows QuantConnect's documented Python History() contract but has not
# been exercised against the real engine; treat a first real run (and its DataFrame
# indexing) as the acceptance step, not this code review alone.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)

from datetime import datetime  # noqa: E402

from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision, SizingContext  # noqa: E402


class main(ExecutionAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Trade the known-in-advance next-bar direction (oracle; never a real strategy)."""

    strategy_name = "perfect_foresight"

    def initialize(self) -> None:
        """Read run parameters; subscribe to the pair; precompute every bar's future
        direction from a full-window history pull (UTC clock)."""
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        symbol = self._required("symbol")
        start = self._required("start")
        end = self._required("end")
        self._size = float(self._required("size"))
        cash = float(self._required("cash"))
        if cash <= 0:
            raise ValueError(
                f"{self.strategy_name}: cash ({cash}) must be positive — the account's starting "
                "deposit; run.py validates this on the host, so a non-positive value here means "
                "the algorithm was launched outside `algo-backtest run`"
            )
        broker_adapter = self._required("broker_adapter")

        start_date = datetime(int(start[:4]), int(start[4:6]), int(start[6:8]))
        end_date = datetime(int(end[:4]), int(end[4:6]), int(end[6:8]))
        self.set_start_date(start_date)
        self.set_end_date(end_date)
        self.set_cash(cash)
        self.debug(f"PERFECT_FORESIGHT_STARTING_CASH={cash}")
        self._symbol = self.add_forex(
            symbol, Resolution.MINUTE, Market.OANDA, False  # noqa: F405
        ).symbol
        self.init_execution(broker_adapter)
        self._future_direction = self._precompute_future_directions(start_date, end_date)

    def _precompute_future_directions(
        self, start_date: datetime, end_date: datetime
    ) -> dict[datetime, int]:
        """Pull the whole window's close history and map each bar's timestamp to the sign
        of the *next* bar's close change: ``+1`` up, ``-1`` down, ``0`` unchanged/last bar."""
        history = self.history(self._symbol, start_date, end_date, Resolution.MINUTE)  # noqa: F405
        if history.empty:
            return {}
        closes = history["close"].droplevel(0) if hasattr(history.index, "nlevels") else history["close"]
        directions: dict[datetime, int] = {}
        timestamps = list(closes.index)
        values = list(closes.to_numpy())
        for i in range(len(values) - 1):
            change = values[i + 1] - values[i]
            directions[timestamps[i]] = 1 if change > 0 else -1 if change < 0 else 0
        return directions

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """Go long/short by the precomputed next-bar direction; flat when unchanged."""
        if self._symbol not in data.quote_bars:
            return
        direction = self._future_direction.get(self.time, 0)
        wants_long = direction > 0
        wants_short = direction < 0
        if self.portfolio.invested:
            holds_long = self.portfolio[self._symbol].is_long
            if (holds_long and not wants_long) or (not holds_long and not wants_short):
                self.order_executor.close(self._symbol)
        if not self.portfolio.invested:
            if wants_long:
                self.order_executor.execute(
                    self._symbol, Decision.BUY, SizingContext(size=self._size)
                )
            elif wants_short:
                self.order_executor.execute(
                    self._symbol, Decision.SELL, SizingContext(size=self._size)
                )

    def on_end_of_algorithm(self) -> None:
        """Emit the closed-trade count for log-based assertions."""
        self.debug(f"PERFECT_FORESIGHT_CLOSED_TRADES={len(self.trade_builder.closed_trades)}")
