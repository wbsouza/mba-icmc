"""Step definitions for gpr.feature (pytest-bdd + respx)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from algo_download.adapters.gpr.paths import GPR_URL, raw_path
from algo_download.adapters.gpr.source import GprSource
from algo_download.orchestrator import run
from algo_download.request import DownloadRequest
from algo_download.result import RunReport, UnitStatus
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/gpr.feature")

_DEFAULT_PAYLOAD = b"XLS"


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


def _source(context: dict[str, object]) -> GprSource:
    return GprSource(data_root=_root(context), retries=1, backoff=0.0, sleep=lambda _: None)


def _catchall(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(GPR_URL).mock(return_value=httpx.Response(200, content=_DEFAULT_PAYLOAD))


@given("a writable data root")
def _writable_root(context: dict[str, object]) -> None:
    assert _root(context).is_dir()


@given("the GPR datafeed returns index bytes by default")
def _default_feed(context: dict[str, object]) -> None:
    context["default"] = _DEFAULT_PAYLOAD


@given("the GPR datafeed always errors")
def _always_errors(context: dict[str, object], respx_mock: respx.MockRouter) -> None:
    context["feed_overridden"] = True
    respx_mock.get(GPR_URL).mock(side_effect=httpx.ConnectError)


@given("gpr is already downloaded")
def _already(context: dict[str, object]) -> None:
    path = raw_path(_root(context))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_DEFAULT_PAYLOAD)


@when("I plan gpr")
def _plan(context: dict[str, object]) -> None:
    context["units"] = list(_source(context).plan(DownloadRequest()))


@when("I download gpr")
def _download(context: dict[str, object], respx_mock: respx.MockRouter) -> None:
    if not context.get("feed_overridden"):
        _catchall(respx_mock)
    context["report"] = run(_source(context), DownloadRequest())


@when("I build the GPR URL")
def _build_url(context: dict[str, object]) -> None:
    context["url"] = GPR_URL


@then(parsers.parse("the plan lists {count:d} unit"))
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


@then("the unit is counted FAILED")
def _unit_failed(context: dict[str, object]) -> None:
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
