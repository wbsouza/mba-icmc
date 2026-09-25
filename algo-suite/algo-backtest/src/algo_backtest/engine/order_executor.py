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

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


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
    ``utc_time``). Order events are collected via :meth:`on_order_event`, which
    ``engine/algorithm.py``'s ``OnOrderEvent`` callback forwards here.

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

        direction = 1 if decision is Decision.BUY else -1
        quantity = self._algorithm.calculate_order_quantity(symbol, direction * sizing.size)
        ticket = self._algorithm.market_order(symbol, quantity)
        event = self._pending.pop(ticket.order_id, None)
        return self._normalize(decision, ticket.order_id, sizing, event)

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
            "LONG" if decision is Decision.BUY else "SHORT" if decision is Decision.SELL else None
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
