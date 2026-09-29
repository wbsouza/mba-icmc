"""Step definitions for dukascopy_retry.feature (pytest-bdd).

The adapter's retry/backoff/throttle is exercised with injected fake clients
(no network, no respx), mirroring the original narrow unit tests.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from algo_download.adapters.dukascopy.source import DukascopySource
from algo_download.result import DownloadUnit, UnitStatus
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/dukascopy_retry.feature")


class FlakyClient:
    """An httpx-like client that fails ``fail_times`` then returns 200."""

    def __init__(self, fail_times: int, content: bytes) -> None:
        self._fail_times = fail_times
        self._content = content
        self.attempts = 0

    def get(self, url: str) -> httpx.Response:
        """Raise a ConnectError until the fail budget is spent, then return 200."""
        self.attempts += 1
        if self.attempts <= self._fail_times:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, content=self._content, request=httpx.Request("GET", url))


class StatusClient:
    """An httpx-like client that always returns a fixed status code."""

    def __init__(self, code: int) -> None:
        self._code = code
        self.attempts = 0

    def get(self, url: str) -> httpx.Response:
        """Return the fixed status code, counting each attempt."""
        self.attempts += 1
        return httpx.Response(self._code, request=httpx.Request("GET", url))


class OkClient:
    """An httpx-like client that always returns 200 with tick bytes."""

    def get(self, url: str) -> httpx.Response:
        """Return 200 with the canonical tick payload."""
        return httpx.Response(200, content=b"TICKS", request=httpx.Request("GET", url))


def _unit(tmp_path: Path, hour: int = 14) -> DownloadUnit:
    """Build the canonical EURUSD download unit for the given hour."""
    path = tmp_path / f"raw/dukascopy/EURUSD/2020/01/02/{hour:02d}h.bi5"
    return DownloadUnit(key=f"EURUSD 2020-01-02 {hour:02d}h", raw_path=path)


@given(
    parsers.parse('a client that fails {fail_times:d} times then returns 200 with "{content}"')
)
def _flaky(context: dict[str, object], fail_times: int, content: str) -> None:
    context["client"] = FlakyClient(fail_times=fail_times, content=content.encode())


@given(parsers.parse("a client that always returns HTTP {code:d}"))
def _status(context: dict[str, object], code: int) -> None:
    context["client"] = StatusClient(code)


@given(parsers.parse("the source retries {retries:d} times with no backoff"))
def _retries(context: dict[str, object], tmp_path: Path, retries: int) -> None:
    context["source"] = DukascopySource(
        data_root=tmp_path,
        client=context["client"],
        retries=retries,
        backoff=0.0,
        sleep=lambda _: None,
    )


@given(parsers.parse("an always-OK client and a {interval:g}s minimum interval"))
def _throttled(context: dict[str, object], tmp_path: Path, interval: float) -> None:
    waits: list[float] = []
    context["waits"] = waits
    context["source"] = DukascopySource(
        data_root=tmp_path,
        client=OkClient(),
        retries=0,
        min_interval=interval,
        sleep=waits.append,
    )


@given(parsers.parse('the env ALGO_DUKASCOPY_MIN_INTERVAL is "{value}"'))
def _env(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("ALGO_DUKASCOPY_MIN_INTERVAL", value)


@when("the source fetches the EURUSD 14h unit")
def _fetch(context: dict[str, object], tmp_path: Path) -> None:
    source = context["source"]
    assert isinstance(source, DukascopySource)
    context["unit"] = _unit(tmp_path)
    context["result"] = source.fetch(context["unit"])


@when("the source fetches the EURUSD 14h and 15h units in turn")
def _fetch_two(context: dict[str, object], tmp_path: Path) -> None:
    source = context["source"]
    assert isinstance(source, DukascopySource)
    for hour in (14, 15):
        source.fetch(_unit(tmp_path, hour))


@when("I construct a Dukascopy source with an always-OK client")
def _construct(context: dict[str, object], tmp_path: Path) -> None:
    try:
        DukascopySource(data_root=tmp_path, client=OkClient())
    except ValueError as exc:
        context["error"] = exc


@then(parsers.parse("the client was called {attempts:d} times"))
def _attempts(context: dict[str, object], attempts: int) -> None:
    client = context["client"]
    assert isinstance(client, FlakyClient | StatusClient)
    assert client.attempts == attempts


@then(parsers.parse("the unit status is {status}"))
def _status_is(context: dict[str, object], status: str) -> None:
    result = context["result"]
    assert result.status is UnitStatus[status]  # type: ignore[union-attr]


@then(parsers.parse('the raw payload bytes are "{content}"'))
def _payload(context: dict[str, object], content: str) -> None:
    result = context["result"]
    assert result.unit.raw_path.read_bytes() == content.encode()  # type: ignore[union-attr]


@then("no raw payload was written")
def _no_payload(context: dict[str, object]) -> None:
    unit = context["unit"]
    assert isinstance(unit, DownloadUnit)
    assert not unit.raw_path.exists()


@then(parsers.parse("at least one recorded wait is {threshold:g}s or more"))
def _wait(context: dict[str, object], threshold: float) -> None:
    waits = context["waits"]
    assert isinstance(waits, list)
    assert any(w >= threshold for w in waits)


@then(parsers.parse('it fails with a ValueError matching "{message}"'))
def _value_error(context: dict[str, object], message: str) -> None:
    error = context["error"]
    assert isinstance(error, ValueError)
    assert message in str(error)
