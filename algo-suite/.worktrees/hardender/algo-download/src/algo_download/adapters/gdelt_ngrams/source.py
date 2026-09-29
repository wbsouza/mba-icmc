"""The GDELT Web News NGrams source: one raw gzip unit per UTC minute."""

from __future__ import annotations

import calendar
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
from algo_core import layout
from algo_core.logging import get_logger

from algo_download.adapters.gdelt_ngrams.paths import (
    SOURCE,
    GdeltNgramsMinute,
    ngrams_url,
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
from algo_download.source import DataSource, RequestShape

_log = get_logger(__name__)
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_RETRIES = 3
_DEFAULT_BACKOFF = 0.5
_ENV_MIN_INTERVAL = "ALGO_GDELT_NGRAMS_MIN_INTERVAL"
_DEFAULT_MIN_INTERVAL = 0.2
_HOURS_PER_DAY = 24
_MINUTES_PER_HOUR = 60


@register
class GdeltNgramsSource(DataSource):
    """Adapts the public GDELT Web News NGrams 3.0 feed to the ``DataSource`` port."""

    name = SOURCE
    request_shape = RequestShape.GLOBAL_MONTHS

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
        """Yield one raw NGrams gzip unit for every UTC minute in the requested months."""
        for year, month in request.months:
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                for hour in range(_HOURS_PER_DAY):
                    for minute in range(_MINUTES_PER_HOUR):
                        target = GdeltNgramsMinute(
                            year=year, month=month, day=day, hour=hour, minute=minute
                        )
                        yield unit_for_minute(self._data_root, target)

    def fetch(self, unit: DownloadUnit) -> UnitResult:
        """Fetch one minute and write provider-native gzip bytes atomically."""
        url = ngrams_url(parse_raw_path(unit.raw_path))
        try:
            payload = self._get(url)
        except (FetchError, httpx.HTTPStatusError) as exc:
            _log.warning("fetch_failed", source=self.name, unit=unit.key, url=url, error=repr(exc))
            return UnitResult(unit=unit, status=UnitStatus.FAILED)
        atomic_write(unit.raw_path, payload)
        status = UnitStatus.WRITTEN if payload else UnitStatus.MISSING
        return UnitResult(unit=unit, status=status, bytes=len(payload))

    def _get(self, url: str) -> bytes:
        """GET a minute, retrying transient failures and returning empty bytes for no-data."""
        return get_with_retries(
            url=url,
            client=self._client,
            retries=self._retries,
            backoff=self._backoff,
            sleep=self._sleep,
            payload_from_response=raw_payload_or_none,
            before_attempt=self._throttle.wait,
        )


def unit_for_minute(data_root: Path, minute: GdeltNgramsMinute) -> DownloadUnit:
    """Build the canonical download unit for one GDELT NGrams minute."""
    return DownloadUnit(key=_key(minute), raw_path=raw_path(data_root, minute))


def _key(minute: GdeltNgramsMinute) -> str:
    """Return a stable human-readable key for logs and reports."""
    date = f"{minute.year:04d}-{minute.month:02d}-{minute.day:02d}"
    return f"gdelt_ngrams {date} {minute.hour:02d}:{minute.minute:02d}"


def _default_min_interval() -> float:
    """Resolve the GDELT NGrams throttle interval from the environment."""
    return env_seconds(_ENV_MIN_INTERVAL, _DEFAULT_MIN_INTERVAL)
