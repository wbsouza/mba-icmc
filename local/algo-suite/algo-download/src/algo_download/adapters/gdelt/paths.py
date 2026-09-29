"""GDELT Events-table URL and raw-path mapping."""

from __future__ import annotations

from pathlib import Path

from algo_core import layout
from pydantic import BaseModel, ConfigDict

SOURCE = "gdelt"
_HOST = "https://data.gdeltproject.org/gdeltv2"


class GdeltSlot(BaseModel):
    """Coordinates of one 15-minute GDELT Events-table raw zip."""

    model_config = ConfigDict(frozen=True)

    year: int
    month: int
    day: int
    hour: int
    minute: int


def stamp(slot: GdeltSlot) -> str:
    """Return the GDELT timestamp string used in URLs and filenames."""
    return (
        f"{slot.year:04d}{slot.month:02d}{slot.day:02d}"
        f"{slot.hour:02d}{slot.minute:02d}00"
    )


def events_url(slot: GdeltSlot) -> str:
    """Build the direct Events-table zip URL for a 15-minute slot."""
    return f"{_HOST}/{stamp(slot)}.export.CSV.zip"


def raw_path(data_root: Path, slot: GdeltSlot) -> Path:
    """Build the day-partitioned raw path for a GDELT Events zip."""
    return (
        layout.raw_dir(data_root, SOURCE)
        / f"{slot.year:04d}"
        / f"{slot.month:02d}"
        / f"{slot.day:02d}"
        / f"{stamp(slot)}.export.CSV.zip"
    )


def parse_raw_path(path: Path) -> GdeltSlot:
    """Recover the ``GdeltSlot`` from a path built by :func:`raw_path`."""
    filename = path.name.removesuffix(".export.CSV.zip")
    return GdeltSlot(
        year=int(filename[0:4]),
        month=int(filename[4:6]),
        day=int(filename[6:8]),
        hour=int(filename[8:10]),
        minute=int(filename[10:12]),
    )
