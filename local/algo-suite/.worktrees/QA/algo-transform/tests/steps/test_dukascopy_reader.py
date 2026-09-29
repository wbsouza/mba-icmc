"""Step definitions for dukascopy_reader.feature (enumeration, completeness, loading)."""

from __future__ import annotations

from pathlib import Path

import pytest
from algo_core.instrument import build_instrument
from algo_core.layout import TickFile, dukascopy_raw_path
from algo_transform.readers.dukascopy import (
    expected_hours,
    is_month_complete,
    load_ticks,
)
from pytest_bdd import given, parsers, scenarios, then, when

from .conftest import bi5_payload, write_raw

scenarios("../features/dukascopy_reader.feature")


@given("a writable data root")
def _writable(data_root: Path) -> None:
    assert data_root.is_dir()


@given(parsers.parse("the EURUSD 2020-01 month is filled with no-data markers"))
def _fill_markers(data_root: Path) -> None:
    for tick in expected_hours("EURUSD", 2020, 1):
        write_raw(data_root, tick, b"")  # 0-byte no-data markers


@given(parsers.parse(
    "a data hour at EURUSD 2020-01-{day:d} {hour:d}h with one EUR/USD tick"
))
def _data_hour(data_root: Path, day: int, hour: int) -> None:
    write_raw(
        data_root,
        TickFile(symbol="EURUSD", year=2020, month=1, day=day, hour=hour),
        bi5_payload([(86, 111966, 111963, 4.39, 0.75)]),
    )


@given(parsers.parse("a corrupt hour at EURUSD 2020-01-{day:d} {hour:d}h"))
def _corrupt_hour(data_root: Path, day: int, hour: int) -> None:
    write_raw(
        data_root,
        TickFile(symbol="EURUSD", year=2020, month=1, day=day, hour=hour),
        b"not-lzma",
    )


@when("I enumerate the expected hours for EURUSD 2020-01")
def _enumerate(context: dict[str, object]) -> None:
    context["hours"] = expected_hours("EURUSD", 2020, 1)


@when(parsers.parse("the hour EURUSD 2020-01-{day:d} {hour:d}h is removed"))
def _remove_hour(data_root: Path, day: int, hour: int) -> None:
    dukascopy_raw_path(
        data_root, TickFile(symbol="EURUSD", year=2020, month=1, day=day, hour=hour)
    ).unlink()


@when("I load ticks for EURUSD 2020-01")
def _load(context: dict[str, object], data_root: Path) -> None:
    context["result"] = load_ticks(data_root, build_instrument("EURUSD"), 2020, 1)


def _hours(context: dict[str, object]) -> list[TickFile]:
    hours = context["hours"]
    assert isinstance(hours, list)
    return hours


@then(parsers.parse("there are {count:d} expected hours"))
def _hour_count(context: dict[str, object], count: int) -> None:
    assert len(_hours(context)) == count  # 31 * 24


@then(parsers.parse("the first expected hour is EURUSD 2020-01-{day:d} {hour:d}h"))
def _first_hour(context: dict[str, object], day: int, hour: int) -> None:
    assert _hours(context)[0] == TickFile(
        symbol="EURUSD", year=2020, month=1, day=day, hour=hour
    )


@then(parsers.parse("the last expected hour is EURUSD 2020-01-{day:d} {hour:d}h"))
def _last_hour(context: dict[str, object], day: int, hour: int) -> None:
    assert _hours(context)[-1] == TickFile(
        symbol="EURUSD", year=2020, month=1, day=day, hour=hour
    )


@then("the month EURUSD 2020-01 is complete")
def _complete(data_root: Path) -> None:
    assert is_month_complete(data_root, "EURUSD", 2020, 1)


@then("the month EURUSD 2020-01 is incomplete")
def _incomplete(data_root: Path) -> None:
    assert not is_month_complete(data_root, "EURUSD", 2020, 1)


@then(parsers.parse("it loads {count:d} tick"))
def _loaded(context: dict[str, object], count: int) -> None:
    assert len(context["result"].ticks) == count  # type: ignore[attr-defined]


@then(parsers.parse("the first loaded tick has ask {ask:g}"))
def _first_ask(context: dict[str, object], ask: float) -> None:
    assert context["result"].ticks[0].ask == pytest.approx(ask)  # type: ignore[attr-defined]


@then(parsers.parse("{count:d} hour is quarantined"))
def _quarantined(context: dict[str, object], count: int) -> None:
    assert len(context["result"].quarantined) == count  # type: ignore[attr-defined]


@then("nothing is quarantined")
def _none_quarantined(context: dict[str, object]) -> None:
    assert context["result"].quarantined == ()  # type: ignore[attr-defined]
