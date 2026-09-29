"""The Dukascopy tick-data source: hourly bi5 units, raw bytes only.

A unit is one hour's ``.bi5`` file. ``fetch`` does a thin HTTP GET and writes the
provider-native bytes verbatim (no decoding; that is ``algo-transform``'s job).
A 404 / empty body means the provider has no data for that hour: an empty payload
is persisted so a re-run skips it (MISSING, durable). A fetch that never
completes writes nothing (FAILED) so the next run retries it. Transient failures
(network errors, 429 rate-limit, 5xx) are retried with backoff; other non-2xx
(e.g. 403) become FAILED rather than crashing the run. Requests are throttled to
at least ``min_interval`` seconds apart so a bulk pull stays polite and avoids a
ban. Writes are atomic, so an interrupted run never leaves a partial file that
resume would mistake for complete. See ../../../SPEC.md §2–§3.
"""

from __future__ import annotations

import calendar
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
from algo_core import layout
from algo_core.instrument import build_instrument
from algo_core.logging import get_logger

from algo_download.adapters.dukascopy.paths import (
    SOURCE,
    TickFile,
    bi5_url,
    parse_raw_path,
    raw_path,
)
from algo_download.adapters.raw_http import (
    FetchError,
    HttpClient,
    RequestThrottle,
    atomic_write,
    env_seconds,
    get_with_retries,
    raw_payload_or_none,
)
from algo_download.registry import register
from algo_download.request import DownloadRequest
from algo_download.result import DownloadUnit, UnitResult, UnitStatus
from algo_download.source import DataSource

_log = get_logger(__name__)
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_RETRIES = 3
_DEFAULT_BACKOFF = 0.5
_HOURS_PER_DAY = 24
# Politeness throttle: minimum seconds between requests, overridable via env
# (operational param; env > default per the suite's config precedence).
_ENV_MIN_INTERVAL = "ALGO_DUKASCOPY_MIN_INTERVAL"
_DEFAULT_MIN_INTERVAL = 0.2


@register
class DukascopySource(DataSource):
    """Adapts the public Dukascopy historical tick datafeed to the ``DataSource`` port."""

    name = SOURCE

    def __init__(
        self,
        data_root: Path | None = None,
        client: HttpClient | None = None,
        retries: int = _DEFAULT_RETRIES,
        backoff: float = _DEFAULT_BACKOFF,
        sleep: Callable[[float], None] = time.sleep,
        min_interval: float | None = None,
    ) -> None:
        self._data_root = data_root if data_root is not None else layout.data_root()
        self._client = client if client is not None else httpx.Client(timeout=_DEFAULT_TIMEOUT)
        self._retries = retries
        self._backoff = backoff
        self._sleep = sleep
        interval = min_interval if min_interval is not None else _default_min_interval()
        self._throttle = RequestThrottle(interval, sleep=sleep)

    def plan(self, request: DownloadRequest) -> Iterator[DownloadUnit]:
        instrument = build_instrument(request.symbol)
        for year, month in request.months:
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                for hour in range(_HOURS_PER_DAY):
                    tick = TickFile(
                        symbol=instrument.symbol, year=year, month=month, day=day, hour=hour
                    )
                    yield DownloadUnit(
                        key=_key(tick), raw_path=raw_path(self._data_root, tick)
                    )

    def fetch(self, unit: DownloadUnit) -> UnitResult:
        url = bi5_url(parse_raw_path(unit.raw_path))
        try:
            payload = self._get(url)
        except (FetchError, httpx.HTTPStatusError) as exc:
            _log.warning("fetch_failed", source=self.name, unit=unit.key, url=url, error=repr(exc))
            return UnitResult(unit=unit, status=UnitStatus.FAILED)
        atomic_write(unit.raw_path, payload)
        status = UnitStatus.WRITTEN if payload else UnitStatus.MISSING
        return UnitResult(unit=unit, status=status, bytes=len(payload))

    def _get(self, url: str) -> bytes:
        """GET the bi5, retrying transient failures; ``b""`` for a provider 404.

        Returns the payload (or empty for a 404). Raises ``FetchError`` when the
        retry budget is exhausted on a transient failure, or ``HTTPStatusError``
        for a non-transient non-2xx response (e.g. 403) — both become FAILED.
        """
        return get_with_retries(
            url=url,
            client=self._client,
            retries=self._retries,
            backoff=self._backoff,
            sleep=self._sleep,
            payload_from_response=raw_payload_or_none,
            before_attempt=self._throttle.wait,
        )


def _key(tick: TickFile) -> str:
    return f"{tick.symbol} {tick.year:04d}-{tick.month:02d}-{tick.day:02d} {tick.hour:02d}h"


def _default_min_interval() -> float:
    """Resolve the throttle interval from the env, failing fast on a bad value."""
    return env_seconds(_ENV_MIN_INTERVAL, _DEFAULT_MIN_INTERVAL)
