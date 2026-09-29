"""Step definitions for bi5.feature (offline decoder; synthetic LZMA payloads)."""

from __future__ import annotations

import lzma
from datetime import UTC, datetime

import pytest
from algo_transform.decoders.bi5 import DecodeError, decode_bi5
from pytest_bdd import given, parsers, scenarios, then, when

from .conftest import bi5_payload

scenarios("../features/bi5.feature")

_HOUR = datetime(2020, 1, 2, 14, 0, tzinfo=UTC)
_EURUSD = 1e-5  # price_increment for digits=5
_USDJPY = 1e-3  # price_increment for digits=3


@given(parsers.parse("a bi5 payload with EUR/USD records"), target_fixture="payload")
def _payload_from_table(datatable: list[list[str]]) -> bytes:
    """Build a payload from the Gherkin data table (header row + record rows)."""
    rows = datatable[1:]
    records = [
        (int(r[0]), int(r[1]), int(r[2]), float(r[3]), float(r[4])) for r in rows
    ]
    return bi5_payload(records)


@given("an empty bi5 payload", target_fixture="payload")
def _empty_payload() -> bytes:
    return b""


@given("a bi5 payload that compresses an empty record stream", target_fixture="payload")
def _compressed_empty_payload() -> bytes:
    return lzma.compress(b"")


@given("a bi5 payload of non-LZMA bytes", target_fixture="payload")
def _non_lzma_payload() -> bytes:
    return b"not-valid-lzma-bytes"


@given("a bi5 payload that compresses 25 bytes", target_fixture="payload")
def _truncated_payload() -> bytes:
    return lzma.compress(b"x" * 25)  # 25 bytes is not a multiple of 20


def _decode(context: dict[str, object], payload: bytes, increment: float) -> None:
    """Decode, storing either ticks or the raised exception in context."""
    try:
        context["ticks"] = decode_bi5(payload, _HOUR, increment)
    except (ValueError, DecodeError) as exc:  # noqa: BLE001 - asserted in Then steps
        context["error"] = exc


@when("I decode it with the EUR/USD increment at hour 2020-01-02 14h UTC")
def _decode_eurusd(context: dict[str, object], payload: bytes) -> None:
    _decode(context, payload, _EURUSD)


@when("I decode it with the USD/JPY increment at hour 2020-01-02 14h UTC")
def _decode_usdjpy(context: dict[str, object], payload: bytes) -> None:
    _decode(context, payload, _USDJPY)


@when("I decode it with the EUR/USD increment at a naive hour start")
def _decode_naive(context: dict[str, object], payload: bytes) -> None:
    try:
        decode_bi5(payload, datetime(2020, 1, 2, 14, 0), _EURUSD)  # naive, no tzinfo
    except ValueError as exc:
        context["error"] = exc


def _ticks(context: dict[str, object]) -> list:  # type: ignore[type-arg]
    ticks = context["ticks"]
    assert isinstance(ticks, list)
    return ticks


@then(parsers.parse("it yields {count:d} ticks"))
def _yields(context: dict[str, object], count: int) -> None:
    assert len(_ticks(context)) == count


@then(parsers.parse("tick {idx:d} has bid {bid:g} and ask {ask:g}"))
def _bid_ask(context: dict[str, object], idx: int, bid: float, ask: float) -> None:
    tick = _ticks(context)[idx]
    assert tick.bid == pytest.approx(bid)
    assert tick.ask == pytest.approx(ask)


@then(parsers.parse("tick {idx:d} has timestamp 2020-01-02 14:00:00.086000 UTC"))
def _timestamp(context: dict[str, object], idx: int) -> None:
    tick = _ticks(context)[idx]
    assert tick.timestamp == datetime(2020, 1, 2, 14, 0, 0, 86_000, tzinfo=UTC)


@then(parsers.parse("tick {idx:d} has bid_volume {bid_vol:g} and ask_volume {ask_vol:g}"))
def _volumes(context: dict[str, object], idx: int, bid_vol: float, ask_vol: float) -> None:
    tick = _ticks(context)[idx]
    assert tick.bid_volume == pytest.approx(bid_vol)
    assert tick.ask_volume == pytest.approx(ask_vol)


@then(parsers.parse("tick {idx:d} has bid not greater than ask"))
def _ordered(context: dict[str, object], idx: int) -> None:
    tick = _ticks(context)[idx]
    assert tick.bid <= tick.ask  # guards against a field-order/scale swap


@then(parsers.parse('it fails with ValueError mentioning "{needle}"'))
def _fails_value_error(context: dict[str, object], needle: str) -> None:
    error = context["error"]
    assert isinstance(error, ValueError)
    assert needle in str(error)


@then("it fails with DecodeError")
def _fails_decode_error(context: dict[str, object]) -> None:
    assert isinstance(context["error"], DecodeError)
