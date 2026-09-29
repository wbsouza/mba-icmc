"""Step definitions for gdelt_ngrams.feature (pytest-bdd + respx)."""

from __future__ import annotations

from pathlib import Path

import httpx
import respx
from algo_download.adapters.gdelt_ngrams.paths import (
    GdeltNgramsMinute,
    ngrams_url,
    parse_raw_path,
    raw_path,
)
from algo_download.adapters.gdelt_ngrams.source import GdeltNgramsSource, unit_for_minute
from algo_download.orchestrator import run
from algo_download.request import DownloadRequest
from algo_download.result import DownloadUnit, RunReport, UnitResult, UnitStatus
from pytest_bdd import given, parsers, scenarios, then, when
from structlog.testing import capture_logs

scenarios("../features/gdelt_ngrams.feature")

_DEFAULT_PAYLOAD = b"GZIP"
_TARGET_MINUTE = GdeltNgramsMinute(year=2020, month=1, day=2, hour=14, minute=34)


def _minute(spec: str) -> GdeltNgramsMinute:
    date, time_ = spec.split(" ")
    year, month, day = (int(part) for part in date.split("-"))
    hour, minute = (int(part) for part in time_.split(":"))
    return GdeltNgramsMinute(year=year, month=month, day=day, hour=hour, minute=minute)


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


def _source(context: dict[str, object]) -> GdeltNgramsSource:
    source = GdeltNgramsSource(data_root=_root(context), retries=1, backoff=0.0, sleep=_noop)
    calls: list[None] = []
    original_wait = source._throttle.wait

    def _counting_wait() -> None:
        calls.append(None)
        original_wait()

    source._throttle.wait = _counting_wait  # type: ignore[method-assign]
    context["throttle_calls"] = calls
    return source


def _catchall(respx_mock: respx.MockRouter) -> None:
    respx_mock.route(method="GET", host="data.gdeltproject.org").mock(
        return_value=httpx.Response(200, content=_DEFAULT_PAYLOAD)
    )


@given("a writable data root")
def _writable_root(context: dict[str, object], tmp_path: Path) -> None:
    context["data_root"] = tmp_path
    assert _root(context).is_dir()


@given("the GDELT NGrams datafeed returns gzip bytes by default")
def _default_feed(context: dict[str, object]) -> None:
    context["default"] = _DEFAULT_PAYLOAD


@given("the GDELT NGrams datafeed has no data for minute 2020-01-02 14:34")
def _no_data(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ngrams_url(_TARGET_MINUTE)).mock(return_value=httpx.Response(404, content=b""))


@given("the GDELT NGrams datafeed always errors for minute 2020-01-02 14:34")
def _always_errors(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ngrams_url(_TARGET_MINUTE)).mock(side_effect=httpx.ConnectError)


@given(parsers.re(r'gdelt_ngrams "(?P<spec>\d{4}-\d{2})" is already downloaded'))
def _already(context: dict[str, object], spec: str) -> None:
    request = DownloadRequest(months=_months(spec))
    for unit in _source(context).plan(request):
        unit.raw_path.parent.mkdir(parents=True, exist_ok=True)
        unit.raw_path.write_bytes(_DEFAULT_PAYLOAD)


@when(parsers.re(r'I plan gdelt_ngrams for "(?P<spec>\d{4}-\d{2})"'))
def _plan(context: dict[str, object], spec: str) -> None:
    context["units"] = list(_source(context).plan(DownloadRequest(months=_months(spec))))


@when(parsers.re(r'I download gdelt_ngrams for "(?P<spec>\d{4}-\d{2})"'))
def _download(context: dict[str, object], respx_mock: respx.MockRouter, spec: str) -> None:
    _catchall(respx_mock)
    with capture_logs() as logs:
        context["report"] = run(_source(context), DownloadRequest(months=_months(spec)))
    context["logs"] = logs


@when("I build the GDELT NGrams URL for minute 2020-01-02 14:34")
def _build_url(context: dict[str, object]) -> None:
    context["url"] = ngrams_url(_TARGET_MINUTE)


@when("I construct a GdeltNgramsSource with an explicit client, backoff, sleep, and min interval")
def _construct_explicit(context: dict[str, object], tmp_path: Path) -> None:
    client = httpx.Client()
    context["given_client"] = client
    context["given_sleep"] = _noop
    context["source"] = GdeltNgramsSource(
        data_root=tmp_path,
        client=client,
        retries=1,
        backoff=5.0,
        sleep=_noop,
        min_interval=5.0,
    )


@when("I construct a GdeltNgramsSource with no overrides")
def _construct_defaults(context: dict[str, object], tmp_path: Path) -> None:
    context["source"] = GdeltNgramsSource(data_root=tmp_path)


@when("I fetch gdelt_ngrams minute 2020-01-02 14:34 directly")
def _fetch_directly(context: dict[str, object]) -> None:
    source = _source(context)
    unit = unit_for_minute(_root(context), _TARGET_MINUTE)
    context["fetch_unit"] = unit
    with capture_logs() as logs:
        context["fetch_result"] = source.fetch(unit)
    context["logs"] = logs


@when(parsers.re(r'I round-trip the raw path under "(?P<root>[^"]+)" for minute (?P<spec>.+)'))
def _round_trip(context: dict[str, object], root: str, spec: str) -> None:
    path = raw_path(Path(root), _minute(spec))
    context["parsed"] = parse_raw_path(path)


@then(parsers.re(r"the plan lists (?P<count>\d+) minute units"))
def _plan_count(context: dict[str, object], count: str) -> None:
    units = context["units"]
    assert isinstance(units, list)
    assert len(units) == int(count)


@then("no HTTP request was made")
def _no_http(respx_mock: respx.MockRouter) -> None:
    assert respx_mock.calls.call_count == 0


@then("no file was written under the data root")
@then("no file is written outside the raw store")
def _nothing_outside_raw(context: dict[str, object]) -> None:
    names = {p.name for p in _root(context).iterdir()}
    assert names <= {"raw"}


@then(parsers.re(r'a raw payload exists at "(?P<rel>[^"]+)"'))
def _payload_exists(context: dict[str, object], rel: str) -> None:
    path = _root(context) / rel
    assert path.is_file()
    assert path.read_bytes() == _DEFAULT_PAYLOAD


@then(parsers.re(r'"(?P<rel>[^"]+)" exists as an empty payload'))
def _empty_payload(context: dict[str, object], rel: str) -> None:
    path = _root(context) / rel
    assert path.is_file()
    assert path.read_bytes() == b""


@then(parsers.re(r'no file exists at "(?P<rel>[^"]+)"'))
def _no_file(context: dict[str, object], rel: str) -> None:
    assert not (_root(context) / rel).exists()


@then("no unit is FAILED")
def _none_failed(context: dict[str, object]) -> None:
    assert _report(context).count(UnitStatus.FAILED) == 0


@then("every unit is SKIPPED")
def _all_skipped(context: dict[str, object]) -> None:
    report = _report(context)
    assert report.count(UnitStatus.SKIPPED) == len(report.results)


@then("that minute is counted MISSING")
def _minute_missing(context: dict[str, object]) -> None:
    assert _report(context).count(UnitStatus.MISSING) == 1


@then("that minute is counted FAILED")
def _minute_failed(context: dict[str, object]) -> None:
    assert _report(context).count(UnitStatus.FAILED) == 1


@then("the run exits 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert _report(context).exit_code == 0


@then("the run exits non-zero")
def _exit_nonzero(context: dict[str, object]) -> None:
    assert _report(context).exit_code != 0


@then(parsers.re(r'the URL is "(?P<url>[^"]+)"'))
def _url_is(context: dict[str, object], url: str) -> None:
    assert context["url"] == url


@then(parsers.re(r"the parsed minute equals (?P<spec>.+)"))
def _parsed_minute(context: dict[str, object], spec: str) -> None:
    assert context["parsed"] == _minute(spec)


@then("the written unit's recorded byte count matches the payload")
def _bytes_recorded(context: dict[str, object]) -> None:
    written = [r for r in _report(context).results if r.status is UnitStatus.WRITTEN]
    assert written
    assert all(r.bytes == len(_DEFAULT_PAYLOAD) for r in written)


@then(
    parsers.re(r'the failure is logged once as "(?P<event>[a-z_]+)" with the unit, url, and error')
)
def _failure_logged(context: dict[str, object], event: str) -> None:
    logs = context["logs"]
    assert isinstance(logs, list)
    matches = [entry for entry in logs if entry.get("event") == event]
    assert len(matches) == 1
    entry = matches[0]
    assert entry["source"] == "gdelt_ngrams"
    assert entry["unit"] == "gdelt_ngrams 2020-01-02 14:34"
    assert entry["url"] == ngrams_url(_TARGET_MINUTE)
    assert entry["error"] and "Error" in entry["error"]


@then("the source uses the explicit client, backoff, sleep, and min interval")
def _explicit_overrides_took_effect(context: dict[str, object]) -> None:
    source = context["source"]
    assert isinstance(source, GdeltNgramsSource)
    assert source._client is context["given_client"]
    assert source._backoff == 5.0
    assert source._sleep is context["given_sleep"]
    assert source._throttle._min_interval == 5.0


@then("the source builds its own client at the default timeout")
def _default_client_timeout(context: dict[str, object]) -> None:
    source = context["source"]
    assert isinstance(source, GdeltNgramsSource)
    assert source._client.timeout == httpx.Timeout(30.0)


@then("the direct fetch result is FAILED with zero bytes")
def _direct_result_failed(context: dict[str, object]) -> None:
    result = context["fetch_result"]
    unit = context["fetch_unit"]
    assert isinstance(result, UnitResult)
    assert isinstance(unit, DownloadUnit)
    assert result == UnitResult(unit=unit, status=UnitStatus.FAILED, bytes=0)


@then("the request throttle waited before every attempt")
def _throttle_waited(context: dict[str, object]) -> None:
    calls = context["throttle_calls"]
    assert isinstance(calls, list)
    assert len(calls) == 2  # retries=1 -> 2 attempts, one throttle wait before each
