"""Step definitions for dukascopy_paths.feature (pytest-bdd)."""

from __future__ import annotations

from pathlib import Path

from algo_download.adapters.dukascopy.paths import (
    TickFile,
    bi5_url,
    parse_raw_path,
    raw_path,
)
from pytest_bdd import parsers, scenarios, then, when

scenarios("../features/dukascopy_paths.feature")


@when(
    parsers.parse('I build the bi5 URL for "{symbol}" {year:d}-{month:d}-{day:d} {hour:d}h'),
    target_fixture="result",
)
def _build_url(symbol: str, year: int, month: int, day: int, hour: int) -> dict[str, object]:
    """Build the bi5 URL for the given tick coordinates."""
    tick = TickFile(symbol=symbol, year=year, month=month, day=day, hour=hour)
    return {"url": bi5_url(tick)}


@when(
    parsers.parse(
        'I build the raw path under "{root}" for "{symbol}" {year:d}-{month:d}-{day:d} {hour:d}h'
    ),
    target_fixture="result",
)
def _build_raw(
    root: str, symbol: str, year: int, month: int, day: int, hour: int
) -> dict[str, object]:
    """Build the on-disk raw path for the given tick coordinates."""
    tick = TickFile(symbol=symbol, year=year, month=month, day=day, hour=hour)
    return {"path": raw_path(Path(root), tick)}


@when(
    parsers.parse(
        'I round-trip the raw path under "{root}" '
        'for "{symbol}" {year:d}-{month:d}-{day:d} {hour:d}h'
    ),
    target_fixture="result",
)
def _round_trip(
    root: str, symbol: str, year: int, month: int, day: int, hour: int
) -> dict[str, object]:
    """Build then parse the raw path, capturing both ticks for comparison."""
    tick = TickFile(symbol=symbol, year=year, month=month, day=day, hour=hour)
    return {"tick": tick, "parsed": parse_raw_path(raw_path(Path(root), tick))}


@then(parsers.parse('the URL is "{expected}"'))
def _url_is(result: dict[str, object], expected: str) -> None:
    assert result["url"] == expected


@then(parsers.parse('the raw path is "{expected}"'))
def _path_is(result: dict[str, object], expected: str) -> None:
    assert result["path"] == Path(expected)


@then("the parsed tick equals the original tick")
def _tick_equals(result: dict[str, object]) -> None:
    assert result["parsed"] == result["tick"]
