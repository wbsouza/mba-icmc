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
        self, *, fills: bool, invested: bool = False, multi_ticket: bool = False
    ) -> None:
        self._fills = fills
        self._invested = invested
        self._multi_ticket = multi_ticket
        self._ids = itertools.count(1)
        self.order_event_sink: Callable[[Any], None] | None = None
        self.orders: list[tuple[Any, float]] = []
        self.liquidated: list[Any] = []
        self.utc_time = datetime(2020, 1, 2, 14, 30, tzinfo=UTC)

    def calculate_order_quantity(self, symbol: Any, target: float) -> float:
        return target  # identity: unit tests pass sizes straight through

    def market_order(self, symbol: Any, quantity: float) -> _Ticket:
        self.orders.append((symbol, quantity))
        order_id = next(self._ids)
        self._fire(order_id)
        return _Ticket(order_id=order_id)

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


@then("the fill record's stop-loss and take-profit match the sizing context")
def _stop_take(context: dict[str, Any]) -> None:
    fill = context["fill"]
    sizing: SizingContext = context["sizing"]
    assert fill.stop_loss == sizing.stop_loss
    assert fill.take_profit == sizing.take_profit
