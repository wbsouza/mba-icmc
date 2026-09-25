"""ExecutionAlgorithm: the QCAlgorithm base wired to OrderExecutor and a
config-selected brokerage adapter (spec.md Sec 3.2, tasks.md Track A step 3).

Only runs inside the pinned LEAN container's Python (``AlgorithmImports`` is
LEAN's own injected bridge, not installable in the normal ``algo-backtest``
environment) — this module is the environmentally-unsuitable adapter boundary
itself, proven correct via ``tests/features/order_execution.feature`` against
the real container, not by plain unit tests.

Every strategy's ``main.py`` subclasses ``ExecutionAlgorithm`` and places every
order through ``self.order_executor`` (never a raw ``self.market_order`` /
``self.liquidate`` call), so every fill is normalized and every rejection is
recorded via ``OnOrderEvent``, never silently dropped.
"""

from __future__ import annotations

from AlgorithmImports import *  # noqa: F403  (LEAN injects its API into this namespace)
from engine.brokerage import build_brokerage_adapter  # noqa: E402
from engine.order_executor import OrderExecutor  # noqa: E402


class ExecutionAlgorithm(QCAlgorithm):  # noqa: F405
    """Base algorithm: brokerage-adapter selection + OrderExecutor wiring.

    ``strategy_name`` labels this algorithm's :meth:`_required` failures; each
    subclass overrides it (defaults to the class name so a strategy that forgets
    to set one still fails with a useful, non-generic label).
    """

    strategy_name: str = ""

    def _required(self, name: str) -> str:
        """Fetch a required run parameter, failing fast if the runner didn't inject it.

        Shared by every strategy so a runner regression that drops one parameter
        fails loudly, with the same wording, everywhere instead of per-algo copies.
        """
        value = self.get_parameter(name)
        if not value:
            label = self.strategy_name or type(self).__qualname__
            raise ValueError(f"{label} requires the '{name}' parameter (none supplied)")
        return value

    def init_execution(self, broker_adapter_name: str) -> None:
        """Apply the config-selected brokerage model and build the OrderExecutor.

        Called from a subclass's own ``initialize()``, after subscribing to its
        symbol(s). Raises ``UnknownBrokerageAdapterError`` before the first bar
        if ``broker_adapter_name`` names no registered adapter — a hard stop,
        never a silent default brokerage model (it changes fill economics).
        """
        build_brokerage_adapter(broker_adapter_name).apply(self)
        self.order_executor = OrderExecutor(self)

    def on_order_event(self, order_event: OrderEvent) -> None:  # noqa: F405
        """Forward every order event (fill or rejection) to the OrderExecutor."""
        self.order_executor.on_order_event(order_event)
