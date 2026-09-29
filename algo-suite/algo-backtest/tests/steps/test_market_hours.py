"""Steps for market_hours.feature — LEAN's OANDA forex hours, mirrored offline."""

from __future__ import annotations

from datetime import datetime

from algo_backtest.market_hours import lean_delivers
from pytest_bdd import parsers, scenarios, then

scenarios("../features/market_hours.feature")


@then(parsers.parse('a bar starting at "{utc}" is {delivered}'))
def _delivered(utc: str, delivered: str) -> None:
    assert lean_delivers(datetime.fromisoformat(utc)) is (delivered == "delivered")
