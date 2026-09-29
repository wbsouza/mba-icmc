"""Read exact minute quote counts from canonical prices with a single-month cache."""

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from algo_core import layout
from algo_core.instrument import Instrument

from algo_backtest.months import months_between


def activity_provenance(
    data_root: Path, instrument: Instrument, start: date, end: date
) -> dict[str, str]:
    """Hash exact m1 partition bytes for the inclusive window, keyed relative to data_root.

    Stream each month once per call without caching or writing files. Call before
    and after engine execution and compare the returned manifests to detect changed
    inputs; this function performs no per-bar work and does not record artifacts.

    Raises:
        ValueError: A covered partition cannot be read, or the date window is reversed.
    """
    manifest: dict[str, str] = {}
    for year, month in months_between(start, end):
        path = layout.price_path_for(data_root, instrument, "m1", year, month)
        try:
            with path.open("rb") as source:
                digest = hashlib.file_digest(source, "sha256").hexdigest()
        except OSError as exc:
            raise ValueError(
                f"cannot hash canonical tick activity from {path}: {exc}; "
                "download/transform this m1 month and verify ALGO_DATA_ROOT and read permissions"
            ) from exc
        manifest[path.relative_to(data_root).as_posix()] = digest
    return manifest


def _utc_minute(timestamp: object) -> datetime:
    """Reject missing, naive, non-UTC or non-minute timestamps without rounding."""
    if not isinstance(timestamp, datetime) or timestamp.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be an aware UTC minute start; supply a UTC bar start")
    if timestamp.second or timestamp.microsecond or getattr(timestamp, "nanosecond", 0):
        raise ValueError("timestamp must be an exact UTC minute start; supply a UTC bar start")
    return timestamp


def _month_counts(path: Path, month: tuple[int, int]) -> dict[datetime, int]:
    """Validate raw projected columns before publishing a complete month dictionary."""
    with pq.ParquetFile(path) as parquet:  # type: ignore[no-untyped-call]
        table = parquet.read(columns=["timestamp", "tick_count"])
    for column in ("timestamp", "tick_count"):
        if table.column_names.count(column) != 1:
            raise ValueError(f"canonical prices require exactly one {column} column")
    counts: dict[datetime, int] = {}
    for raw_time, raw_count in zip(table["timestamp"], table["tick_count"], strict=True):
        timestamp, count = _canonical_time(raw_time), raw_count.as_py()
        _validate_row(timestamp, count, month)
        if timestamp in counts:
            raise ValueError(f"duplicate canonical timestamp {timestamp!r}")
        counts[timestamp] = count
    return counts


def _canonical_time(timestamp: pa.Scalar) -> datetime:
    """Check Arrow precision before conversion so sub-microsecond values cannot round."""
    if isinstance(timestamp, pa.TimestampScalar) and timestamp.is_valid:
        ticks_per_minute = {"s": 60, "ms": 60_000, "us": 60_000_000, "ns": 60_000_000_000}
        if timestamp.value % ticks_per_minute[timestamp.type.unit]:
            raise ValueError("canonical timestamp must be an exact UTC minute start")
        timestamp = timestamp.cast(pa.timestamp("us", tz=timestamp.type.tz))
    return _utc_minute(timestamp.as_py())


def _validate_row(timestamp: datetime, count: object, month: tuple[int, int]) -> None:
    """Enforce partition membership and integer quote counts without coercion."""
    if (timestamp.year, timestamp.month) != month:
        raise ValueError(f"timestamp {timestamp!r} is outside its partition month {month}")
    if type(count) is not int or count < 0:
        raise ValueError(f"tick_count at {timestamp!r} must be a nonnegative integer")


class TickActivityIndex:
    """Lazy, read-only canonical m1 lookup; future rows never substitute for an exact key.

    One validated month is cached until another month is requested. The source is
    treated as immutable during a run; failed loads do not replace the cache.
    """

    def __init__(self, data_root: Path, instrument: Instrument) -> None:
        """Bind canonical storage and instrument without opening any partitions."""
        self._data_root = data_root
        self._instrument = instrument
        self._month: tuple[int, int] | None = None
        self._counts: dict[datetime, int] = {}

    def count_at(self, timestamp: datetime, *, fill_forward: bool) -> int:
        """Return this UTC minute's count, or explicit zero for a fill-forward bar.

        Raises:
            ValueError: Invalid arguments, missing real evidence, or corrupt prices.
                Repair canonical m1 partitions with download/transform before retrying.
        """
        timestamp = _utc_minute(timestamp)
        if type(fill_forward) is not bool:
            raise ValueError("fill_forward must be a boolean; supply the bar's explicit flag")
        if fill_forward:
            return 0
        month = (timestamp.year, timestamp.month)
        path = layout.price_path_for(self._data_root, self._instrument, "m1", *month)
        if month != self._month:
            self._load_month(path, month)
        if timestamp not in self._counts:
            raise ValueError(
                f"no tick_count for real bar {timestamp!r} in canonical prices {path}; "
                "download/transform the missing minute and verify ALGO_DATA_ROOT"
            )
        return self._counts[timestamp]

    def _load_month(self, path: Path, month: tuple[int, int]) -> None:
        """Replace the cached month only after all rows pass validation."""
        try:
            counts = _month_counts(path, month)
        except (OSError, pa.ArrowException, ValueError) as exc:
            raise ValueError(
                f"cannot read canonical tick activity from {path}: {exc}; "
                "download/transform this m1 month and verify ALGO_DATA_ROOT"
            ) from exc
        self._counts = counts
        self._month = month
