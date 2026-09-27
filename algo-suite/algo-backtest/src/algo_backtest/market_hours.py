"""LEAN's own OANDA forex trading hours, so offline code sees exactly the bars LEAN does.

The pinned LEAN engine only delivers a minute bar to `on_data` (and to the indicators
registered on it) when the exchange is open at the bar's start, per its market-hours
database — e.g. never during the daily 16:58-17:03 New York break, the weekend, or a
listed holiday. `lean_market_hours_forex_oanda.json` is the `Forex-oanda-[*]` entry
copied verbatim from `quantconnect/lean:17748`, so F7 training
(`algo_backtest.training`) can drop exactly the bars the live algorithm never sees.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_ENTRY: dict[str, Any] = json.loads(
    Path(__file__).with_name("lean_market_hours_forex_oanda.json").read_text()
)["entry"]
_EXCHANGE_TZ = ZoneInfo(_ENTRY["exchangeTimeZone"])
_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _offset(raw: str) -> timedelta:
    """A LEAN time-of-day (`HH:MM:SS` or `D.HH:MM:SS`) as an offset from midnight."""
    days, _, clock = raw.rpartition(".")
    hours, minutes, seconds = (int(part) for part in clock.split(":"))
    return timedelta(days=int(days or 0), hours=hours, minutes=minutes, seconds=seconds)


def _day(raw: str) -> date:
    """A LEAN `M/D/YYYY` date."""
    month, day, year = (int(part) for part in raw.split("/"))
    return date(year, month, day)


_SEGMENTS: dict[int, list[tuple[timedelta, timedelta]]] = {
    weekday: [
        (_offset(segment["start"]), _offset(segment["end"]))
        for segment in _ENTRY[name]
        if segment["state"] == "market"
    ]
    for weekday, name in enumerate(_WEEKDAYS)
}
_HOLIDAYS = {_day(raw) for raw in _ENTRY["holidays"]}
_EARLY_CLOSES = {_day(raw): _offset(clock) for raw, clock in _ENTRY["earlyCloses"].items()}
_LATE_OPENS = {_day(raw): _offset(clock) for raw, clock in _ENTRY["lateOpens"].items()}


def lean_delivers(bar_start: datetime) -> bool:
    """Whether LEAN delivers the minute bar starting at `bar_start` (aware, any zone).

    Open means: the exchange-local time falls in one of that weekday's market segments
    (start inclusive, end exclusive); a holiday is closed unless it also has an early
    close or late open (a partial day); an early close ends the day at its time and a
    late open starts it at its time.
    """
    local = bar_start.astimezone(_EXCHANGE_TZ)
    day = local.date()
    clock = timedelta(hours=local.hour, minutes=local.minute, seconds=local.second)
    partial = day in _EARLY_CLOSES or day in _LATE_OPENS
    if day in _HOLIDAYS and not partial:
        return False
    if day in _EARLY_CLOSES and clock >= _EARLY_CLOSES[day]:
        return False
    if day in _LATE_OPENS and clock < _LATE_OPENS[day]:
        return False
    return any(start <= clock < end for start, end in _SEGMENTS[local.weekday()])
