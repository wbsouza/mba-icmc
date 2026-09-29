"""GDELT Web News NGrams URL and raw-path mapping."""

from __future__ import annotations

from pathlib import Path

from algo_core import layout
from pydantic import BaseModel, ConfigDict

SOURCE = "gdelt_ngrams"
_HOST = "https://data.gdeltproject.org/gdeltv3/webngrams"
_SUFFIX = ".webngrams.json.gz"


class GdeltNgramsMinute(BaseModel):
    """Coordinates of one UTC-minute GDELT Web News NGrams raw payload."""

    model_config = ConfigDict(frozen=True)

    year: int
    month: int
    day: int
    hour: int
    minute: int


def stamp(minute: GdeltNgramsMinute) -> str:
    """Return the GDELT timestamp string used in NGrams URLs and filenames."""
    return (
        f"{minute.year:04d}{minute.month:02d}{minute.day:02d}"
        f"{minute.hour:02d}{minute.minute:02d}00"
    )


def ngrams_url(minute: GdeltNgramsMinute) -> str:
    """Build the direct Web News NGrams gzip URL for a UTC minute."""
    return f"{_HOST}/{stamp(minute)}{_SUFFIX}"


def raw_path(data_root: Path, minute: GdeltNgramsMinute) -> Path:
    """Build the day-partitioned raw path for a Web News NGrams gzip payload."""
    return (
        layout.raw_dir(data_root, SOURCE)
        / f"{minute.year:04d}"
        / f"{minute.month:02d}"
        / f"{minute.day:02d}"
        / f"{stamp(minute)}{_SUFFIX}"
    )


def parse_raw_path(path: Path) -> GdeltNgramsMinute:
    """Recover the ``GdeltNgramsMinute`` from a path built by :func:`raw_path`."""
    filename = path.name.removesuffix(_SUFFIX)
    return GdeltNgramsMinute(
        year=int(filename[0:4]),
        month=int(filename[4:6]),
        day=int(filename[6:8]),
        hour=int(filename[8:10]),
        minute=int(filename[10:12]),
    )
