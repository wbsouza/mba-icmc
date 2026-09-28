"""Incremental data and label-maturity adapter (Story 19, T2; RWT-23, RWT-24).

The adaptive cycle consumes already-built, keyed training rows in batches (one batch per
source partition delivery) and keeps a small JSON ledger under a caller-given directory:

- the **availability watermark**: the latest bar close whose rows have been validated
  *and* persisted (RWT-23). A completed month on disk never makes its later rows
  historically available; visibility is judged against a cutoff, never the file.
- per row, its availability (bar close), its `label_time` (the close of the horizon bar)
  and its label; a label is **pending** until a cutoff reaches `label_time` and
  **mature** from then on, inclusive (RWT-24). A row whose maturity is unknown
  (`label_time` is `None`) is rejected: unknown maturity is not maturity.
- per source partition, its path, content sha256 and persisted row count, so a silently
  rewritten file cannot masquerade as the same batch.

Every timestamp is a UTC instant. A batch must be internally ordered by availability and
unique by key. Re-delivering identical rows is a no-op; re-delivering a key with different
content is a conflict. A rejected batch persists nothing (validation runs before the
single atomic write), and later batches never rewrite what earlier ones persisted.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from algo_backtest.retraining.utc import iso_utc, require_utc

LEDGER_FILE = "ledger.json"
_SCHEMA_VERSION = 1
_MODULE = "retraining.ingestion"
_PENDING = "pending"
_MATURE = "mature"
_PARQUET_COLUMNS = ("key", "available_at", "label_time", "label")


@dataclass(frozen=True)
class SourceRow:
    """One keyed training observation as delivered by a source batch.

    `available_at` is the bar close (feature availability), `label_time` the close of the
    horizon bar; both UTC. `label_time` may arrive as `None` only so that `consume` can
    reject it explicitly (RWT-24).
    """

    key: str
    available_at: datetime
    label_time: datetime | None
    label: int


@dataclass(frozen=True)
class Batch:
    """One delivery from one source partition.

    `declared_bars` is the bar count the partition declares (parquet row-group metadata,
    a manifest); a delivery that falls short is a missing bar. `path`/`sha256` identify a
    file-backed partition; in-memory batches leave them `None`.
    """

    partition: str
    rows: tuple[SourceRow, ...]
    declared_bars: int | None = None
    path: str | None = None
    sha256: str | None = None


@dataclass(frozen=True)
class PartitionRecord:
    """What the ledger remembers about one source partition."""

    path: str | None
    sha256: str | None
    row_count: int


def _parse(text: str) -> datetime:
    """The inverse of `iso_utc`."""
    return datetime.fromisoformat(text)


def _validate_row(row: SourceRow) -> None:
    """One row's timestamp contract: UTC, known maturity, label after availability."""
    require_utc(row.available_at, what=f"row {row.key!r} available_at")
    if row.label_time is None:
        raise ValueError(
            f"{_MODULE}: row {row.key!r} has label_time None; unknown maturity is not "
            "maturity in the adaptive path (RWT-24), supply the horizon bar's close"
        )
    require_utc(row.label_time, what=f"row {row.key!r} label_time")
    if row.label_time <= row.available_at:
        raise ValueError(
            f"{_MODULE}: row {row.key!r} label_time {iso_utc(row.label_time)} must be after "
            f"its availability {iso_utc(row.available_at)}; a label cannot be knowable before "
            "the features it labels"
        )


def _require_unique(rows: Sequence[SourceRow]) -> None:
    """Keys must be unique inside one batch."""
    seen: set[str] = set()
    for row in rows:
        if row.key in seen:
            raise ValueError(
                f"{_MODULE}: batch keys must be unique, key {row.key!r} appears more than "
                "once; deduplicate the source delivery"
            )
        seen.add(row.key)


def _require_ordered(rows: Sequence[SourceRow]) -> None:
    """Rows must arrive ordered (non-decreasing) by availability."""
    for earlier, later in zip(rows, rows[1:], strict=False):
        if later.available_at < earlier.available_at:
            raise ValueError(
                f"{_MODULE}: batch rows must be ordered by available_at, row {later.key!r} "
                f"({iso_utc(later.available_at)}) follows {earlier.key!r} "
                f"({iso_utc(earlier.available_at)}); sort the delivery by bar close"
            )


def _require_declared(batch: Batch) -> None:
    """A partition that declares more bars than it delivers is missing bars."""
    if batch.declared_bars is not None and batch.declared_bars != len(batch.rows):
        raise ValueError(
            f"{_MODULE}: partition {batch.partition!r} declares {batch.declared_bars} bars "
            f"but delivers {len(batch.rows)} rows; the delivery is incomplete or corrupt"
        )


def validate_batch(batch: Batch) -> None:
    """Reject an internally invalid batch before anything touches the ledger (RWT-02)."""
    _require_unique(batch.rows)
    _require_ordered(batch.rows)
    for row in batch.rows:
        _validate_row(row)
    _require_declared(batch)


def _record(row: SourceRow, partition: str) -> dict[str, Any]:
    """The JSON-ready persisted form of one validated row."""
    assert row.label_time is not None  # validated by `_validate_row`
    return {
        "available_at": iso_utc(row.available_at),
        "label_time": iso_utc(row.label_time),
        "label": row.label,
        "partition": partition,
    }


class Ledger:
    """The persisted ingestion state of one directory: watermark, rows, partitions."""

    def __init__(self, directory: Path, payload: dict[str, Any]) -> None:
        self._directory = directory
        self._watermark: str | None = payload["watermark"]
        self._records: dict[str, dict[str, Any]] = payload["rows"]
        self._partitions: dict[str, dict[str, Any]] = payload["partitions"]

    @classmethod
    def open(cls, directory: Path) -> Ledger:
        """Load the ledger persisted under `directory`, or an empty one if none exists yet."""
        path = directory / LEDGER_FILE
        if not path.exists():
            return cls(directory, {"watermark": None, "rows": {}, "partitions": {}})
        return cls(directory, json.loads(path.read_text(encoding="utf-8")))

    @property
    def path(self) -> Path:
        """Where this ledger is (or will be) persisted."""
        return self._directory / LEDGER_FILE

    @property
    def watermark(self) -> datetime | None:
        """The latest validated-and-persisted bar close; `None` before the first batch."""
        return None if self._watermark is None else _parse(self._watermark)

    @property
    def row_count(self) -> int:
        """How many rows the ledger holds."""
        return len(self._records)

    @property
    def partitions(self) -> Mapping[str, PartitionRecord]:
        """Every source partition consumed so far, by partition id."""
        return {
            name: PartitionRecord(
                path=entry["path"], sha256=entry["sha256"], row_count=entry["row_count"]
            )
            for name, entry in self._partitions.items()
        }

    def consume(self, batch: Batch) -> Ledger:
        """Validate `batch`, persist its new rows atomically, advance the watermark (RWT-23).

        Raises:
            ValueError: the batch is internally invalid, re-delivers a key with different
                content, re-identifies a partition with a different checksum, or would
                regress the watermark. Nothing is persisted in any of these cases.
        """
        validate_batch(batch)
        new_rows = self._new_rows(batch)
        self._require_partition_identity(batch)
        if not new_rows:
            return self
        self._require_watermark_order(new_rows)
        for row in new_rows:
            self._records[row.key] = _record(row, batch.partition)
        self._partitions[batch.partition] = {
            "path": batch.path,
            "sha256": batch.sha256,
            "row_count": self._partitions.get(batch.partition, {}).get("row_count", 0)
            + len(new_rows),
        }
        self._watermark = iso_utc(max(row.available_at for row in new_rows))
        self._write()
        return self

    def _new_rows(self, batch: Batch) -> list[SourceRow]:
        """Rows not yet persisted; identical re-delivery is skipped, a different one conflicts."""
        new_rows: list[SourceRow] = []
        for row in batch.rows:
            stored = self._records.get(row.key)
            if stored is None:
                new_rows.append(row)
            elif stored != _record(row, batch.partition):
                raise ValueError(
                    f"{_MODULE}: row {row.key!r} is a conflict: persisted {stored!r} but the "
                    f"batch re-delivers {_record(row, batch.partition)!r}; the source was "
                    "rewritten, register it as a new partition instead of overwriting history"
                )
        return new_rows

    def _require_partition_identity(self, batch: Batch) -> None:
        """A partition id already recorded must keep its path and checksum."""
        known = self._partitions.get(batch.partition)
        if known is None:
            return
        if (known["path"], known["sha256"]) != (batch.path, batch.sha256):
            raise ValueError(
                f"{_MODULE}: partition {batch.partition!r} conflict: recorded path "
                f"{known['path']!r} sha256 {known['sha256']!r}, batch has path {batch.path!r} "
                f"sha256 {batch.sha256!r}; a rewritten source needs a new partition id"
            )

    def _require_watermark_order(self, new_rows: Sequence[SourceRow]) -> None:
        """New rows may not precede the watermark: availability only ever advances."""
        earliest = new_rows[0].available_at
        if self._watermark is not None and earliest < _parse(self._watermark):
            raise ValueError(
                f"{_MODULE}: batch would regress the watermark: its earliest new row "
                f"{new_rows[0].key!r} is available at {iso_utc(earliest)}, before the "
                f"persisted watermark {self._watermark}; consume partitions in order"
            )

    def _write(self) -> None:
        """Persist the whole ledger atomically (temp file + rename) with a canonical layout."""
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "watermark": self._watermark,
            "partitions": self._partitions,
            "rows": self._records,
        }
        self._directory.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(temp, self.path)

    def maturity(self, key: str) -> str:
        """`"mature"` if the row's label_time is at or before the watermark, else `"pending"`."""
        record = self._records[key]
        assert self._watermark is not None  # a persisted row implies a watermark
        return _MATURE if record["label_time"] <= self._watermark else _PENDING

    def visible_keys(self, cutoff: datetime) -> tuple[str, ...]:
        """Keys available at or before `cutoff` (inclusive), in availability order."""
        return self._keys_where(cutoff, mature_only=False)

    def mature_keys(self, cutoff: datetime) -> tuple[str, ...]:
        """Visible keys whose label_time is at or before `cutoff` (inclusive, RWT-24)."""
        return self._keys_where(cutoff, mature_only=True)

    def _keys_where(self, cutoff: datetime, *, mature_only: bool) -> tuple[str, ...]:
        """Keys visible at `cutoff`, optionally only the mature ones, ordered by availability."""
        require_utc(cutoff, what="cutoff")
        bound = iso_utc(cutoff)
        chosen = [
            (record["available_at"], key)
            for key, record in self._records.items()
            if record["available_at"] <= bound
            and (not mature_only or record["label_time"] <= bound)
        ]
        return tuple(key for _, key in sorted(chosen))


def consume(directory: Path, batch: Batch) -> Ledger:
    """Open the ledger under `directory`, consume `batch` and return the updated ledger."""
    return Ledger.open(directory).consume(batch)


def file_sha256(path: Path) -> str:
    """Hex sha256 of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_partition(path: Path, *, partition: str) -> Batch:
    """A `Batch` from one parquet partition file with columns key/available_at/label_time/label.

    The file's row-group metadata is the declared bar count and its bytes' sha256 the
    partition identity. Timestamp columns must be tz-aware UTC; naive columns surface as
    naive datetimes and are rejected by `consume`.
    """
    table: Any = pq.read_table(path, columns=list(_PARQUET_COLUMNS))  # type: ignore[no-untyped-call]
    columns = [table.column(name).to_pylist() for name in _PARQUET_COLUMNS]
    rows = tuple(
        SourceRow(key=str(key), available_at=available_at, label_time=label_time, label=int(label))
        for key, available_at, label_time, label in zip(*columns, strict=True)
    )
    return Batch(
        partition=partition,
        rows=rows,
        declared_bars=int(pq.read_metadata(path).num_rows),  # type: ignore[no-untyped-call]
        path=str(path),
        sha256=file_sha256(path),
    )
