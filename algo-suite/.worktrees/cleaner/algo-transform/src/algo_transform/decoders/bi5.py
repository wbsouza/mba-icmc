"""Decode Dukascopy ``.bi5`` hourly tick files into validated ``Tick`` objects.

Standard library only (``lzma`` + ``struct``); no third-party Dukascopy client,
so decoding stays inside this stage and the download stage's raw-only boundary
holds. The format was confirmed against the real feed (algo-download SPEC §7a):
an LZMA stream of 20-byte big-endian ``>IIIff`` records
(ms-offset-in-hour, ask-points, bid-points, ask-volume, bid-volume). Integer
points become prices via ``price_increment`` (``10**-digits``), never the pip.
See ../../../SPEC.md §3.
"""

from __future__ import annotations

import lzma
import struct
from datetime import datetime, timedelta

from algo_core.bars import Tick

_RECORD = struct.Struct(">IIIff")  # one tick = 20 bytes


class DecodeError(ValueError):
    """A non-empty bi5 payload that could not be decoded (corrupt or truncated)."""


def _require_utc(hour_start: datetime) -> None:
    """Fail fast if ``hour_start`` is naive or not UTC (the stage's UTC contract)."""
    if hour_start.tzinfo is None or hour_start.utcoffset() != timedelta(0):
        raise ValueError(
            f"hour_start must be timezone-aware UTC; got {hour_start!r}. "
            "Fix: pass a UTC datetime, e.g. datetime(..., tzinfo=UTC)."
        )


def decode_bi5(payload: bytes, hour_start: datetime, price_increment: float) -> list[Tick]:
    """Decode one hour's bi5 payload into ticks.

    ``hour_start`` is the UTC start of the file's hour; each record's millisecond
    offset is added to it. An **empty** payload is the download's 0-byte no-data
    marker and yields ``[]`` (not an error). A payload that fails LZMA
    decompression, or whose decompressed length is not a multiple of the 20-byte
    record, raises ``DecodeError`` so the caller can quarantine it.
    """
    _require_utc(hour_start)
    if not payload:
        return []
    try:
        raw = lzma.decompress(payload)
    except lzma.LZMAError as exc:
        raise DecodeError(f"bi5 LZMA decompression failed: {exc}") from exc
    if not raw:
        raise DecodeError("non-empty bi5 payload decompressed to zero bytes")
    if len(raw) % _RECORD.size:
        raise DecodeError(
            f"bi5 decompressed length {len(raw)} is not a multiple of {_RECORD.size}"
        )
    return [
        _to_tick(hour_start, price_increment, _RECORD.unpack_from(raw, offset))
        for offset in range(0, len(raw), _RECORD.size)
    ]


def _to_tick(
    hour_start: datetime, price_increment: float, record: tuple[int, int, int, float, float]
) -> Tick:
    """Build a ``Tick`` from one unpacked ``>IIIff`` record."""
    ms_offset, ask_points, bid_points, ask_volume, bid_volume = record
    return Tick(
        timestamp=hour_start + timedelta(milliseconds=ms_offset),
        bid=bid_points * price_increment,
        ask=ask_points * price_increment,
        bid_volume=bid_volume,
        ask_volume=ask_volume,
    )
