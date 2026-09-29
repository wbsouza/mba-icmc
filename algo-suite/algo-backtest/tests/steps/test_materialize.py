"""Steps for materialize.feature — canonical Parquet -> lean-data, idempotent + CLI."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from algo_backtest.cli import app
from algo_backtest.materialize import MaterializeStatus, materialize_month
from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import lean_data_dir_for, price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/materialize.feature")

_EURUSD = build_instrument("EURUSD")
_UTC = ZoneInfo("UTC")


def _bars(count: int) -> list[QuoteBar]:
    """`count` consecutive minute bars from 2014-07-15 12:00 UTC, distinct prices."""
    start = datetime(2014, 7, 15, 12, 0, tzinfo=UTC)
    out = []
    for i in range(count):
        bid = round(1.10000 + i * 0.00010, 5)
        ask = round(1.20000 + i * 0.00010, 5)
        out.append(
            QuoteBar(
                timestamp=start + timedelta(minutes=i),
                bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid,
                ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask,
                tick_count=1,
            )
        )
    return out


@pytest.fixture
def mat_ctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Tmp data root + empty conf dir (zero-config => UTC) with a clean ALGO_ env."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    data_root = tmp_path / "data"
    monkeypatch.setenv("ALGO_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    monkeypatch.setenv("ALGO_BROKER__ADAPTER", "oanda")
    return {"data_root": data_root, "monkeypatch": monkeypatch}


@given(parsers.parse("a canonical EUR/USD minute Parquet for {ym} with {count:d} bars on the 15th"))
def _write_parquet(mat_ctx: dict[str, Any], ym: str, count: int) -> None:
    year, month = (int(p) for p in ym.split("-"))
    repo: ParquetRepository[QuoteBar] = ParquetRepository(
        QuoteBar, price_path_for(mat_ctx["data_root"], _EURUSD, Timeframe.M1.value, year, month)
    )
    repo.put(_bars(count))


@given("a canonical EUR/USD minute Parquet for 2014-07 spanning the 15th and 16th")
def _write_two_day_parquet(mat_ctx: dict[str, Any]) -> None:
    bars = [
        _bars(1)[0],  # 2014-07-15 12:00 UTC
        QuoteBar(
            timestamp=datetime(2014, 7, 16, 12, 0, tzinfo=UTC),
            bid_open=1.105, bid_high=1.105, bid_low=1.105, bid_close=1.105,
            ask_open=1.205, ask_high=1.205, ask_low=1.205, ask_close=1.205,
            tick_count=1,
        ),
    ]
    repo: ParquetRepository[QuoteBar] = ParquetRepository(
        QuoteBar, price_path_for(mat_ctx["data_root"], _EURUSD, Timeframe.M1.value, 2014, 7)
    )
    repo.put(bars)


@given(parsers.parse("a canonical EUR/USD minute Parquet for {ym} with 0 bars"))
def _write_empty_parquet(mat_ctx: dict[str, Any], ym: str) -> None:
    year, month = (int(p) for p in ym.split("-"))
    repo: ParquetRepository[QuoteBar] = ParquetRepository(
        QuoteBar, price_path_for(mat_ctx["data_root"], _EURUSD, Timeframe.M1.value, year, month)
    )
    repo.put([])


@given("EUR/USD 2014-07 has already been materialized")
def _premateralized(mat_ctx: dict[str, Any]) -> None:
    materialize_month(mat_ctx["data_root"], _EURUSD, 2014, 7, _UTC)


@when(parsers.parse("I materialize EUR/USD for {ym}"))
def _materialize(mat_ctx: dict[str, Any], ym: str) -> None:
    year, month = (int(p) for p in ym.split("-"))
    mat_ctx["result"] = mat_ctx["error"] = None
    try:
        mat_ctx["result"] = materialize_month(mat_ctx["data_root"], _EURUSD, year, month, _UTC)
    except Exception as exc:  # noqa: BLE001 — asserted in the Then steps
        mat_ctx["error"] = exc


@when(parsers.parse('I run "{command}"'))
def _run_cli(mat_ctx: dict[str, Any], command: str) -> None:
    mat_ctx["cli"] = CliRunner().invoke(app, command.split()[1:])


@then(parsers.parse("the materialize status is {status}"))
def _status(mat_ctx: dict[str, Any], status: str) -> None:
    assert mat_ctx["result"].status is MaterializeStatus[status]


@then(parsers.parse('lean-data has "{name}" for EUR/USD'))
def _has_zip(mat_ctx: dict[str, Any], name: str) -> None:
    out_dir = lean_data_dir_for(mat_ctx["data_root"], _EURUSD, "minute")
    assert (out_dir / name).is_file()


@then(parsers.parse("{count:d} day was written"))
def _one_written(mat_ctx: dict[str, Any], count: int) -> None:
    assert len(mat_ctx["result"].written) == count


@then(parsers.parse("{count:d} days were written"))
def _n_written(mat_ctx: dict[str, Any], count: int) -> None:
    assert len(mat_ctx["result"].written) == count


@then("materializing fails with a missing-source error")
def _missing_source(mat_ctx: dict[str, Any]) -> None:
    assert isinstance(mat_ctx["error"], FileNotFoundError)


@then("materializing fails with an empty-source error")
def _empty_source(mat_ctx: dict[str, Any]) -> None:
    assert isinstance(mat_ctx["error"], ValueError)
    assert "empty" in str(mat_ctx["error"]).lower()


@then("no temporary files remain in the lean-data store")
def _no_temp_files(mat_ctx: dict[str, Any]) -> None:
    import zipfile

    out_dir = lean_data_dir_for(mat_ctx["data_root"], _EURUSD, "minute")
    assert list(out_dir.glob("*.tmp")) == []
    # every produced zip is a complete, readable archive (atomic rename succeeded)
    zips = list(out_dir.glob("*_quote.zip"))
    assert zips
    for zip_path in zips:
        with zipfile.ZipFile(zip_path) as zf:
            assert zf.namelist()


@then("the command exits successfully")
def _cli_ok(mat_ctx: dict[str, Any]) -> None:
    assert mat_ctx["cli"].exit_code == 0, mat_ctx["cli"].output


@then(parsers.parse('the output reports "{needle}"'))
def _output_reports(mat_ctx: dict[str, Any], needle: str) -> None:
    assert needle in mat_ctx["cli"].output
