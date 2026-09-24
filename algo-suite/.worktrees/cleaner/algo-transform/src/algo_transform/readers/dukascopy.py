"""Read a month of Dukascopy raw bi5 files into decoded ticks.

This module is the **single owner** of "which hours a month is expected to have",
so completeness (``is_month_complete``) and loading (``load_ticks``) share one
enumeration and cannot drift apart. It reads against the shared raw-path contract
in ``algo_core.layout``; a 0-byte file is the download's no-data marker (decodes
to no ticks), and a corrupt file is quarantined and returned in the result so the
orchestrator can refuse to write a truncated month (status CORRUPT).
"""

from __future__ import annotations

import calendar
from datetime import UTC, datetime
from pathlib import Path

from algo_core.bars import Tick
from algo_core.instrument import Instrument
from algo_core.layout import TickFile, dukascopy_raw_path
from algo_core.logging import get_logger
from pydantic import BaseModel, ConfigDict

from algo_transform.decoders.bi5 import DecodeError, decode_bi5

_log = get_logger(__name__)
_HOURS_PER_DAY = 24


class LoadResult(BaseModel):
    """Ticks decoded for a month, plus any files quarantined as corrupt."""

    model_config = ConfigDict(frozen=True)

    ticks: tuple[Tick, ...]
    quarantined: tuple[Path, ...]


def expected_hours(symbol: str, year: int, month: int) -> list[TickFile]:
    """Every hourly file a complete month should contain (the one enumeration)."""
    days = calendar.monthrange(year, month)[1]
    return [
        TickFile(symbol=symbol, year=year, month=month, day=day, hour=hour)
        for day in range(1, days + 1)
        for hour in range(_HOURS_PER_DAY)
    ]


def is_month_complete(data_root: Path, symbol: str, year: int, month: int) -> bool:
    """True iff every expected hour is present on disk (data or 0-byte marker)."""
    return all(
        dukascopy_raw_path(data_root, tick).exists()
        for tick in expected_hours(symbol, year, month)
    )


def load_ticks(data_root: Path, instrument: Instrument, year: int, month: int) -> LoadResult:
    """Decode every present hour of the month into ticks, quarantining corrupt files."""
    ticks: list[Tick] = []
    quarantined: list[Path] = []
    for tick_file in expected_hours(instrument.symbol, year, month):
        path = dukascopy_raw_path(data_root, tick_file)
        if not path.exists():
            continue
        hour_start = datetime(
            tick_file.year, tick_file.month, tick_file.day, tick_file.hour, tzinfo=UTC
        )
        try:
            ticks.extend(decode_bi5(path.read_bytes(), hour_start, instrument.price_increment))
        except DecodeError:
            _log.warning("quarantined_bi5", path=str(path))
            quarantined.append(path)
    return LoadResult(ticks=tuple(ticks), quarantined=tuple(quarantined))
