"""Step definitions for transform.feature (end-to-end through the CLI)."""

from __future__ import annotations

import lzma
import struct
from pathlib import Path

import pytest
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from algo_core.layout import TickFile, dukascopy_raw_path, price_path_for
from algo_core.repository.parquet import ParquetRepository
from algo_transform.cli import app
from algo_transform.readers.dukascopy import expected_hours
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/transform.feature")

runner = CliRunner()


@pytest.fixture
def context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    monkeypatch.setenv("ALGO_DATA_ROOT", str(tmp_path))
    return {"data_root": tmp_path}


def _root(context: dict[str, object]) -> Path:
    root = context["data_root"]
    assert isinstance(root, Path)
    return root


def _bi5(records: list[tuple[int, int, int, float, float]]) -> bytes:
    return lzma.compress(b"".join(struct.pack(">IIIff", *r) for r in records))


@given("a writable data root")
def _writable(context: dict[str, object]) -> None:
    assert _root(context).is_dir()


@given(parsers.parse(
    "a complete raw month for EURUSD {spec} with tick data in hour {date} {hour:d}h"
))
def _complete_month(context: dict[str, object], spec: str, date: str, hour: int) -> None:
    root = _root(context)
    year, month = (int(p) for p in spec.split("-"))
    for tick in expected_hours("EURUSD", year, month):
        path = dukascopy_raw_path(root, tick)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")  # 0-byte no-data markers everywhere
    _, _, day = (int(p) for p in date.split("-"))
    data = dukascopy_raw_path(
        root, TickFile(symbol="EURUSD", year=year, month=month, day=day, hour=hour)
    )
    data.write_bytes(_bi5([(86, 111966, 111963, 4.39, 0.75), (1086, 111970, 111968, 1.0, 2.0)]))


@given(parsers.parse("the raw hour {date} {hour:d}h is removed"))
def _remove_hour(context: dict[str, object], date: str, hour: int) -> None:
    year, month, day = (int(p) for p in date.split("-"))
    dukascopy_raw_path(
        _root(context), TickFile(symbol="EURUSD", year=year, month=month, day=day, hour=hour)
    ).unlink()


@given(parsers.parse("the raw hour {date} {hour:d}h is corrupt"))
def _corrupt_hour(context: dict[str, object], date: str, hour: int) -> None:
    year, month, day = (int(p) for p in date.split("-"))
    dukascopy_raw_path(
        _root(context), TickFile(symbol="EURUSD", year=year, month=month, day=day, hour=hour)
    ).write_bytes(b"not-valid-lzma")


@when(parsers.parse('I transform "{source}" "{symbol}" "{spec}"'))
def _transform(context: dict[str, object], source: str, symbol: str, spec: str) -> None:
    context["result"] = runner.invoke(
        app, ["run", "--source", source, "--symbol", symbol, "--month", spec]
    )


def _result(context: dict[str, object]):  # type: ignore[no-untyped-def]
    return context["result"]


def _minute_path(context: dict[str, object]) -> Path:
    return price_path_for(_root(context), build_instrument("EURUSD"), "m1", 2020, 1)


@then("a minute Parquet partition exists for EURUSD 2020-01")
def _partition_exists(context: dict[str, object]) -> None:
    assert _minute_path(context).is_file()


@then("it contains at least one QuoteBar")
def _has_bars(context: dict[str, object]) -> None:
    bars = ParquetRepository(QuoteBar, _minute_path(context)).read_all()
    assert len(bars) >= 1


@then("no minute Parquet partition exists for EURUSD 2020-01")
def _partition_absent(context: dict[str, object]) -> None:
    assert not _minute_path(context).exists()


@then("the run exits 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert _result(context).exit_code == 0


@then("the report says the month is incomplete")
def _incomplete(context: dict[str, object]) -> None:
    assert "incomplete" in _result(context).stdout.lower()


@then("the report says the month is corrupt")
def _corrupt(context: dict[str, object]) -> None:
    result = _result(context)
    assert "corrupt" in result.stdout.lower()
    assert result.exit_code != 0
