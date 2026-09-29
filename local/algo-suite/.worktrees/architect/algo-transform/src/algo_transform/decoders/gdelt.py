"""Decode raw GDELT Events-table zip payloads."""

from __future__ import annotations

import csv
import zipfile
from datetime import date
from io import BytesIO, TextIOWrapper
from pathlib import Path

from pydantic import ValidationError

from algo_transform.decoders.bi5 import DecodeError
from algo_transform.events import GdeltEvent

_EVENTS_COLUMNS = 61
_GLOBAL_EVENT_ID = 0
_DAY = 1
_ACTOR1_CODE = 5
_ACTOR2_CODE = 15
_EVENT_CODE = 26
_GOLDSTEIN_SCALE = 30
_NUM_MENTIONS = 31
_NUM_SOURCES = 32
_NUM_ARTICLES = 33
_AVG_TONE = 34
_SOURCE_URL = 60


def decode_events_zip(payload: bytes, raw_path: Path) -> list[GdeltEvent]:
    """Decode one GDELT Events zip payload into typed event rows.

    An empty payload is the downloader's durable MISSING marker and yields no
    rows. A non-empty payload must be a valid zip containing tab-delimited Events
    rows with the expected GDELT column count.
    """
    if not payload:
        return []
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            names = archive.namelist()
            if len(names) != 1:
                raise DecodeError(f"{raw_path}: expected one CSV member, found {len(names)}")
            with archive.open(names[0]) as member:
                reader = csv.reader(TextIOWrapper(member, encoding="utf-8"), delimiter="\t")
                return [_row_to_event(row, raw_path) for row in reader]
    except zipfile.BadZipFile as exc:
        raise DecodeError(f"{raw_path}: invalid GDELT zip") from exc


def _row_to_event(row: list[str], raw_path: Path) -> GdeltEvent:
    """Convert one raw Events-table row to the canonical subset."""
    if len(row) != _EVENTS_COLUMNS:
        raise DecodeError(f"{raw_path}: GDELT row has {len(row)} columns, expected 61")
    try:
        return GdeltEvent(
            global_event_id=int(row[_GLOBAL_EVENT_ID]),
            event_date=_parse_yyyymmdd(row[_DAY]),
            event_code=row[_EVENT_CODE],
            goldstein_scale=float(row[_GOLDSTEIN_SCALE]),
            avg_tone=float(row[_AVG_TONE]),
            actor1_code=row[_ACTOR1_CODE],
            actor2_code=row[_ACTOR2_CODE],
            num_mentions=int(row[_NUM_MENTIONS]),
            num_sources=int(row[_NUM_SOURCES]),
            num_articles=int(row[_NUM_ARTICLES]),
            source_url=row[_SOURCE_URL],
        )
    except (ValueError, ValidationError) as exc:
        raise DecodeError(f"{raw_path}: malformed GDELT row") from exc


def _parse_yyyymmdd(value: str) -> date:
    """Parse a GDELT YYYYMMDD date string."""
    return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
