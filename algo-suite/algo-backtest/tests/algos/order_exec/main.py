# Order-execution-engine test algorithm (Spec 04a, tests/features/order_execution.feature).
# Fully parameterized so each scenario controls exactly what OrderExecutor does, rather than
# depending on a real price signal (unlike baseline_ma/baseline_meanrev). Emits parseable
# ORDEREXEC_* debug lines the step defs assert on, mirroring the probe algo's PROBE_BAR style.
from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)

from engine.algorithm import ExecutionAlgorithm  # noqa: E402
from engine.order_executor import Decision, FillStatus, SizingContext  # noqa: E402

_ACT_ON_BAR = 3  # let the subscription warm up before acting, mirrors probe's pattern
_CLOSE_ON_BAR = _ACT_ON_BAR + 3  # a few bars later, so BUY/SELL become one closed trade


class main(ExecutionAlgorithm):  # noqa: F405  (algorithm-type-name = "main")
    """Places one parameterized Decision (optionally after opening a position first)."""

    def _required(self, name: str) -> str:
        value = self.get_parameter(name)
        if not value:
            raise ValueError(f"order_exec requires the '{name}' parameter (none supplied)")
        return value

    def _optional_float(self, name: str) -> float | None:
        value = self.get_parameter(name)
        return float(value) if value else None

    def initialize(self) -> None:
        """Subscribe EURUSD; apply the (possibly invalid) brokerage adapter; read the
        decision to place. `init_execution` runs before the first bar, so an unknown
        adapter raises here — LEAN fails the backtest before OnData ever fires (order
        _execution-07's "refuses to start before the first bar").
        """
        self.set_time_zone(TimeZones.UTC)  # noqa: F405
        start = self._required("start")
        end = self._required("end")
        self.set_start_date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        self.set_end_date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        self.set_cash(100_000)
        self._symbol = self.add_forex(
            "EURUSD", Resolution.MINUTE, Market.OANDA, False  # noqa: F405
        ).symbol

        self._decision = Decision(self._required("decision"))
        self._size = float(self.get_parameter("size") or "1.0")
        self._open_position_first = (self.get_parameter("open_position_first") or "") == "true"
        self._stop_loss = self._optional_float("stop_loss")
        self._take_profit = self._optional_float("take_profit")
        self._acted = False
        self._opened = False
        self._needs_close = False
        self._closed = False
        self._bar_count = 0

        broker_adapter = self._required("broker_adapter")
        self.init_execution(broker_adapter)
        self.debug(f"ORDEREXEC_BROKERAGE|adapter={broker_adapter}")

    def on_data(self, data: Slice) -> None:  # noqa: F405
        """On the `_ACT_ON_BAR`th ready bar: optionally open a position, then execute
        the parameterized decision exactly once.
        """
        if self._symbol not in data.quote_bars:
            return
        self._bar_count += 1
        if self._bar_count < _ACT_ON_BAR:
            return

        if self._open_position_first and not self._opened:
            self.order_executor.execute(self._symbol, Decision.BUY, SizingContext(size=self._size))
            self._opened = True
            return

        if not self._acted:
            self._acted = True
            sizing = SizingContext(
                size=self._size, stop_loss=self._stop_loss, take_profit=self._take_profit
            )
            fill = self.order_executor.execute(self._symbol, self._decision, sizing)
            self.debug(
                "ORDEREXEC_FILL|"
                f"decision={fill.decision.value}|status={fill.status.value}|"
                f"direction={fill.direction}|stop_loss={fill.stop_loss}|"
                f"take_profit={fill.take_profit}|reason={fill.rejection_reason}"
            )
            # A directional fill needs a later exit to register as one closed trade
            # (LEAN's trade_builder only counts round-trips, not open positions).
            self._needs_close = (
                fill.status == FillStatus.FILLED and self._decision in (Decision.BUY, Decision.SELL)
            )
            return

        if self._needs_close and not self._closed and self._bar_count >= _CLOSE_ON_BAR:
            self.order_executor.close(self._symbol)
            self._closed = True

    def on_end_of_algorithm(self) -> None:
        """Emit the closed-trade count and open-position state for log-based assertions."""
        self.debug(f"ORDEREXEC_CLOSED_TRADES={len(self.trade_builder.closed_trades)}")
        self.debug(f"ORDEREXEC_INVESTED={self.portfolio.invested}")
