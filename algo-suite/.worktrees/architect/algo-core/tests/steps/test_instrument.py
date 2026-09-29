"""Step definitions for instrument.feature (pytest-bdd)."""

from __future__ import annotations

import pytest
from algo_core.instrument import Instrument, UnknownSymbolError, build_instrument
from pytest_bdd import parsers, scenarios, then, when

scenarios("../features/instrument.feature")


@pytest.fixture
def context() -> dict[str, object]:
    """Carries the built instrument (or raised error) between steps."""
    return {}


def _instrument(context: dict[str, object]) -> Instrument:
    inst = context["instrument"]
    assert isinstance(inst, Instrument)
    return inst


@when(parsers.parse('I build the instrument "{symbol}"'))
def _build(context: dict[str, object], symbol: str) -> None:
    try:
        context["instrument"] = build_instrument(symbol)
    except UnknownSymbolError as exc:
        context["error"] = exc


@then(parsers.parse('its unit is "{unit}"'))
def _unit(context: dict[str, object], unit: str) -> None:
    assert _instrument(context).unit == unit


@then(parsers.parse("its unit_size is {value:g}"))
def _unit_size(context: dict[str, object], value: float) -> None:
    assert _instrument(context).unit_size == pytest.approx(value)


@then(parsers.parse("its digits is {value:d}"))
def _digits(context: dict[str, object], value: int) -> None:
    assert _instrument(context).digits == value


@then(parsers.parse("its price_increment is {value:g}"))
def _price_increment(context: dict[str, object], value: float) -> None:
    assert _instrument(context).price_increment == pytest.approx(value)


@then(parsers.parse('its details base is "{base}" and quote is "{quote}"'))
def _details(context: dict[str, object], base: str, quote: str) -> None:
    details = _instrument(context).details
    assert details.base == base
    assert details.quote == quote


@then(parsers.parse('its security_type is "{value}"'))
def _security_type(context: dict[str, object], value: str) -> None:
    assert _instrument(context).security_type == value


@then(parsers.parse('its market is "{value}"'))
def _market(context: dict[str, object], value: str) -> None:
    assert _instrument(context).market == value


@then(parsers.parse("its lot_size is {value:g}"))
def _lot_size(context: dict[str, object], value: float) -> None:
    assert _instrument(context).lot_size == pytest.approx(value)


@then(parsers.parse("rounding {price:g} yields {expected:g}"))
def _round(context: dict[str, object], price: float, expected: float) -> None:
    assert _instrument(context).round_price(price) == pytest.approx(expected)


@then("construction fails with an unknown-symbol error")
def _unknown(context: dict[str, object]) -> None:
    assert isinstance(context.get("error"), UnknownSymbolError)
    assert "instrument" not in context
