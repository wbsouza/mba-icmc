"""Step definitions for gdelt_network.feature (pytest-bdd, opt-in @network)."""

from __future__ import annotations

import zipfile
from pathlib import Path

from algo_download.adapters.gdelt.paths import GdeltSlot, raw_path
from algo_download.adapters.gdelt.source import GdeltSource
from algo_download.result import DownloadUnit, UnitResult, UnitStatus
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/gdelt_network.feature")


def _unit(root: Path, slot: GdeltSlot) -> DownloadUnit:
    """Build a DownloadUnit at the canonical raw path for ``slot``."""
    key = f"gdelt {slot.year:04d}-{slot.month:02d}-{slot.day:02d} {slot.hour:02d}:{slot.minute:02d}"
    return DownloadUnit(key=key, raw_path=raw_path(root, slot))


def _source(context: dict[str, object]) -> GdeltSource:
    source = context["source"]
    assert isinstance(source, GdeltSource)
    return source


def _root(context: dict[str, object]) -> Path:
    root = context["root"]
    assert isinstance(root, Path)
    return root


def _result(context: dict[str, object], name: str) -> UnitResult:
    result = context[name]
    assert isinstance(result, UnitResult)
    return result


@given("a GDELT source against the live feed")
def _live_source(context: dict[str, object], tmp_path: Path) -> None:
    context["root"] = tmp_path
    context["source"] = GdeltSource(data_root=tmp_path)


@when(
    parsers.parse(
        "I fetch the real Events slot {year:d}-{month:d}-{day:d} {hour:d}:{minute:d}"
    )
)
def _fetch_real(
    context: dict[str, object], year: int, month: int, day: int, hour: int, minute: int
) -> None:
    slot = GdeltSlot(year=year, month=month, day=day, hour=hour, minute=minute)
    unit = _unit(_root(context), slot)
    context["data_unit"] = unit
    context["data_result"] = _source(context).fetch(unit)


@when(
    parsers.parse(
        "I fetch the out-of-coverage slot {year:d}-{month:d}-{day:d} {hour:d}:{minute:d}"
    )
)
def _fetch_missing(
    context: dict[str, object], year: int, month: int, day: int, hour: int, minute: int
) -> None:
    slot = GdeltSlot(year=year, month=month, day=day, hour=hour, minute=minute)
    unit = _unit(_root(context), slot)
    context["missing_unit"] = unit
    context["missing_result"] = _source(context).fetch(unit)


@then("the slot status is WRITTEN with a positive byte count")
def _written(context: dict[str, object]) -> None:
    result = _result(context, "data_result")
    assert result.status is UnitStatus.WRITTEN
    assert result.bytes > 0


@then(parsers.parse('the raw path is "{rel}"'))
def _raw_path(context: dict[str, object], rel: str) -> None:
    unit = context["data_unit"]
    assert isinstance(unit, DownloadUnit)
    assert unit.raw_path == _root(context) / rel


@then(parsers.parse('the payload is a zip containing exactly one CSV named "{name}"'))
def _zip_contains(context: dict[str, object], name: str) -> None:
    unit = context["data_unit"]
    assert isinstance(unit, DownloadUnit)
    with zipfile.ZipFile(unit.raw_path) as archive:
        assert archive.namelist() == [name]


@then("the slot status is MISSING with an empty marker persisted")
def _missing(context: dict[str, object]) -> None:
    result = _result(context, "missing_result")
    unit = context["missing_unit"]
    assert result.status is UnitStatus.MISSING
    assert isinstance(unit, DownloadUnit)
    assert unit.raw_path.exists()
    assert unit.raw_path.read_bytes() == b""


@then("both slots are now done on disk")
def _both_done(context: dict[str, object]) -> None:
    source = _source(context)
    assert source.is_done(context["data_unit"])  # type: ignore[arg-type]
    assert source.is_done(context["missing_unit"])  # type: ignore[arg-type]
