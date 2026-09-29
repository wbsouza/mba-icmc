"""Step definitions for paths.feature (pytest-bdd)."""

from __future__ import annotations

from pathlib import Path

import pytest
from algo_core import layout
from algo_core.instrument import build_instrument
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/paths.feature")


@pytest.fixture
def context() -> dict[str, object]:
    """Carries the data root and the built path between steps."""
    return {}


def _root(context: dict[str, object]) -> Path:
    root = context["data_root"]
    assert isinstance(root, Path)
    return root


def _path(context: dict[str, object]) -> Path:
    path = context["path"]
    assert isinstance(path, Path)
    return path


@given(parsers.parse('the data root "{root}"'))
def _set_root(context: dict[str, object], root: str) -> None:
    context["data_root"] = Path(root)


@when(
    parsers.parse(
        'I build the price path for security_type "{security_type}" symbol "{symbol}" '
        'resolution "{resolution}" year {year:d} month {month:d}'
    )
)
def _build_price(
    context: dict[str, object],
    security_type: str,
    symbol: str,
    resolution: str,
    year: int,
    month: int,
) -> None:
    context["path"] = layout.price_path(
        _root(context), security_type, symbol, resolution, year, month
    )


@when(
    parsers.parse(
        'I build the feature path for domain "{domain}" dataset "{dataset}" '
        "year {year:d} month {month:d}"
    )
)
def _build_feature(
    context: dict[str, object], domain: str, dataset: str, year: int, month: int
) -> None:
    context["path"] = layout.feature_path(_root(context), domain, dataset, year, month)


@then(parsers.parse('the path is "{expected}"'))
def _path_is(context: dict[str, object], expected: str) -> None:
    assert str(_path(context)) == expected


@then(
    parsers.parse(
        'parsing the price path yields security_type "{security_type}" symbol "{symbol}" '
        'resolution "{resolution}" year {year:d} month {month:d}'
    )
)
def _parse_price(
    context: dict[str, object],
    security_type: str,
    symbol: str,
    resolution: str,
    year: int,
    month: int,
) -> None:
    parts = layout.parse_price_path(_path(context))
    assert parts.security_type == security_type
    assert parts.symbol == symbol
    assert parts.resolution == resolution
    assert parts.year == year
    assert parts.month == month


@then(
    parsers.parse(
        'parsing the feature path yields domain "{domain}" dataset "{dataset}" '
        "year {year:d} month {month:d}"
    )
)
def _parse_feature(
    context: dict[str, object], domain: str, dataset: str, year: int, month: int
) -> None:
    parts = layout.parse_feature_path(_path(context))
    assert parts.feature_domain == domain
    assert parts.dataset == dataset
    assert parts.year == year
    assert parts.month == month


@when(
    parsers.parse(
        'I build the lean-data dir for security_type "{security_type}" market "{market}" '
        'resolution "{resolution}" symbol "{symbol}"'
    )
)
def _build_lean(
    context: dict[str, object],
    security_type: str,
    market: str,
    resolution: str,
    symbol: str,
) -> None:
    context["path"] = layout.lean_data_dir(
        _root(context), security_type, market, resolution, symbol
    )


@then(
    parsers.parse(
        'parsing the lean-data dir yields security_type "{security_type}" market "{market}" '
        'resolution "{resolution}" symbol "{symbol}"'
    )
)
def _parse_lean(
    context: dict[str, object],
    security_type: str,
    market: str,
    resolution: str,
    symbol: str,
) -> None:
    parts = layout.parse_lean_data_dir(_path(context))
    assert parts.security_type == security_type
    assert parts.market == market
    assert parts.resolution == resolution
    assert parts.symbol == symbol


@when(
    parsers.parse(
        'I build the price path from instrument "{symbol}" resolution "{resolution}" '
        "year {year:d} month {month:d}"
    )
)
def _build_price_for(
    context: dict[str, object], symbol: str, resolution: str, year: int, month: int
) -> None:
    context["path"] = layout.price_path_for(
        _root(context), build_instrument(symbol), resolution, year, month
    )


@when(
    parsers.parse('I build the lean-data dir from instrument "{symbol}" resolution "{resolution}"')
)
def _build_lean_for(context: dict[str, object], symbol: str, resolution: str) -> None:
    context["path"] = layout.lean_data_dir_for(_root(context), build_instrument(symbol), resolution)


@when(parsers.parse('I build the raw dir for source "{source}"'))
def _build_raw(context: dict[str, object], source: str) -> None:
    context["path"] = layout.raw_dir(_root(context), source)


@when(
    parsers.parse(
        'I build the dukascopy raw path for symbol "{symbol}" '
        "year {year:d} month {month:d} day {day:d} hour {hour:d}"
    )
)
def _build_dukascopy_raw(
    context: dict[str, object], symbol: str, year: int, month: int, day: int, hour: int
) -> None:
    tick = layout.TickFile(symbol=symbol, year=year, month=month, day=day, hour=hour)
    context["path"] = layout.dukascopy_raw_path(_root(context), tick)


@then(
    parsers.parse(
        'parsing the dukascopy raw path yields symbol "{symbol}" '
        "year {year:d} month {month:d} day {day:d} hour {hour:d}"
    )
)
def _parse_dukascopy_raw(
    context: dict[str, object], symbol: str, year: int, month: int, day: int, hour: int
) -> None:
    tick = layout.parse_dukascopy_raw_path(_path(context))
    assert tick.symbol == symbol
    assert (tick.year, tick.month, tick.day, tick.hour) == (year, month, day, hour)
