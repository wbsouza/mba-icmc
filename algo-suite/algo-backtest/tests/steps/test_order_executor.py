"""Step definitions for order_executor.feature (pytest-bdd).

Uses a fake algorithm double that mirrors LEAN's real synchronous backtest
ordering: ``market_order``/``liquidate`` fire the OnOrderEvent callback before
returning the ticket, matching how ``OrderExecutor.execute``/``close`` expect
to find the event already recorded in ``self._pending`` by the time the call
returns.
"""

from __future__ import annotations

import itertools
import sys
import types
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from algo_backtest.chain.model import Decision as ChainDecision
from algo_backtest.engine.order_executor import (
    Decision,
    FillStatus,
    OrderExecutor,
    SizingContext,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/order_executor.feature")

_SYMBOL = "EURUSD"


@pytest.fixture(autouse=True)
def _fake_order_status() -> Iterator[None]:
    """Stand in for LEAN's real AlgorithmImports.OrderStatus (container-only)."""
    module = types.ModuleType("AlgorithmImports")
    module.OrderStatus = types.SimpleNamespace(FILLED="FILLED", INVALID="INVALID")  # type: ignore[attr-defined]
    sys.modules["AlgorithmImports"] = module
    yield
    del sys.modules["AlgorithmImports"]


@dataclass
class _Ticket:
    order_id: int
    quantity: float = 0.0
    stop_price: float | None = None
    limit_price: float | None = None
    cancelled: bool = False

    def update_stop_price(self, price: float) -> None:
        self.stop_price = price

    def update_quantity(self, quantity: float) -> None:
        self.quantity = quantity

    def cancel(self) -> None:
        self.cancelled = True


@dataclass
class _Order:
    """LEAN `Order` as `Transactions.get_open_orders` returns it (id + quantity read)."""

    id: int
    quantity: float


class _Transactions:
    """Stand-in for `algorithm.transactions`: tickets by id, open = not cancelled."""

    def __init__(self) -> None:
        self.tickets: dict[int, _Ticket] = {}

    def get_order_ticket(self, order_id: int) -> _Ticket | None:
        return self.tickets.get(order_id)

    def get_open_orders(self, symbol: Any) -> list[_Order]:
        return [
            _Order(id=t.order_id, quantity=t.quantity)
            for t in self.tickets.values()
            if not t.cancelled
        ]


@dataclass
class _OrderEvent:
    order_id: int
    status: str
    fill_price: float = 0.0
    message: str | None = None


class _FakeAlgorithm:
    """A minimal QCAlgorithm double: market_order/liquidate fire the fill/reject
    event synchronously, exactly as LEAN's real backtest engine does.
    """

    def __init__(
        self, *, fills: bool, invested: bool = False, multi_ticket: bool = False,
        silent: bool = False,
    ) -> None:
        self._fills = fills
        self._invested = invested
        self._multi_ticket = multi_ticket
        self._silent = silent  # never fires OnOrderEvent (an order LEAN loses track of)
        self._ids = itertools.count(1)
        self.order_event_sink: Callable[[Any], None] | None = None
        self.orders: list[tuple[Any, float]] = []
        self.liquidated: list[Any] = []
        self.utc_time = datetime(2020, 1, 2, 14, 30, tzinfo=UTC)
        self.transactions = _Transactions()

    def calculate_order_quantity(self, symbol: Any, target: float) -> float:
        return target  # identity: unit tests pass sizes straight through

    def market_order(self, symbol: Any, quantity: float) -> _Ticket:
        self.orders.append((symbol, quantity))
        order_id = next(self._ids)
        self._fire(order_id)
        return _Ticket(order_id=order_id)

    def stop_market_order(self, symbol: Any, quantity: float, stop_price: float) -> _Ticket:
        """Mirror of LEAN's three-argument binding (a positional tag does not bind)."""
        ticket = _Ticket(order_id=next(self._ids), quantity=quantity, stop_price=stop_price)
        self.transactions.tickets[ticket.order_id] = ticket
        return ticket

    def limit_order(self, symbol: Any, quantity: float, limit_price: float) -> _Ticket:
        """Mirror of LEAN's three-argument binding (a positional tag does not bind)."""
        ticket = _Ticket(order_id=next(self._ids), quantity=quantity, limit_price=limit_price)
        self.transactions.tickets[ticket.order_id] = ticket
        return ticket

    def liquidate(self, symbol: Any) -> list[_Ticket]:
        if self._multi_ticket:
            # A multi-lot position split across two tickets — OrderExecutor.close
            # must reject this before consuming any OnOrderEvent, so no _fire here.
            return [_Ticket(order_id=next(self._ids)), _Ticket(order_id=next(self._ids))]
        if not self._invested:
            return []
        self.liquidated.append(symbol)
        order_id = next(self._ids)
        self._fire(order_id)
        return [_Ticket(order_id=order_id)]

    def _fire(self, order_id: int) -> None:
        assert self.order_event_sink is not None, "OrderExecutor never wired on_order_event"
        if self._silent:
            return
        if self._fills:
            event = _OrderEvent(order_id=order_id, status="FILLED", fill_price=1.2345)
        else:
            event = _OrderEvent(order_id=order_id, status="INVALID", message="insufficient margin")
        self.order_event_sink(event)


@pytest.fixture
def context() -> dict[str, Any]:
    return {}


def _wire(context: dict[str, Any], algorithm: _FakeAlgorithm) -> None:
    executor = OrderExecutor(algorithm)
    algorithm.order_event_sink = executor.on_order_event
    context["algorithm"] = algorithm
    context["executor"] = executor


@given("a fake algorithm that fills every order")
def _fills(context: dict[str, Any]) -> None:
    _wire(context, _FakeAlgorithm(fills=True))


@given("a fake algorithm that rejects every order")
def _rejects(context: dict[str, Any]) -> None:
    _wire(context, _FakeAlgorithm(fills=False))


@given("a fake algorithm that never reports an order event")
def _silent(context: dict[str, Any]) -> None:
    _wire(context, _FakeAlgorithm(fills=True, silent=True))


@given("a fake algorithm with an open position that fills every order")
def _open_position(context: dict[str, Any]) -> None:
    _wire(context, _FakeAlgorithm(fills=True, invested=True))


@given("a fake algorithm with no open position")
def _no_position(context: dict[str, Any]) -> None:
    _wire(context, _FakeAlgorithm(fills=True, invested=False))


@given("a fake algorithm whose liquidation returns multiple tickets")
def _multi_ticket_position(context: dict[str, Any]) -> None:
    _wire(context, _FakeAlgorithm(fills=True, multi_ticket=True))


@when(parsers.parse('OrderExecutor executes a {decision} decision with size {size:g}'))
def _execute(context: dict[str, Any], decision: str, size: float) -> None:
    executor: OrderExecutor = context["executor"]
    context["fill"] = executor.execute(_SYMBOL, Decision(decision), SizingContext(size=size))


@when(
    parsers.parse(
        "OrderExecutor executes a {decision} decision from chain.model's own Decision class"
    )
)
def _execute_cross_class(context: dict[str, Any], decision: str) -> None:
    executor: OrderExecutor = context["executor"]
    # Deliberately chain.model.Decision, NOT engine.order_executor.Decision.
    cross_class_decision = ChainDecision(decision)
    context["fill"] = executor.execute(_SYMBOL, cross_class_decision, SizingContext(size=1.0))


@when("OrderExecutor executes a BUY decision with a stop distance")
def _execute_with_stop(context: dict[str, Any]) -> None:
    executor: OrderExecutor = context["executor"]
    sizing = SizingContext(size=1.0, stop_loss=1.2300, take_profit=1.2400)
    context["sizing"] = sizing
    context["fill"] = executor.execute(_SYMBOL, Decision.BUY, sizing)


@when("OrderExecutor closes the position")
def _close(context: dict[str, Any]) -> None:
    executor: OrderExecutor = context["executor"]
    context["error"] = None
    try:
        context["fill"] = executor.close(_SYMBOL)
    except ValueError as exc:
        context["error"] = exc


@then(parsers.parse("a market order for size {size:g} is placed"))
def _order_placed(context: dict[str, Any], size: float) -> None:
    algorithm: _FakeAlgorithm = context["algorithm"]
    assert algorithm.orders == [(_SYMBOL, size)]


@then("no market order is placed")
def _no_order(context: dict[str, Any]) -> None:
    algorithm: _FakeAlgorithm = context["algorithm"]
    assert algorithm.orders == []


@then("the position is liquidated")
def _liquidated(context: dict[str, Any]) -> None:
    algorithm: _FakeAlgorithm = context["algorithm"]
    assert algorithm.liquidated == [_SYMBOL]


@then("closing fails with a multi-ticket error")
def _multi_ticket_error(context: dict[str, Any]) -> None:
    assert isinstance(context["error"], ValueError)
    assert "2 tickets" in str(context["error"])


@then(parsers.parse("the fill record status is {status} with direction {direction}"))
def _status_direction(context: dict[str, Any], status: str, direction: str) -> None:
    fill = context["fill"]
    assert fill.status is FillStatus(status)
    assert fill.direction == direction


@then(parsers.re(r"the fill record status is (?P<status>\w+)$"))
def _status(context: dict[str, Any], status: str) -> None:
    fill = context["fill"]
    assert fill.status is FillStatus(status)


@then("the fill record status is REJECTED with a rejection reason")
def _rejected(context: dict[str, Any]) -> None:
    fill = context["fill"]
    assert fill.status is FillStatus.REJECTED
    # exact text, not just truthiness: pins `event.message or event.status`
    # precedence (message wins when present) against an `and` mutation.
    assert fill.rejection_reason == "insufficient margin"


@then(parsers.parse('the fill record is rejected with reason "{reason}"'))
def _rejected_with_reason(context: dict[str, Any], reason: str) -> None:
    fill = context["fill"]
    assert fill.status is FillStatus.REJECTED
    assert fill.rejection_reason == reason


@then("the fill record's stop-loss and take-profit match the sizing context")
def _stop_take(context: dict[str, Any]) -> None:
    fill = context["fill"]
    sizing: SizingContext = context["sizing"]
    assert fill.stop_loss == sizing.stop_loss
    assert fill.take_profit == sizing.take_profit


# --- Story 12: quantity entries and the plan's working orders ---------------------------


@when(parsers.parse("OrderExecutor executes a {decision} decision for {quantity:g} units"))
def _execute_quantity(context: dict[str, Any], decision: str, quantity: float) -> None:
    executor: OrderExecutor = context["executor"]
    context["fill"] = executor.execute_quantity(_SYMBOL, Decision(decision), quantity)


@when(
    parsers.parse("OrderExecutor executing a {decision} decision for {quantity:g} units fails")
)
def _execute_quantity_fails(context: dict[str, Any], decision: str, quantity: float) -> None:
    executor: OrderExecutor = context["executor"]
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        executor.execute_quantity(_SYMBOL, Decision(decision), quantity)
    context["error"] = exc_info.value


@then(parsers.parse('the executor failure names "{fragment}"'))
def _executor_failure(context: dict[str, Any], fragment: str) -> None:
    assert fragment in str(context["error"]), str(context["error"])


@when(
    parsers.parse(
        "OrderExecutor places a stop for {quantity:g} units at {price:g}"
    )
)
@given(
    parsers.parse(
        "OrderExecutor placed a stop for {quantity:g} units at {price:g}"
    )
)
def _place_stop(context: dict[str, Any], quantity: float, price: float) -> None:
    executor: OrderExecutor = context["executor"]
    context["stop_id"] = executor.place_stop(_SYMBOL, quantity, price)


@when(
    parsers.parse(
        "OrderExecutor places a limit for {quantity:g} units at {price:g}"
    )
)
@given(
    parsers.parse(
        "OrderExecutor placed a limit for {quantity:g} units at {price:g}"
    )
)
def _place_limit(context: dict[str, Any], quantity: float, price: float) -> None:
    executor: OrderExecutor = context["executor"]
    context.setdefault("limit_ids", []).append(executor.place_limit(_SYMBOL, quantity, price))


def _tickets(context: dict[str, Any]) -> dict[int, _Ticket]:
    algorithm: _FakeAlgorithm = context["algorithm"]
    return algorithm.transactions.tickets


@then(
    parsers.parse(
        "the fake algorithm holds a stop-market order for {quantity:g} at {price:g}"
    )
)
def _holds_stop(context: dict[str, Any], quantity: float, price: float) -> None:
    ticket = _tickets(context)[context["stop_id"]]
    assert (ticket.quantity, ticket.stop_price) == (quantity, price)


@then(
    parsers.parse(
        "the fake algorithm holds a limit order for {quantity:g} at {price:g}"
    )
)
def _holds_limit(context: dict[str, Any], quantity: float, price: float) -> None:
    ticket = _tickets(context)[context["limit_ids"][-1]]
    assert (ticket.quantity, ticket.limit_price) == (quantity, price)


@then(parsers.parse("the executor reports {count:d} open orders for the symbol"))
def _open_count(context: dict[str, Any], count: int) -> None:
    executor: OrderExecutor = context["executor"]
    assert len(executor.open_orders(_SYMBOL)) == count


@when(parsers.parse("OrderExecutor moves that stop to {price:g}"))
def _move_stop(context: dict[str, Any], price: float) -> None:
    executor: OrderExecutor = context["executor"]
    executor.update_stop_price(context["stop_id"], price)


@when(parsers.parse("OrderExecutor resizes that stop to {quantity:g}"))
def _resize_stop(context: dict[str, Any], quantity: float) -> None:
    executor: OrderExecutor = context["executor"]
    executor.update_quantity(context["stop_id"], quantity)


@then(parsers.parse("the stop ticket's price is {price:g} and its quantity {quantity:g}"))
def _stop_ticket(context: dict[str, Any], price: float, quantity: float) -> None:
    ticket = _tickets(context)[context["stop_id"]]
    assert (ticket.stop_price, ticket.quantity) == (price, quantity)


@when("OrderExecutor cancels every open order for the symbol")
def _cancel_all(context: dict[str, Any]) -> None:
    executor: OrderExecutor = context["executor"]
    executor.cancel(order.order_id for order in executor.open_orders(_SYMBOL))


@then("every fake ticket is cancelled")
def _all_cancelled(context: dict[str, Any]) -> None:
    tickets = _tickets(context)
    assert tickets and all(t.cancelled for t in tickets.values())


@when(parsers.parse("OrderExecutor moving stop {order_id:d} to {price:g} fails"))
def _move_missing(context: dict[str, Any], order_id: int, price: float) -> None:
    executor: OrderExecutor = context["executor"]
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        executor.update_stop_price(order_id, price)
    context["error"] = exc_info.value
