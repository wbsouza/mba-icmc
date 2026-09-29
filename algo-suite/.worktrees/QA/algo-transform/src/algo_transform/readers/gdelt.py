"""Read complete GDELT raw months into canonical event rows."""

from __future__ import annotations

import calendar
from pathlib import Path

from algo_core.layout import feature_path, raw_dir
from algo_core.logging import get_logger
from pydantic import BaseModel, ConfigDict

from algo_transform.decoders.bi5 import DecodeError
from algo_transform.decoders.gdelt import decode_events_zip
from algo_transform.events import GdeltEvent

_log = get_logger(__name__)
_SOURCE = "gdelt"
_SLOT_MINUTES = (0, 15, 30, 45)


class GdeltSlot(BaseModel):
    """Coordinates of one 15-minute GDELT Events raw zip."""

    model_config = ConfigDict(frozen=True)

    year: int
    month: int
    day: int
    hour: int
    minute: int


class GdeltLoadResult(BaseModel):
    """Decoded GDELT events plus corrupt slots."""

    model_config = ConfigDict(frozen=True)

    events: tuple[GdeltEvent, ...]
    quarantined: tuple[Path, ...]


def expected_slots(year: int, month: int) -> list[GdeltSlot]:
    """Every 15-minute Events slot expected for a complete month."""
    days = calendar.monthrange(year, month)[1]
    return [
        GdeltSlot(year=year, month=month, day=day, hour=hour, minute=minute)
        for day in range(1, days + 1)
        for hour in range(24)
        for minute in _SLOT_MINUTES
    ]


def raw_path(data_root: Path, slot: GdeltSlot) -> Path:
    """Build the raw GDELT Events zip path."""
    return (
        raw_dir(data_root, _SOURCE)
        / f"{slot.year:04d}"
        / f"{slot.month:02d}"
        / f"{slot.day:02d}"
        / f"{slot.year:04d}{slot.month:02d}{slot.day:02d}{slot.hour:02d}{slot.minute:02d}00"
        ".export.CSV.zip"
    )


def event_path(data_root: Path, year: int, month: int) -> Path:
    """Build the canonical GDELT event Parquet path."""
    return feature_path(data_root, "events", _SOURCE, year, month)


def is_month_complete(data_root: Path, year: int, month: int) -> bool:
    """True iff every expected slot is present as data or a 0-byte marker."""
    return all(raw_path(data_root, slot).exists() for slot in expected_slots(year, month))


def load_events(data_root: Path, year: int, month: int) -> GdeltLoadResult:
    """Decode every present GDELT slot, quarantining corrupt slots."""
    events: list[GdeltEvent] = []
    quarantined: list[Path] = []
    for slot in expected_slots(year, month):
        path = raw_path(data_root, slot)
        if not path.exists():
            continue
        try:
            events.extend(decode_events_zip(path.read_bytes(), path))
        except DecodeError:
            _log.warning("quarantined_gdelt", path=str(path))
            quarantined.append(path)
    return GdeltLoadResult(events=tuple(events), quarantined=tuple(quarantined))
