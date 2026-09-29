"""Decode the raw GPR headline index file."""

from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import cast

import xlrd  # type: ignore[import-untyped]

from algo_transform.decoders.bi5 import DecodeError
from algo_transform.events import GprEvent


def decode_gpr(payload: bytes, raw_path: Path) -> list[GprEvent]:
    """Decode GPR rows without forward-filling or interpolation.

    The production source is distributed as ``.xls``. The decoder also accepts
    UTF-8 CSV/TSV-style tabular bytes so the Gherkin fixtures can stay tiny while
    pinning the same period/GPR contract.
    """
    if not payload:
        raise DecodeError(f"{raw_path}: empty GPR raw file")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        return _decode_xls(payload, raw_path)
    rows = list(csv.DictReader(StringIO(text), delimiter=_delimiter(text)))
    if not rows:
        raise DecodeError(f"{raw_path}: GPR file has no rows")
    period_key, value_key = _columns(rows[0], raw_path)
    return [_row_to_event(row, period_key, value_key, raw_path) for row in rows]


def _decode_xls(payload: bytes, raw_path: Path) -> list[GprEvent]:
    """Decode the real binary XLS distribution with xlrd."""
    try:
        book = xlrd.open_workbook(file_contents=payload)
    except xlrd.XLRDError as exc:
        raise DecodeError(f"{raw_path}: malformed GPR raw file") from exc
    sheet = book.sheet_by_index(0)
    if sheet.nrows < 2:
        raise DecodeError(f"{raw_path}: GPR file has no rows")
    headers = [str(sheet.cell_value(0, col)).strip() for col in range(sheet.ncols)]
    rows = [
        {
            headers[col]: _cell_value(headers[col], sheet.cell_value(row_index, col), book.datemode)
            for col in range(sheet.ncols)
        }
        for row_index in range(1, sheet.nrows)
    ]
    period_key, value_key = _columns(rows[0], raw_path)
    return [_row_to_event(row, period_key, value_key, raw_path) for row in rows]


def _cell_value(header: str, value: object, datemode: int) -> str:
    """Convert an xlrd cell value to the string form consumed by the row decoder."""
    if _is_period_header(header) and isinstance(value, float):
        try:
            parsed = cast(datetime, xlrd.xldate.xldate_as_datetime(value, datemode))
        except (OverflowError, ValueError, xlrd.XLRDError):
            return str(value)
        return parsed.date().isoformat()
    return str(value).strip()


def _is_period_header(header: str) -> bool:
    """Whether a spreadsheet column should be interpreted as a date period."""
    return header.strip().lower() in {"period", "month", "date"}


def _delimiter(text: str) -> str:
    """Choose CSV vs TSV from the header line."""
    header = text.splitlines()[0] if text.splitlines() else ""
    return "\t" if "\t" in header else ","


def _columns(row: dict[str, str], raw_path: Path) -> tuple[str, str]:
    """Find the period and headline GPR columns in a small set of known labels."""
    normalized = {key.strip().lower(): key for key in row}
    period = normalized.get("period") or normalized.get("month") or normalized.get("date")
    value = normalized.get("gpr") or normalized.get("gprhc")
    if period is None or value is None:
        raise DecodeError(f"{raw_path}: GPR file lacks period/date and gpr columns")
    return period, value


def _row_to_event(
    row: dict[str, str], period_key: str, value_key: str, raw_path: Path
) -> GprEvent:
    """Convert one headline-index row."""
    try:
        return GprEvent(period=_parse_period(row[period_key]), gpr=float(row[value_key]))
    except (KeyError, ValueError) as exc:
        raise DecodeError(f"{raw_path}: malformed GPR row") from exc


def _parse_period(value: str) -> date:
    """Parse YYYY-MM or YYYY-MM-DD periods as dates."""
    parts = value.strip().split("-")
    if len(parts) == 2:
        return date(int(parts[0]), int(parts[1]), 1)
    if len(parts) == 3:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    raise ValueError(f"unsupported period {value!r}")
