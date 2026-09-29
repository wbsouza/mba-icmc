"""Step definitions for gpr_network.feature (pytest-bdd, opt-in @network)."""

from __future__ import annotations

from pathlib import Path

from algo_download.adapters.gpr.paths import raw_path
from algo_download.adapters.gpr.source import GprSource
from algo_download.orchestrator import run
from algo_download.request import DownloadRequest
from algo_download.result import DownloadUnit, RunReport, UnitStatus
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/gpr_network.feature")


def _source(context: dict[str, object]) -> GprSource:
    source = context["source"]
    assert isinstance(source, GprSource)
    return source


def _root(context: dict[str, object]) -> Path:
    root = context["root"]
    assert isinstance(root, Path)
    return root


def _unit(context: dict[str, object]) -> DownloadUnit:
    unit = context["unit"]
    assert isinstance(unit, DownloadUnit)
    return unit


def _report(context: dict[str, object]) -> RunReport:
    report = context["report"]
    assert isinstance(report, RunReport)
    return report


@given("a GPR source against the live feed")
def _live_source(context: dict[str, object], tmp_path: Path) -> None:
    context["root"] = tmp_path
    context["source"] = GprSource(data_root=tmp_path)


@when("I fetch the real GPR index")
def _fetch_real(context: dict[str, object]) -> None:
    unit = DownloadUnit(key="gpr data_gpr_export.xls", raw_path=raw_path(_root(context)))
    context["unit"] = unit
    context["result"] = _source(context).fetch(unit)


@when("I download gpr again")
def _download_again(context: dict[str, object]) -> None:
    context["report"] = run(_source(context), DownloadRequest())


@then("the unit status is WRITTEN with a positive byte count")
def _written(context: dict[str, object]) -> None:
    result = context["result"]
    assert result.status is UnitStatus.WRITTEN  # type: ignore[union-attr]
    assert result.bytes > 0  # type: ignore[union-attr]


@then(parsers.parse('the raw path is "{rel}"'))
def _raw_path(context: dict[str, object], rel: str) -> None:
    assert _unit(context).raw_path == _root(context) / rel


@then("the payload is a non-empty Excel file")
def _excel_file(context: dict[str, object]) -> None:
    payload = _unit(context).raw_path.read_bytes()
    assert payload
    assert payload[:2] in {b"PK", b"\xd0\xcf"}


@then("the unit is now SKIPPED")
def _skipped(context: dict[str, object]) -> None:
    report = _report(context)
    assert report.count(UnitStatus.SKIPPED) == 1
    assert report.exit_code == 0
