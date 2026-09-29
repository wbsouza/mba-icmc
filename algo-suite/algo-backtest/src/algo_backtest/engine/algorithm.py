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
from engine.fill_models import apply_fill_costs  # noqa: E402
from engine.order_executor import OrderExecutor  # noqa: E402


class ExecutionAlgorithm(QCAlgorithm):  # noqa: F405
    """Base algorithm: brokerage-adapter selection + OrderExecutor wiring.

    ``strategy_name`` labels this algorithm's :meth:`_required` failures; each
    subclass overrides it (defaults to the class name so a strategy that forgets
    to set one still fails with a useful, non-generic label). ``log_tag`` prefixes
    the grep-able ``<TAG>_...`` debug lines (``ChainAlgorithm`` sets it per strategy);
    when empty the label falls back to ``strategy_name``, then the class name.
    """

    strategy_name: str = ""
    log_tag: str = ""

    def _label(self) -> str:
        """The tag naming this algorithm in failures and ``<TAG>_...`` log lines."""
        return self.log_tag or self.strategy_name or type(self).__qualname__

    def _required(self, name: str) -> str:
        """Fetch a required run parameter, failing fast if the runner didn't inject it.

        Shared by every strategy so a runner regression that drops one parameter
        fails loudly, with the same wording, everywhere instead of per-algo copies.
        """
        value = self.get_parameter(name)
        if not value:
            raise ValueError(f"{self._label()} requires the '{name}' parameter (none supplied)")
        return value

    def init_execution(
        self,
        broker_adapter_name: str,
        *,
        spread_pips: float = 0.0,
        commission_per_lot: float = 0.0,
        lot_notional_units: float | None = None,
        pip_size: float | None = None,
    ) -> None:
        """Apply the brokerage model, then the configured fill costs, then build the executor.

        Called from a subclass's own ``initialize()``, after subscribing to its
        symbol(s). Raises ``UnknownBrokerageAdapterError`` before the first bar
        if ``broker_adapter_name`` names no registered adapter — a hard stop,
        never a silent default brokerage model (it changes fill economics).

        The keyword arguments are the strategy YAML's ``execution`` section (story 12):
        a positive ``spread_pips`` installs a half-spread-per-side slippage model and a
        positive ``commission_per_lot`` a per-lot fee model on every subscribed security
        (``engine/fill_models.py``), each logged as one ``<TAG>_FILL_COSTS|model=...``
        line. Zero (the default) keeps the brokerage adapter's own model for that cost.
        ``pip_size`` is derived per security from LEAN's ``minimum_price_variation``
        (pip = 10 × tick for fractional-pip FX quotes, ``costs.pip_size_for``) unless
        given explicitly. ``lot_notional_units`` is the strategy's
        ``capital_mgmt.lot_notional_units`` and is required (fail fast) whenever
        ``commission_per_lot`` is positive — no lot size is assumed here.
        """
        build_brokerage_adapter(broker_adapter_name).apply(self)
        apply_fill_costs(
            self,
            spread_pips=spread_pips,
            commission_per_lot=commission_per_lot,
            lot_notional_units=lot_notional_units,
            pip_size=pip_size,
            log_tag=self._label(),
        )
        self.order_executor = OrderExecutor(self)

    def on_order_event(self, order_event: OrderEvent) -> None:  # noqa: F405
        """Forward every order event (fill or rejection) to the OrderExecutor."""
        self.order_executor.on_order_event(order_event)
