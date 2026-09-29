"""Step definitions for dukascopy_network.feature (pytest-bdd, opt-in @network).

The @network tag on the feature maps to ``pytest.mark.network`` and is excluded
from the default gate (addopts ``-m 'not network and not integration'``). Run
on demand with ``uv run pytest -m network``.
"""

from __future__ import annotations

import lzma
import struct
from pathlib import Path

from algo_download.adapters.dukascopy.paths import TickFile, raw_path
from algo_download.adapters.dukascopy.source import DukascopySource
from algo_download.result import DownloadUnit, UnitStatus
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/dukascopy_network.feature")

_RECORD = 20  # bytes per tick: >IIIff (ms, ask, bid, askvol, bidvol)


def _unit(root: Path, tick: TickFile) -> DownloadUnit:
    """Build a DownloadUnit at the canonical raw path for ``tick``."""
    key = f"{tick.symbol} {tick.year}-{tick.month:02d}-{tick.day:02d} {tick.hour:02d}h"
    return DownloadUnit(key=key, raw_path=raw_path(root, tick))


@given("a Dukascopy source against the live feed")
def _source(context: dict[str, object], tmp_path: Path) -> None:
    context["root"] = tmp_path
    context["source"] = DukascopySource(data_root=tmp_path)  # real httpx + real feed


@when(parsers.parse("I fetch the real EURUSD hour {year:d}-{month:d}-{day:d} {hour:d}h"))
def _fetch_real(
    context: dict[str, object], year: int, month: int, day: int, hour: int
) -> None:
    root = context["root"]
    source = context["source"]
    assert isinstance(root, Path)
    assert isinstance(source, DukascopySource)
    unit = _unit(root, TickFile(symbol="EURUSD", year=year, month=month, day=day, hour=hour))
    context["data_unit"] = unit
    context["data_result"] = source.fetch(unit)


@when(parsers.parse("I fetch the weekend EURUSD hour {year:d}-{month:d}-{day:d} {hour:d}h"))
def _fetch_weekend(
    context: dict[str, object], year: int, month: int, day: int, hour: int
) -> None:
    root = context["root"]
    source = context["source"]
    assert isinstance(root, Path)
    assert isinstance(source, DukascopySource)
    unit = _unit(root, TickFile(symbol="EURUSD", year=year, month=month, day=day, hour=hour))
    context["wknd_unit"] = unit
    context["wknd_result"] = source.fetch(unit)


@then("the hour status is WRITTEN with a positive byte count")
def _written(context: dict[str, object]) -> None:
    result = context["data_result"]
    assert result.status is UnitStatus.WRITTEN  # type: ignore[union-attr]
    assert result.bytes > 0  # type: ignore[union-attr]


@then(parsers.parse('the raw path is "{rel}"'))
def _raw_path(context: dict[str, object], rel: str) -> None:
    root = context["root"]
    unit = context["data_unit"]
    assert isinstance(root, Path)
    assert isinstance(unit, DownloadUnit)
    assert unit.raw_path == root / rel


@then("the payload decompresses to whole 20-byte tick records")
def _decompresses(context: dict[str, object]) -> None:
    unit = context["data_unit"]
    assert isinstance(unit, DownloadUnit)
    raw = lzma.decompress(unit.raw_path.read_bytes())
    assert raw and len(raw) % _RECORD == 0
    context["raw"] = raw


@then("the first record has a plausible EURUSD level with bid no greater than ask")
def _plausible(context: dict[str, object]) -> None:
    raw = context["raw"]
    assert isinstance(raw, bytes)
    _ms, ask, bid, _av, _bv = struct.unpack(">IIIff", raw[:_RECORD])
    assert 0.5 < ask * 1e-5 < 2.0  # plausible EUR/USD level
    assert bid <= ask


@then("the hour status is MISSING with an empty marker persisted")
def _missing(context: dict[str, object]) -> None:
    result = context["wknd_result"]
    unit = context["wknd_unit"]
    assert result.status is UnitStatus.MISSING  # type: ignore[union-attr]
    assert isinstance(unit, DownloadUnit)
    assert unit.raw_path.exists()  # empty marker persisted


@then("both hours are now done on disk")
def _done(context: dict[str, object]) -> None:
    source = context["source"]
    assert isinstance(source, DukascopySource)
    assert source.is_done(context["data_unit"])  # type: ignore[arg-type]
    assert source.is_done(context["wknd_unit"])  # type: ignore[arg-type]
