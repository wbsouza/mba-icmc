"""Step definitions for gdelt.feature (pytest-bdd + respx)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from algo_download.adapters.gdelt.paths import GdeltSlot, events_url, parse_raw_path, raw_path
from algo_download.adapters.gdelt.source import GdeltSource
from algo_download.orchestrator import run
from algo_download.request import DownloadRequest
from algo_download.result import RunReport, UnitStatus
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/gdelt.feature")

_DEFAULT_PAYLOAD = b"ZIP"
_TARGET_SLOT = GdeltSlot(year=2020, month=1, day=2, hour=14, minute=30)


@pytest.fixture
def context(tmp_path: Path) -> dict[str, object]:
    """Carry scenario state and the writable data root."""
    return {"data_root": tmp_path}


def _root(context: dict[str, object]) -> Path:
    root = context["data_root"]
    assert isinstance(root, Path)
    return root


def _report(context: dict[str, object]) -> RunReport:
    report = context["report"]
    assert isinstance(report, RunReport)
    return report


def _months(spec: str) -> tuple[tuple[int, int], ...]:
    year, month = spec.split("-")
    return ((int(year), int(month)),)


def _noop(_: float) -> None:
    """No-op sleep so retry/backoff scenarios do not wait."""


def _source(context: dict[str, object]) -> GdeltSource:
    return GdeltSource(data_root=_root(context), retries=1, backoff=0.0, sleep=_noop)


def _catchall(respx_mock: respx.MockRouter) -> None:
    respx_mock.route(method="GET", host="data.gdeltproject.org").mock(
        return_value=httpx.Response(200, content=_DEFAULT_PAYLOAD)
    )


@given("a writable data root")
def _writable_root(context: dict[str, object]) -> None:
    assert _root(context).is_dir()


@given("the GDELT datafeed returns zip bytes by default")
def _default_feed(context: dict[str, object]) -> None:
    context["default"] = _DEFAULT_PAYLOAD


@given("the GDELT datafeed has no data for slot 2020-01-02 14:30")
def _no_data(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(events_url(_TARGET_SLOT)).mock(return_value=httpx.Response(200, content=b""))


@given("the GDELT datafeed always errors for slot 2020-01-02 14:30")
def _always_errors(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(events_url(_TARGET_SLOT)).mock(side_effect=httpx.ConnectError)


@given(parsers.parse('gdelt "{spec}" is already downloaded'))
def _already(context: dict[str, object], spec: str) -> None:
    request = DownloadRequest(months=_months(spec))
    for unit in _source(context).plan(request):
        unit.raw_path.parent.mkdir(parents=True, exist_ok=True)
        unit.raw_path.write_bytes(_DEFAULT_PAYLOAD)


@when(parsers.parse('I plan gdelt for "{spec}"'))
def _plan(context: dict[str, object], spec: str) -> None:
    context["units"] = list(_source(context).plan(DownloadRequest(months=_months(spec))))


@when(parsers.parse('I download gdelt for "{spec}"'))
def _download(context: dict[str, object], respx_mock: respx.MockRouter, spec: str) -> None:
    _catchall(respx_mock)
    context["report"] = run(_source(context), DownloadRequest(months=_months(spec)))


@when("I build the GDELT Events URL for slot 2020-01-02 14:30")
def _build_url(context: dict[str, object]) -> None:
    context["url"] = events_url(_TARGET_SLOT)


@when('I round-trip the raw path under "/data" for slot 2020-01-02 14:30')
def _round_trip(context: dict[str, object]) -> None:
    path = raw_path(Path("/data"), _TARGET_SLOT)
    context["parsed"] = parse_raw_path(path)


@then(parsers.parse("the plan lists {count:d} slot units"))
def _plan_count(context: dict[str, object], count: int) -> None:
    units = context["units"]
    assert isinstance(units, list)
    assert len(units) == count


@then("no HTTP request was made")
def _no_http(respx_mock: respx.MockRouter) -> None:
    assert respx_mock.calls.call_count == 0


@then("no file was written under the data root")
@then("no file is written outside the raw store")
def _nothing_outside_raw(context: dict[str, object]) -> None:
    names = {p.name for p in _root(context).iterdir()}
    assert names <= {"raw"}


@then(parsers.parse('a raw payload exists at "{rel}"'))
def _payload_exists(context: dict[str, object], rel: str) -> None:
    path = _root(context) / rel
    assert path.is_file()
    assert path.read_bytes() == _DEFAULT_PAYLOAD


@then(parsers.parse('"{rel}" exists as an empty payload'))
def _empty_payload(context: dict[str, object], rel: str) -> None:
    path = _root(context) / rel
    assert path.is_file()
    assert path.read_bytes() == b""


@then(parsers.parse('no file exists at "{rel}"'))
def _no_file(context: dict[str, object], rel: str) -> None:
    assert not (_root(context) / rel).exists()


@then("no unit is FAILED")
def _none_failed(context: dict[str, object]) -> None:
    assert _report(context).count(UnitStatus.FAILED) == 0


@then("every unit is SKIPPED")
def _all_skipped(context: dict[str, object]) -> None:
    report = _report(context)
    assert report.count(UnitStatus.SKIPPED) == len(report.results)


@then("that slot is counted MISSING")
def _slot_missing(context: dict[str, object]) -> None:
    assert _report(context).count(UnitStatus.MISSING) == 1


@then("that slot is counted FAILED")
def _slot_failed(context: dict[str, object]) -> None:
    assert _report(context).count(UnitStatus.FAILED) == 1


@then("the run exits 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert _report(context).exit_code == 0


@then("the run exits non-zero")
def _exit_nonzero(context: dict[str, object]) -> None:
    assert _report(context).exit_code != 0


@then(parsers.parse('the URL is "{url}"'))
def _url_is(context: dict[str, object], url: str) -> None:
    assert context["url"] == url


@then("the parsed slot equals the original slot")
def _parsed_slot(context: dict[str, object]) -> None:
    assert context["parsed"] == _TARGET_SLOT
