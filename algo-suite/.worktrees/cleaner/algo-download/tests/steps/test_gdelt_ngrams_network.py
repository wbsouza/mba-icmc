"""Step definitions for gdelt_ngrams_network.feature (pytest-bdd, opt-in @network)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from algo_download.adapters.gdelt_ngrams.paths import GdeltNgramsMinute
from algo_download.adapters.gdelt_ngrams.source import GdeltNgramsSource, unit_for_minute
from algo_download.result import DownloadUnit, UnitResult, UnitStatus
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/gdelt_ngrams_network.feature")


def _unit(root: Path, minute: GdeltNgramsMinute) -> DownloadUnit:
    """Build a DownloadUnit at the canonical raw path for ``minute``."""
    return unit_for_minute(root, minute)


def _source(context: dict[str, object]) -> GdeltNgramsSource:
    source = context["source"]
    assert isinstance(source, GdeltNgramsSource)
    return source


def _root(context: dict[str, object]) -> Path:
    root = context["root"]
    assert isinstance(root, Path)
    return root


def _result(context: dict[str, object], name: str) -> UnitResult:
    result = context[name]
    assert isinstance(result, UnitResult)
    return result


@given("a GDELT NGrams source against the live feed")
def _live_source(context: dict[str, object], tmp_path: Path) -> None:
    context["root"] = tmp_path
    context["source"] = GdeltNgramsSource(data_root=tmp_path)


@when(
    parsers.re(
        r"I fetch the real minute (?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}) "
        r"(?P<hour>\d{2}):(?P<minute>\d{2})"
    )
)
def _fetch_real(
    context: dict[str, object], year: str, month: str, day: str, hour: str, minute: str
) -> None:
    target = GdeltNgramsMinute(
        year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute)
    )
    unit = _unit(_root(context), target)
    context["data_unit"] = unit
    context["data_result"] = _source(context).fetch(unit)


@when(
    parsers.re(
        r"I fetch the out-of-coverage minute "
        r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}) "
        r"(?P<hour>\d{2}):(?P<minute>\d{2})"
    )
)
def _fetch_missing(
    context: dict[str, object], year: str, month: str, day: str, hour: str, minute: str
) -> None:
    target = GdeltNgramsMinute(
        year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute)
    )
    unit = _unit(_root(context), target)
    context["missing_unit"] = unit
    context["missing_result"] = _source(context).fetch(unit)


@then("the minute status is WRITTEN with a positive byte count")
def _written(context: dict[str, object]) -> None:
    result = _result(context, "data_result")
    assert result.status is UnitStatus.WRITTEN
    assert result.bytes > 0


@then(parsers.re(r'the raw path is "(?P<rel>[^"]+)"'))
def _raw_path(context: dict[str, object], rel: str) -> None:
    unit = context["data_unit"]
    assert isinstance(unit, DownloadUnit)
    assert unit.raw_path == _root(context) / rel


@then(parsers.re(r'the payload is gzip-compressed JSON-lines with fields "(?P<fields>[^"]+)"'))
def _gzip_jsonl(context: dict[str, object], fields: str) -> None:
    unit = context["data_unit"]
    assert isinstance(unit, DownloadUnit)
    first_line = gzip.decompress(unit.raw_path.read_bytes()).splitlines()[0]
    assert set(json.loads(first_line)) == {field.strip() for field in fields.split(",")}


@then("the minute status is MISSING with an empty marker persisted")
def _missing(context: dict[str, object]) -> None:
    result = _result(context, "missing_result")
    unit = context["missing_unit"]
    assert result.status is UnitStatus.MISSING
    assert isinstance(unit, DownloadUnit)
    assert unit.raw_path.exists()
    assert unit.raw_path.read_bytes() == b""


@then("both minutes are now done on disk")
def _both_done(context: dict[str, object]) -> None:
    source = _source(context)
    assert source.is_done(context["data_unit"])  # type: ignore[arg-type]
    assert source.is_done(context["missing_unit"])  # type: ignore[arg-type]
