"""Step definitions for orchestrator.feature (pytest-bdd).

The orchestrator is exercised with an in-memory fake source so the test covers
only orchestration logic — plan/skip/fetch/aggregate — with no network or disk.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from algo_download.orchestrator import run
from algo_download.request import DownloadRequest
from algo_download.result import DownloadUnit, RunReport, UnitResult, UnitStatus
from algo_download.source import DataSource
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/orchestrator.feature")


class FakeSource(DataSource):
    """A source whose per-unit behavior is scripted by the scenario."""

    name = "fake"

    def __init__(self, behavior: dict[int, str]) -> None:
        self._behaviour = behavior
        self.visited: list[str] = []

    def plan(self, request: DownloadRequest) -> Iterator[DownloadUnit]:
        for i in sorted(self._behaviour):
            yield DownloadUnit(key=f"u{i}", raw_path=Path(f"/tmp/u{i}.raw"))

    def is_done(self, unit: DownloadUnit) -> bool:
        self.visited.append(unit.key)
        return self._behaviour[int(unit.key[1:])] == "disk"

    def fetch(self, unit: DownloadUnit) -> UnitResult:
        self.visited.append(unit.key)
        spec = self._behaviour[int(unit.key[1:])]
        if spec == "raise":
            raise RuntimeError(f"boom on {unit.key}")
        status = UnitStatus(spec)
        size = 7 if status is UnitStatus.WRITTEN else 0
        return UnitResult(unit=unit, status=status, bytes=size)


@pytest.fixture
def context() -> dict[str, object]:
    return {"behavior": {}}


def _behaviour(context: dict[str, object]) -> dict[int, str]:
    behavior = context["behavior"]
    assert isinstance(behavior, dict)
    return behavior


def _report(context: dict[str, object]) -> RunReport:
    report = context["report"]
    assert isinstance(report, RunReport)
    return report


@given(parsers.parse("a source planning {count:d} units"))
def _plan_units(context: dict[str, object], count: int) -> None:
    _behaviour(context).update({i: "written" for i in range(1, count + 1)})


@given(parsers.parse("unit {n:d} is already on disk"))
def _on_disk(context: dict[str, object], n: int) -> None:
    _behaviour(context)[n] = "disk"


@given(parsers.parse('unit {n:d} fetches "{status}"'))
def _fetches(context: dict[str, object], n: int, status: str) -> None:
    _behaviour(context)[n] = status


@given(parsers.parse("unit {n:d} raises an unexpected error"))
def _raises(context: dict[str, object], n: int) -> None:
    _behaviour(context)[n] = "raise"


@when("I run the download")
def _run(context: dict[str, object]) -> None:
    source = FakeSource(_behaviour(context))
    context["source"] = source
    context["report"] = run(source, DownloadRequest(symbol="EURUSD", months=((2020, 1),)))


@then(
    parsers.parse(
        "the report is written={written:d} skipped={skipped:d} "
        "missing={missing:d} failed={failed:d}"
    )
)
def _report_counts(
    context: dict[str, object], written: int, skipped: int, missing: int, failed: int
) -> None:
    report = _report(context)
    assert report.count(UnitStatus.WRITTEN) == written
    assert report.count(UnitStatus.SKIPPED) == skipped
    assert report.count(UnitStatus.MISSING) == missing
    assert report.count(UnitStatus.FAILED) == failed


@then("every planned unit was visited")
def _all_visited(context: dict[str, object]) -> None:
    source = context["source"]
    assert isinstance(source, FakeSource)
    assert set(source.visited) == {"u1", "u2", "u3"}


@then("the exit code is 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert _report(context).exit_code == 0


@then("the exit code is non-zero")
def _exit_nonzero(context: dict[str, object]) -> None:
    assert _report(context).exit_code != 0
