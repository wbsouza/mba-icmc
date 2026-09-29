"""Read complete GDELT NGrams raw months into canonical article rows."""

from __future__ import annotations

import calendar
from pathlib import Path

from algo_core.layout import feature_path, raw_dir
from algo_core.logging import get_logger
from pydantic import BaseModel, ConfigDict

from algo_transform.decoders.bi5 import DecodeError
from algo_transform.decoders.gdelt_ngrams import decode_ngrams_minute
from algo_transform.events import GdeltNewsArticle

_log = get_logger(__name__)
_RAW_SOURCE = "gdelt_ngrams"  # algo-download's raw/{source}/... directory name
_DATASET = "gdelt"  # output dataset name: parquet/news/gdelt/..., matching algo-score's contract
_SUFFIX = ".webngrams.json.gz"
_HOURS_PER_DAY = 24
_MINUTES_PER_HOUR = 60


class GdeltNgramsMinute(BaseModel):
    """Coordinates of one UTC-minute GDELT Web News NGrams raw payload."""

    model_config = ConfigDict(frozen=True)

    year: int
    month: int
    day: int
    hour: int
    minute: int


class GdeltNgramsLoadResult(BaseModel):
    """Decoded GDELT NGrams articles plus corrupt minutes."""

    model_config = ConfigDict(frozen=True)

    articles: tuple[GdeltNewsArticle, ...]
    quarantined: tuple[Path, ...]


def expected_minutes(year: int, month: int) -> list[GdeltNgramsMinute]:
    """Every UTC minute expected for a complete month."""
    days = calendar.monthrange(year, month)[1]
    return [
        GdeltNgramsMinute(year=year, month=month, day=day, hour=hour, minute=minute)
        for day in range(1, days + 1)
        for hour in range(_HOURS_PER_DAY)
        for minute in range(_MINUTES_PER_HOUR)
    ]


def raw_path(data_root: Path, minute: GdeltNgramsMinute) -> Path:
    """Build the raw NGrams gzip path (must match algo_download's convention)."""
    stamp = (
        f"{minute.year:04d}{minute.month:02d}{minute.day:02d}{minute.hour:02d}{minute.minute:02d}00"
    )
    return (
        raw_dir(data_root, _RAW_SOURCE)
        / f"{minute.year:04d}"
        / f"{minute.month:02d}"
        / f"{minute.day:02d}"
        / f"{stamp}{_SUFFIX}"
    )


def news_path(data_root: Path, year: int, month: int) -> Path:
    """Build the canonical GDELT news Parquet path (parquet/news/gdelt/...)."""
    return feature_path(data_root, "news", _DATASET, year, month)


def is_month_complete(data_root: Path, year: int, month: int) -> bool:
    """True iff every expected minute is present as data or a 0-byte marker."""
    return all(raw_path(data_root, minute).exists() for minute in expected_minutes(year, month))


def load_articles(data_root: Path, year: int, month: int) -> GdeltNgramsLoadResult:
    """Decode every present NGrams minute, quarantining corrupt minutes."""
    articles: list[GdeltNewsArticle] = []
    quarantined: list[Path] = []
    for minute in expected_minutes(year, month):
        path = raw_path(data_root, minute)
        if not path.exists():
            continue
        try:
            articles.extend(decode_ngrams_minute(path.read_bytes(), path))
        except DecodeError:
            _log.warning("quarantined_gdelt_ngrams", path=str(path))
            quarantined.append(path)
    return GdeltNgramsLoadResult(articles=tuple(articles), quarantined=tuple(quarantined))
