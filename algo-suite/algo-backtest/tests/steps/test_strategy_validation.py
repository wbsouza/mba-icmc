"""Steps for strategy_validation.feature — per-strategy run-input validation."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from algo_backtest.run import validate_run_inputs
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/strategy_validation.feature")

_START, _END = date(2014, 5, 7), date(2014, 5, 9)


@pytest.fixture
def vctx() -> dict[str, Any]:
    """Holds the strategy + parsed params + the validation outcome/error."""
    return {}


@given(parsers.parse('strategy "{strategy}" with params {params}'))
def _given(vctx: dict[str, Any], strategy: str, params: str) -> None:
    vctx["strategy"] = strategy
    vctx["params"] = dict(token.split("=", 1) for token in params.split())


@when("I validate the run inputs")
def _validate(vctx: dict[str, Any]) -> None:
    validate_run_inputs(vctx["strategy"], vctx["params"], _START, _END)
    vctx["ok"] = True


@when("I validate the run inputs expecting failure")
def _validate_failing(vctx: dict[str, Any]) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        validate_run_inputs(vctx["strategy"], vctx["params"], _START, _END)
    vctx["error"] = str(exc_info.value)


@then("validation passes")
def _passes(vctx: dict[str, Any]) -> None:
    assert vctx.get("ok") is True


@then("validation fails naming the unknown strategy")
def _unknown(vctx: dict[str, Any]) -> None:
    assert "unknown strategy" in vctx["error"] and "bogus" in vctx["error"]


@then("validation fails saying the params must be exactly the strategy's set")
def _wrong_keys(vctx: dict[str, Any]) -> None:
    assert "must be exactly" in vctx["error"]


@then("validation fails saying the band must be positive")
def _band(vctx: dict[str, Any]) -> None:
    assert "band" in vctx["error"] and "positive" in vctx["error"]


@then("validation fails saying the window must be at least 2")
def _window(vctx: dict[str, Any]) -> None:
    assert "window" in vctx["error"] and "at least 2" in vctx["error"]


@then(parsers.parse('validation fails naming "{word}"'))
def _fails_naming(vctx: dict[str, Any], word: str) -> None:
    assert word in vctx["error"]


@when(parsers.parse("I validate the run inputs for the window {first} to {last}"))
def _validate_window(vctx: dict[str, Any], first: str, last: str) -> None:
    from datetime import date

    validate_run_inputs(
        vctx["strategy"], vctx["params"], date.fromisoformat(first), date.fromisoformat(last)
    )
    vctx["ok"] = True


@when(
    parsers.parse("I validate the run inputs for the window {first} to {last} expecting failure")
)
def _validate_window_failing(vctx: dict[str, Any], first: str, last: str) -> None:
    from datetime import date

    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        validate_run_inputs(
            vctx["strategy"], vctx["params"], date.fromisoformat(first), date.fromisoformat(last)
        )
    vctx["error"] = str(exc_info.value)


@given(parsers.parse("materialized lean-data day-zips for EURUSD on {days}"))
def _day_zips(vctx: dict[str, Any], tmp_path: Any, days: str) -> None:
    from algo_core.instrument import build_instrument
    from algo_core.layout import lean_data_dir_for

    instrument = build_instrument("EURUSD")
    directory = lean_data_dir_for(tmp_path, instrument, "minute")
    directory.mkdir(parents=True)
    for day in days.split(","):
        (directory / f"{day.strip()}_quote.zip").write_bytes(b"")
    vctx["data_root"], vctx["instrument"] = tmp_path, instrument


@then(parsers.parse("lean-data covers {first} to {last} is {covered}"))
def _covers(vctx: dict[str, Any], first: str, last: str, covered: str) -> None:
    from datetime import date

    from algo_backtest.run import lean_data_covers

    result = lean_data_covers(
        vctx["data_root"], vctx["instrument"], date.fromisoformat(first), date.fromisoformat(last)
    )
    assert result is (covered == "true")
