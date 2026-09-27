"""OrderExecutor: given a Decision + sizing context, place the order through
LEAN's real order primitives, handle the OnOrderEvent fill/rejection callback,
and return a normalized fill record (spec.md Sec 3).

Holds no state about open positions itself — LEAN's ``algorithm.portfolio`` is
the source of truth; this class only translates a Decision into the right LEAN
call and normalizes what ``OnOrderEvent`` reports back. Decoupled from
``AlgorithmImports`` at import time (only referenced through the ``algorithm``
object passed in), so this module is importable and unit-testable outside the
LEAN container.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from algo_backtest.engine.trade_plan import OpenOrder


class Decision(StrEnum):
    """One of the four final per-tick outcomes (specs.md Sec 11.3.1.1)."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NO_TRADE = "NO_TRADE"


class FillStatus(StrEnum):
    """The outcome of one OrderExecutor call."""

    NONE = "NONE"  # HOLD/NO_TRADE: no order was placed
    FILLED = "FILLED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class SizingContext:
    """Position-sizing/risk inputs the order executor needs to place an order.

    ``size`` is a signed-agnostic magnitude (lots/units, or a portfolio
    fraction for ``set_holdings``-style sizing); direction comes from the
    ``Decision``, not from the sign of ``size``.
    """

    size: float
    stop_loss: float | None = None
    take_profit: float | None = None


@dataclass(frozen=True)
class FillRecord:
    """Normalized outcome of one ``OrderExecutor`` call."""

    decision: Decision
    status: FillStatus
    order_id: int | None = None
    fill_price: float | None = None
    fill_time: str | None = None  # ISO timestamp, from the algorithm's UTC clock
    direction: str | None = None  # "LONG" / "SHORT" / None
    stop_loss: float | None = None
    take_profit: float | None = None
    rejection_reason: str | None = None


_NO_OP = FillRecord(decision=Decision.HOLD, status=FillStatus.NONE)


class OrderExecutor:
    """Places/manages one symbol's order via ``algorithm``'s real LEAN primitives.

    ``algorithm`` is the running ``QCAlgorithm`` (or a test double exposing the
    same narrow surface: ``market_order``, ``liquidate``, ``calculate_order_quantity``,
    ``stop_market_order``, ``limit_order``, ``transactions``, ``utc_time``). Order events
    are collected via :meth:`on_order_event`, which ``engine/algorithm.py``'s
    ``OnOrderEvent`` callback forwards here.

    ``SizingContext.size`` is a target portfolio fraction in ``(0, 1]`` — the same
    semantics ``self.set_holdings`` uses — translated to a real order quantity via
    ``algorithm.calculate_order_quantity`` (LEAN's own percent-to-quantity helper)
    before placing the order, so a fractional size below one lot is never rejected.
    """

    def __init__(self, algorithm: Any) -> None:
        self._algorithm = algorithm
        self._pending: dict[int, Any] = {}

    def on_order_event(self, order_event: Any) -> None:
        """Record one ``OnOrderEvent`` payload, keyed by its order id.

        Never raises on a rejection — the rejection is recorded and surfaced
        by :meth:`execute`'s return value, not by crashing the backtest.
        """
        self._pending[order_event.order_id] = order_event

    def execute(self, symbol: Any, decision: Decision, sizing: SizingContext) -> FillRecord:
        """Place (or stand aside from) an order for one Decision.

        ``HOLD``/``NO_TRADE`` place no order (§11.3.1.1: the order executor's
        job for these is to manage/stand aside, not open a new position).
        """
        if decision in (Decision.HOLD, Decision.NO_TRADE):
            return FillRecord(decision=decision, status=FillStatus.NONE)

        # == not is: StrEnum members compare equal by string value even across two
        # distinct Decision classes (this module's own vs. e.g. chain.model.Decision) --
        # `is` silently fails cross-class and would misfire every direction as -1.
        # Confirmed live (2026-09-26 PR #33 review): a caller passing chain.model.Decision
        # straight into this method had every BUY execute as a SELL until this was fixed.
        direction = 1 if decision == Decision.BUY else -1
        quantity = self._algorithm.calculate_order_quantity(symbol, direction * sizing.size)
        ticket = self._algorithm.market_order(symbol, quantity)
        event = self._pending.pop(ticket.order_id, None)
        return self._normalize(decision, ticket.order_id, sizing, event)

    def execute_quantity(self, symbol: Any, decision: Decision, quantity: float) -> FillRecord:
        """Place a market order for an explicit signed `quantity` (units) for a BUY/SELL.

        The trade-plan path (story 12): the quantity comes from F6's lot size, not from a
        portfolio fraction, so LEAN's percent-to-quantity helper is bypassed.

        Raises:
            ValueError: `decision` is not BUY/SELL, or `quantity`'s sign contradicts it
                (a plan bug to surface before any order is placed).
        """
        if decision not in (Decision.BUY, Decision.SELL):
            raise ValueError(
                f"OrderExecutor.execute_quantity: {decision!r} places no order; only BUY/SELL"
            )
        expected_sign = 1 if decision == Decision.BUY else -1
        if quantity == 0 or (quantity > 0) != (expected_sign > 0):
            raise ValueError(
                f"OrderExecutor.execute_quantity: quantity {quantity!r} contradicts {decision} "
                "(BUY needs a positive quantity, SELL a negative one)"
            )
        ticket = self._algorithm.market_order(symbol, quantity)
        event = self._pending.pop(ticket.order_id, None)
        return self._normalize(decision, ticket.order_id, SizingContext(size=abs(quantity)), event)

    def place_stop(self, symbol: Any, quantity: float, stop_price: float, tag: str) -> int:
        """Submit a stop-market order (the plan's protective stop); returns its order id."""
        return int(self._algorithm.stop_market_order(symbol, quantity, stop_price, tag).order_id)

    def place_limit(self, symbol: Any, quantity: float, limit_price: float, tag: str) -> int:
        """Submit a limit order (one take-profit level); returns its order id."""
        return int(self._algorithm.limit_order(symbol, quantity, limit_price, tag).order_id)

    def update_stop_price(self, order_id: int, stop_price: float) -> None:
        """Move a working stop order to `stop_price` (LEAN `OrderTicket.update_stop_price`)."""
        self._ticket(order_id).update_stop_price(stop_price)

    def update_quantity(self, order_id: int, quantity: float) -> None:
        """Resize a working order (LEAN `OrderTicket.update_quantity`)."""
        self._ticket(order_id).update_quantity(quantity)

    def cancel(self, order_ids: Iterable[int]) -> None:
        """Cancel each working order by id (LEAN `OrderTicket.cancel`)."""
        for order_id in order_ids:
            self._ticket(order_id).cancel()

    def open_orders(self, symbol: Any) -> tuple[OpenOrder, ...]:
        """The working orders for `symbol` (LEAN `Transactions.get_open_orders`)."""
        return tuple(
            OpenOrder(order_id=int(order.id), quantity=float(order.quantity))
            for order in self._algorithm.transactions.get_open_orders(symbol)
        )

    def _ticket(self, order_id: int) -> Any:
        """The LEAN order ticket for `order_id` (fail fast if LEAN has none)."""
        ticket = self._algorithm.transactions.get_order_ticket(order_id)
        if ticket is None:
            raise ValueError(
                f"OrderExecutor: no order ticket for order id {order_id}; the plan's working "
                "orders and LEAN's transaction ledger disagree"
            )
        return ticket

    def close(self, symbol: Any) -> FillRecord:
        """Liquidate the open position in ``symbol`` (an exit, not one of the
        four Decisions — shared here so both baseline algos stop duplicating
        their own ``self.liquidate(...)`` order-placement code).

        The ``FillRecord.decision`` field is ``HOLD`` here for lack of a dedicated
        "closed" value (spec.md Sec 11.3.1.1 only defines the four order-placement
        decisions); the caller must read ``status`` (``FILLED``/``REJECTED``), not
        ``decision``, to tell a close from a true no-op (``_NO_OP``, ``status=NONE``).

        Raises:
            ValueError: if ``liquidate`` returns more than one ticket — every caller
                today (both baseline algos) opens at most one position per symbol, so
                multiple tickets means a multi-lot position this method was never
                designed to normalize; fail fast rather than silently reporting only
                the first ticket's fill and dropping the rest.
        """
        tickets = self._algorithm.liquidate(symbol)
        if not tickets:
            return _NO_OP
        if len(tickets) > 1:
            raise ValueError(
                f"liquidate({symbol!r}) returned {len(tickets)} tickets; "
                "OrderExecutor.close only normalizes a single-ticket liquidation."
            )
        ticket = tickets[0]
        event = self._pending.pop(ticket.order_id, None)
        return self._normalize(Decision.HOLD, ticket.order_id, SizingContext(size=0.0), event)

    def _normalize(
        self, decision: Decision, order_id: int, sizing: SizingContext, event: Any
    ) -> FillRecord:
        """Build the normalized fill record from a (possibly-absent) order event."""
        if event is None:
            # In backtest mode LEAN's transaction handler runs synchronously, so this
            # should not happen; treated as a rejection rather than a silent fill.
            return FillRecord(
                decision=decision,
                status=FillStatus.REJECTED,
                order_id=order_id,
                rejection_reason="no OnOrderEvent received for this order",
            )
        from AlgorithmImports import OrderStatus  # noqa: PLC0415

        if event.status != OrderStatus.FILLED:
            return FillRecord(
                decision=decision,
                status=FillStatus.REJECTED,
                order_id=order_id,
                rejection_reason=str(event.message or event.status),
            )
        direction = (
            "LONG" if decision == Decision.BUY else "SHORT" if decision == Decision.SELL else None
        )
        return FillRecord(
            decision=decision,
            status=FillStatus.FILLED,
            order_id=order_id,
            fill_price=float(event.fill_price),
            fill_time=self._algorithm.utc_time.isoformat(),
            direction=direction,
            stop_loss=sizing.stop_loss,
            take_profit=sizing.take_profit,
        )
