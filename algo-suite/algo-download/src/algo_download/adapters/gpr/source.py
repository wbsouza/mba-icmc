"""The GPR source: one whole-window raw Excel file."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
from algo_core import layout
from algo_core.logging import get_logger

from algo_download.adapters.gpr.paths import GPR_URL, SOURCE, raw_path
from algo_download.adapters.raw_http import (
    FetchError,
    HttpClient,
    atomic_write,
    get_with_retries,
    is_retryable,
)
from algo_download.registry import register
from algo_download.request import DownloadRequest
from algo_download.result import DownloadUnit, UnitResult, UnitStatus
from algo_download.source import DataSource, RequestShape

_log = get_logger(__name__)
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_RETRIES = 3
_DEFAULT_BACKOFF = 0.5


@register
class GprSource(DataSource):
    """Adapts the public Caldara & Iacoviello GPR index to the ``DataSource`` port."""

    name = SOURCE
    request_shape = RequestShape.WHOLE_WINDOW

    def __init__(
        self,
        data_root: Path | None = None,
        client: HttpClient | None = None,
        retries: int = _DEFAULT_RETRIES,
        backoff: float = _DEFAULT_BACKOFF,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._data_root = data_root if data_root is not None else layout.data_root()
        self._client = client if client is not None else httpx.Client(timeout=_DEFAULT_TIMEOUT)
        self._retries = retries
        self._backoff = backoff
        self._sleep = sleep

    def plan(self, request: DownloadRequest) -> Iterator[DownloadUnit]:
        """Yield the single whole-window GPR raw-file unit."""
        yield DownloadUnit(key="gpr data_gpr_export.xls", raw_path=raw_path(self._data_root))

    def fetch(self, unit: DownloadUnit) -> UnitResult:
        """Fetch the index file and write provider-native bytes atomically."""
        try:
            payload = self._get(GPR_URL)
        except (FetchError, httpx.HTTPStatusError) as exc:
            _log.warning(
                "fetch_failed", source=self.name, unit=unit.key, url=GPR_URL, error=repr(exc)
            )
            return UnitResult(unit=unit, status=UnitStatus.FAILED)
        atomic_write(unit.raw_path, payload)
        return UnitResult(unit=unit, status=UnitStatus.WRITTEN, bytes=len(payload))

    def _get(self, url: str) -> bytes:
        """GET the GPR file, retrying transient failures."""
        return get_with_retries(
            url=url,
            client=self._client,
            retries=self._retries,
            backoff=self._backoff,
            sleep=self._sleep,
            payload_from_response=_payload_or_retry,
        )


def _payload_or_retry(response: httpx.Response) -> bytes | None:
    """Return GPR bytes, ``None`` for retryable statuses, or raise on other HTTP errors."""
    if is_retryable(response):
        return None
    response.raise_for_status()
    return response.content
