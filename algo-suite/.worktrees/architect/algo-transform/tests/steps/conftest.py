"""Shared fixtures and builders for the algo-transform BDD step definitions."""

from __future__ import annotations

import lzma
import struct
from datetime import UTC, datetime
from pathlib import Path

import pytest
from algo_core.bars import Tick
from algo_core.layout import TickFile, dukascopy_raw_path


def bi5_payload(records: list[tuple[int, int, int, float, float]]) -> bytes:
    """LZMA-compress a stream of >IIIff Dukascopy tick records."""
    raw = b"".join(struct.pack(">IIIff", *record) for record in records)
    return lzma.compress(raw)


def write_raw(data_root: Path, tick: TickFile, payload: bytes) -> None:
    """Write a raw .bi5 payload at the canonical Dukascopy path for a tick hour."""
    path = dukascopy_raw_path(data_root, tick)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def make_tick(day: int, hour: int, minute: int, second: int, bid: float, ask: float) -> Tick:
    """Build a UTC Tick on 2020-01-<day> with unit bid/ask volumes."""
    return Tick(
        timestamp=datetime(2020, 1, day, hour, minute, second, tzinfo=UTC),
        bid=bid,
        ask=ask,
        bid_volume=1.0,
        ask_volume=1.0,
    )


@pytest.fixture
def context() -> dict[str, object]:
    """Per-scenario mutable context bag passed between steps."""
    return {}


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    """A writable per-scenario data root (a fresh tmp_path)."""
    return tmp_path
