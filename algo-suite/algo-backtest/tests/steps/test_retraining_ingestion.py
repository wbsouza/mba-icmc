"""Steps for retraining_ingestion.feature: the incremental data and label-maturity adapter."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from algo_backtest.retraining.ingestion import (
    LEDGER_FILE,
    Batch,
    Ledger,
    SourceRow,
    consume,
    read_partition,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/retraining_ingestion.feature")

_PARQUET_PARTITION = "eurusd/h1/2016-01"


@dataclass
class _IngestCtx:
    """Per-scenario state: the ledger directory, the named batches and the last failure."""

    directory: Path
    batches: dict[str, Batch] = field(default_factory=dict)
    error: Exception | None = None
    remembered_bytes: bytes | None = None
    remembered_records: dict[str, Any] = field(default_factory=dict)
    parquet_path: Path | None = None


@pytest.fixture
def ingest_ctx(tmp_path: Path) -> _IngestCtx:
    """A fresh context whose ledger directory is empty."""
    return _IngestCtx(directory=tmp_path / "ledger")


def _timestamp(text: str) -> datetime | None:
    """`None` for the literal `None`; otherwise the ISO text as given (naive stays naive)."""
    return None if text == "None" else datetime.fromisoformat(text)


def _cells(datatable: list[list[str]]) -> list[dict[str, str]]:
    """A Gherkin table as one dict per row, keyed by the header."""
    header, *rows = datatable
    return [dict(zip(header, row, strict=True)) for row in rows]


def _rows(datatable: list[list[str]]) -> tuple[SourceRow, ...]:
    """The table's rows as `SourceRow`s."""
    return tuple(
        SourceRow(
            key=cell["key"],
            available_at=datetime.fromisoformat(cell["available_at"]),
            label_time=_timestamp(cell["label_time"]),
            label=int(cell["label"]),
        )
        for cell in _cells(datatable)
    )


def _ledger_bytes(ctx: _IngestCtx) -> bytes | None:
    """The persisted ledger file's bytes, or `None` when no file exists."""
    path = ctx.directory / LEDGER_FILE
    return path.read_bytes() if path.exists() else None


def _persisted_records(ctx: _IngestCtx, keys: str) -> dict[str, Any]:
    """The persisted JSON records of the comma-separated `keys`, read straight from disk."""
    payload = json.loads((ctx.directory / LEDGER_FILE).read_text(encoding="utf-8"))
    return {key.strip(): payload["rows"][key.strip()] for key in keys.split(",")}


def _write_parquet(path: Path, rows: tuple[SourceRow, ...], compression: str = "snappy") -> None:
    """Write rows as one tz-aware-UTC parquet partition file."""
    stamp = pa.timestamp("us", tz="UTC")
    table = pa.table(
        {
            "key": [row.key for row in rows],
            "available_at": pa.array([row.available_at for row in rows], stamp),
            "label_time": pa.array([row.label_time for row in rows], stamp),
            "label": [row.label for row in rows],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression=compression)


@given("an empty ledger directory")
def _empty_directory(ingest_ctx: _IngestCtx) -> None:
    ingest_ctx.directory.mkdir()


@given(parsers.parse('the batch "{name}" from partition "{partition}" carries the rows'))
def _batch(ingest_ctx: _IngestCtx, name: str, partition: str, datatable: list[list[str]]) -> None:
    ingest_ctx.batches[name] = Batch(partition=partition, rows=_rows(datatable))


@given(
    parsers.parse(
        'the batch "{name}" from partition "{partition}" declares {bars:d} bars and carries '
        "the rows"
    )
)
def _declaring_batch(
    ingest_ctx: _IngestCtx, name: str, partition: str, bars: int, datatable: list[list[str]]
) -> None:
    ingest_ctx.batches[name] = Batch(partition=partition, rows=_rows(datatable), declared_bars=bars)


@given(parsers.parse('the batch "{name}" is consumed'))
@when(parsers.parse('the batch "{name}" is consumed'))
@when(parsers.parse('the batch "{name}" is consumed again'))
def _consume(ingest_ctx: _IngestCtx, name: str) -> None:
    consume(ingest_ctx.directory, ingest_ctx.batches[name])


@when(parsers.parse('consuming the batch "{name}" fails'))
def _consume_fails(ingest_ctx: _IngestCtx, name: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        consume(ingest_ctx.directory, ingest_ctx.batches[name])
    ingest_ctx.error = exc_info.value


@when("the ledger is reopened from the same directory")
def _reopen(ingest_ctx: _IngestCtx) -> None:
    """Every Then below reopens from disk, so this step only proves the call itself works."""
    assert Ledger.open(ingest_ctx.directory).path == ingest_ctx.directory / LEDGER_FILE


@then(parsers.parse("the ledger watermark is {stamp}"))
def _watermark(ingest_ctx: _IngestCtx, stamp: str) -> None:
    assert Ledger.open(ingest_ctx.directory).watermark == datetime.fromisoformat(stamp)


@then(parsers.parse("the ledger holds {count:d} rows"))
def _row_count(ingest_ctx: _IngestCtx, count: int) -> None:
    assert Ledger.open(ingest_ctx.directory).row_count == count


@then("the ledger directory contains a ledger file")
def _has_file(ingest_ctx: _IngestCtx) -> None:
    assert (ingest_ctx.directory / LEDGER_FILE).is_file()


@then("the ledger directory contains no ledger file")
def _has_no_file(ingest_ctx: _IngestCtx) -> None:
    assert not (ingest_ctx.directory / LEDGER_FILE).exists()
    assert list(ingest_ctx.directory.iterdir()) == []


@then(parsers.parse('the ingestion failure names "{fragment}"'))
def _failure_names(ingest_ctx: _IngestCtx, fragment: str) -> None:
    assert ingest_ctx.error is not None
    assert fragment in str(ingest_ctx.error)


@then(parsers.parse('the row "{key}" is {state}'))
def _row_state(ingest_ctx: _IngestCtx, key: str, state: str) -> None:
    assert Ledger.open(ingest_ctx.directory).maturity(key) == state


@given("the ledger file bytes are remembered")
def _remember_bytes(ingest_ctx: _IngestCtx) -> None:
    ingest_ctx.remembered_bytes = _ledger_bytes(ingest_ctx)
    assert ingest_ctx.remembered_bytes is not None


@then("the ledger file bytes are unchanged")
def _bytes_unchanged(ingest_ctx: _IngestCtx) -> None:
    assert _ledger_bytes(ingest_ctx) == ingest_ctx.remembered_bytes


@then(parsers.parse('the mature rows as of {stamp} are "{keys}"'))
def _mature_rows(ingest_ctx: _IngestCtx, stamp: str, keys: str) -> None:
    expected = tuple(key.strip() for key in keys.split(",") if key.strip())
    assert Ledger.open(ingest_ctx.directory).mature_keys(datetime.fromisoformat(stamp)) == expected


@then(parsers.parse('the visible rows as of {stamp} are "{keys}"'))
def _visible_rows(ingest_ctx: _IngestCtx, stamp: str, keys: str) -> None:
    expected = tuple(key.strip() for key in keys.split(",") if key.strip())
    ledger = Ledger.open(ingest_ctx.directory)
    assert ledger.visible_keys(datetime.fromisoformat(stamp)) == expected


@given(parsers.parse('the persisted records of the keys "{keys}" are remembered'))
def _remember_records(ingest_ctx: _IngestCtx, keys: str) -> None:
    ingest_ctx.remembered_records = _persisted_records(ingest_ctx, keys)


@then(parsers.parse('the persisted records of the keys "{keys}" are unchanged'))
def _records_unchanged(ingest_ctx: _IngestCtx, keys: str) -> None:
    assert _persisted_records(ingest_ctx, keys) == ingest_ctx.remembered_records


@given(parsers.parse('the rows of the batch "{name}" are written as a parquet partition file'))
def _write_partition(ingest_ctx: _IngestCtx, name: str) -> None:
    ingest_ctx.parquet_path = ingest_ctx.directory.parent / "source" / "eurusd-h1-2016-01.parquet"
    _write_parquet(ingest_ctx.parquet_path, ingest_ctx.batches[name].rows)


def _parquet_batch(ingest_ctx: _IngestCtx) -> Batch:
    """The on-disk partition read back through the adapter's own reader."""
    assert ingest_ctx.parquet_path is not None
    return read_partition(ingest_ctx.parquet_path, partition=_PARQUET_PARTITION)


@given("the parquet partition is consumed")
@when("the parquet partition is consumed")
def _consume_parquet(ingest_ctx: _IngestCtx) -> None:
    consume(ingest_ctx.directory, _parquet_batch(ingest_ctx))


@when("consuming the parquet partition fails")
def _consume_parquet_fails(ingest_ctx: _IngestCtx) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        consume(ingest_ctx.directory, _parquet_batch(ingest_ctx))
    ingest_ctx.error = exc_info.value


@then(parsers.parse("the ledger records that partition's path, sha256 and {count:d} rows"))
def _partition_recorded(ingest_ctx: _IngestCtx, count: int) -> None:
    assert ingest_ctx.parquet_path is not None
    record = Ledger.open(ingest_ctx.directory).partitions[_PARQUET_PARTITION]
    assert record.path == str(ingest_ctx.parquet_path)
    assert record.sha256 == hashlib.sha256(ingest_ctx.parquet_path.read_bytes()).hexdigest()
    assert record.row_count == count


@given(parsers.parse('the same partition file is rewritten with the label of "{key}" flipped'))
def _rewrite_flipped(ingest_ctx: _IngestCtx, key: str) -> None:
    assert ingest_ctx.parquet_path is not None
    rows = _parquet_batch(ingest_ctx).rows
    flipped = tuple(
        SourceRow(row.key, row.available_at, row.label_time, 1 - row.label)
        if row.key == key
        else row
        for row in rows
    )
    _write_parquet(ingest_ctx.parquet_path, flipped)


@given("the same partition file is rewritten with identical rows and different bytes")
def _rewrite_same_rows(ingest_ctx: _IngestCtx) -> None:
    """Same rows, another codec: the file's sha256 changes while its content does not."""
    assert ingest_ctx.parquet_path is not None
    before = hashlib.sha256(ingest_ctx.parquet_path.read_bytes()).hexdigest()
    _write_parquet(ingest_ctx.parquet_path, _parquet_batch(ingest_ctx).rows, compression="gzip")
    assert hashlib.sha256(ingest_ctx.parquet_path.read_bytes()).hexdigest() != before


@when(parsers.parse("querying the mature rows as of {stamp} fails"))
def _mature_query_fails(ingest_ctx: _IngestCtx, stamp: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        Ledger.open(ingest_ctx.directory).mature_keys(datetime.fromisoformat(stamp))
    ingest_ctx.error = exc_info.value
