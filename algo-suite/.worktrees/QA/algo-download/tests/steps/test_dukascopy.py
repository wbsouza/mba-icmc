"""Step definitions for dukascopy.feature (pytest-bdd + respx).

The datafeed is fully mocked (respx) — no live network. Scenario-specific routes
are registered before the catch-all so they take precedence.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx
from algo_download.adapters.dukascopy.paths import TickFile, bi5_url
from algo_download.adapters.dukascopy.source import DukascopySource
from algo_download.orchestrator import run
from algo_download.request import DownloadRequest
from algo_download.result import RunReport, UnitStatus
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/dukascopy.feature")

_DEFAULT_PAYLOAD = b"TICKS"


@pytest.fixture
def context(tmp_path: Path) -> dict[str, object]:
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
    """No-op sleep so retry/backoff scenarios don't actually wait."""


def _build_source(context: dict[str, object]) -> DukascopySource:
    return DukascopySource(data_root=_root(context), retries=1, backoff=0.0, sleep=_noop)


def _catchall(respx_mock: respx.MockRouter) -> None:
    respx_mock.route(method="GET", host="datafeed.dukascopy.com").mock(
        return_value=httpx.Response(200, content=_DEFAULT_PAYLOAD)
    )


@given("a writable data root")
def _writable_root(context: dict[str, object]) -> None:
    assert _root(context).is_dir()


@given("the Dukascopy datafeed returns tick bytes by default")
def _default_feed(context: dict[str, object]) -> None:
    context["default"] = _DEFAULT_PAYLOAD


@given(
    parsers.parse('the datafeed has no data for "{symbol}" {year:d}-{month:d}-{day:d} {hour:d}h')
)
def _no_data(
    context: dict[str, object],
    respx_mock: respx.MockRouter,
    symbol: str,
    year: int,
    month: int,
    day: int,
    hour: int,
) -> None:
    url = bi5_url(TickFile(symbol=symbol, year=year, month=month, day=day, hour=hour))
    respx_mock.get(url).mock(return_value=httpx.Response(404))


@given(
    parsers.parse('the datafeed always errors for "{symbol}" {year:d}-{month:d}-{day:d} {hour:d}h')
)
def _always_errors(
    context: dict[str, object],
    respx_mock: respx.MockRouter,
    symbol: str,
    year: int,
    month: int,
    day: int,
    hour: int,
) -> None:
    url = bi5_url(TickFile(symbol=symbol, year=year, month=month, day=day, hour=hour))
    respx_mock.get(url).mock(side_effect=httpx.ConnectError)


@given(parsers.parse('"{symbol}" "{spec}" is already downloaded'))
def _already(context: dict[str, object], symbol: str, spec: str) -> None:
    request = DownloadRequest(symbol=symbol, months=_months(spec))
    for unit in _build_source(context).plan(request):
        unit.raw_path.parent.mkdir(parents=True, exist_ok=True)
        unit.raw_path.write_bytes(_DEFAULT_PAYLOAD)


@when(parsers.parse('I plan dukascopy "{symbol}" for "{spec}"'))
def _plan(context: dict[str, object], symbol: str, spec: str) -> None:
    source = _build_source(context)
    request = DownloadRequest(symbol=symbol, months=_months(spec))
    context["units"] = list(source.plan(request))


@when(parsers.parse('I download dukascopy "{symbol}" for "{spec}"'))
def _download(
    context: dict[str, object], respx_mock: respx.MockRouter, symbol: str, spec: str
) -> None:
    _catchall(respx_mock)
    context["report"] = run(
        _build_source(context), DownloadRequest(symbol=symbol, months=_months(spec))
    )


@then(parsers.parse("the plan lists {count:d} hour units"))
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


@then(parsers.parse("that hour is counted {status}"))
def _counted(context: dict[str, object], status: str) -> None:
    assert _report(context).count(UnitStatus(status.lower())) == 1


@then("no unit is FAILED")
def _none_failed(context: dict[str, object]) -> None:
    assert _report(context).count(UnitStatus.FAILED) == 0


@then("every unit is SKIPPED")
def _all_skipped(context: dict[str, object]) -> None:
    report = _report(context)
    assert report.count(UnitStatus.SKIPPED) == len(report.results)


@then("the run exits 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert _report(context).exit_code == 0


@then("the run exits non-zero")
def _exit_nonzero(context: dict[str, object]) -> None:
    assert _report(context).exit_code != 0
