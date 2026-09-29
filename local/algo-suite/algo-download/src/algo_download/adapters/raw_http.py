"""Shared raw HTTP download helpers for provider adapters."""

from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import httpx


def _noop() -> None:
    """Default hook used when an adapter has no pre-request work."""


class HttpClient(Protocol):
    """The slice of an HTTP client that raw adapters need."""

    def get(self, url: str) -> httpx.Response:
        """Return the HTTP response for ``url``."""


class FetchError(RuntimeError):
    """A fetch that did not complete within the retry budget."""


class RequestThrottle:
    """Spaces adapter requests by at least ``min_interval`` seconds."""

    def __init__(
        self,
        min_interval: float,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._min_interval = min_interval
        self._sleep = sleep
        self._clock = clock
        self._last_request = 0.0

    def wait(self) -> None:
        """Sleep long enough to satisfy the configured request spacing."""
        if self._min_interval <= 0:
            return
        wait = self._min_interval - (self._clock() - self._last_request)
        if wait > 0:
            self._sleep(wait)
        self._last_request = self._clock()


def env_seconds(name: str, default: float) -> float:
    """Resolve a non-negative seconds value from ``name`` or return ``default``."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(
            f"{name} must be a number of seconds; got {raw!r}. "
            f"Fix: unset it or set e.g. {name}={default}"
        ) from exc
    if value < 0:
        raise ValueError(f"{name} must be >= 0; got {value}.")
    return value


def get_with_retries(
    url: str,
    client: HttpClient,
    retries: int,
    backoff: float,
    sleep: Callable[[float], None],
    payload_from_response: Callable[[httpx.Response], bytes | None],
    before_attempt: Callable[[], None] = _noop,
) -> bytes:
    """GET ``url`` until a definitive payload is returned or retry budget is spent."""
    last: Exception | None = None
    for attempt in range(retries + 1):
        before_attempt()
        try:
            response = client.get(url)
        except httpx.TransportError as exc:
            last = exc
        else:
            payload = payload_from_response(response)
            if payload is not None:
                return payload
            last = httpx.HTTPStatusError(
                "retryable status", request=response.request, response=response
            )
        if attempt < retries:
            sleep(backoff * (attempt + 1))
    raise FetchError(f"failed to fetch {url} after {retries + 1} attempts") from last


def raw_payload_or_none(response: httpx.Response) -> bytes | None:
    """Return bytes for definitive raw responses, ``None`` for retryable statuses."""
    code = response.status_code
    if code == httpx.codes.NOT_FOUND:
        return b""
    if is_retryable(response):
        return None
    response.raise_for_status()
    return response.content


def is_retryable(response: httpx.Response) -> bool:
    """Return true for statuses that should spend retry budget."""
    code = response.status_code
    return code == httpx.codes.TOO_MANY_REQUESTS or code >= httpx.codes.INTERNAL_SERVER_ERROR


def atomic_write(path: Path, payload: bytes) -> None:
    """Write bytes atomically so filesystem resume never sees partial payloads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".part")
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)
