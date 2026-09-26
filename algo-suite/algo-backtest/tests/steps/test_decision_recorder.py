"""Steps for decision_recorder.feature — DecisionRecorder's per-run trade_id bookkeeping."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest
from algo_backtest.chain.audit import DecisionRow
from algo_backtest.chain.decision_recorder import DecisionRecorder
from algo_backtest.chain.model import ChainOutcome, Decision, ExecutionState
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/decision_recorder.feature")


@dataclass
class _RecorderCtx:
    """Per-scenario fixture context."""

    recorder: DecisionRecorder = field(default_factory=DecisionRecorder)
    path: Path | None = None
    read_back: list[DecisionRow] = field(default_factory=list)


@pytest.fixture
def recorder_ctx() -> _RecorderCtx:
    """A fresh per-scenario context."""
    return _RecorderCtx()


@given("a decision recorder")
def _given_recorder(recorder_ctx: _RecorderCtx) -> None:
    """No-op: `recorder_ctx` already builds a fresh `DecisionRecorder`."""


@when(parsers.parse('trade "{trade_id}" is opened'))
def _open_trade(recorder_ctx: _RecorderCtx, trade_id: str) -> None:
    recorder_ctx.recorder.open_trade(trade_id)


@when(parsers.parse('trade "{trade_id}" is closed'))
def _close_trade(recorder_ctx: _RecorderCtx, trade_id: str) -> None:
    recorder_ctx.recorder.close_trade()


@when(parsers.parse('a "{decision}" decision for pair "{pair}" is recorded'))
def _record_decision(recorder_ctx: _RecorderCtx, decision: str, pair: str) -> None:
    state = ExecutionState(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC), pair=pair, features={"probe": True}
    )
    outcome = ChainOutcome(decision=Decision(decision), state=state)
    recorder_ctx.recorder.record(outcome)


@then(parsers.parse('the last recorded row\'s trade_id is "{trade_id}"'))
def _last_row_trade_id(recorder_ctx: _RecorderCtx, trade_id: str) -> None:
    assert recorder_ctx.recorder._rows[-1].trade_id == trade_id  # noqa: SLF001


@then("the last recorded row's trade_id is absent")
def _last_row_trade_id_absent(recorder_ctx: _RecorderCtx) -> None:
    assert recorder_ctx.recorder._rows[-1].trade_id is None  # noqa: SLF001


@then(parsers.parse('recorded row {index:d}\'s trade_id is "{trade_id}"'))
def _nth_row_trade_id(recorder_ctx: _RecorderCtx, index: int, trade_id: str) -> None:
    assert recorder_ctx.recorder._rows[index - 1].trade_id == trade_id  # noqa: SLF001


@then(parsers.parse("recorded row {index:d}'s trade_id is absent"))
def _nth_row_trade_id_absent(recorder_ctx: _RecorderCtx, index: int) -> None:
    assert recorder_ctx.recorder._rows[index - 1].trade_id is None  # noqa: SLF001


@when(parsers.parse('the recorder is written to "{filename}"'))
def _write_recorder(recorder_ctx: _RecorderCtx, tmp_path: Path, filename: str) -> None:
    recorder_ctx.path = tmp_path / filename
    recorder_ctx.recorder.write(recorder_ctx.path)


@then("the Parquet file exists on disk")
def _file_exists(recorder_ctx: _RecorderCtx) -> None:
    assert recorder_ctx.path is not None
    assert recorder_ctx.path.exists()


@then(parsers.parse("it contains {count:d} rows"))
def _row_count(recorder_ctx: _RecorderCtx, count: int) -> None:
    assert recorder_ctx.path is not None
    repo: ParquetRepository[DecisionRow] = ParquetRepository(DecisionRow, recorder_ctx.path)
    recorder_ctx.read_back = repo.read_all()
    assert len(recorder_ctx.read_back) == count


@then(parsers.parse('row {index:d} read back has trade_id "{trade_id}" and pair "{pair}"'))
def _read_back_row(recorder_ctx: _RecorderCtx, index: int, trade_id: str, pair: str) -> None:
    row = next(r for r in recorder_ctx.read_back if r.pair == pair)
    assert row.trade_id == trade_id


@then(parsers.parse("row {index:d} read back has trade_id absent and pair \"{pair}\""))
def _read_back_row_absent(recorder_ctx: _RecorderCtx, index: int, pair: str) -> None:
    row = next(r for r in recorder_ctx.read_back if r.pair == pair)
    assert row.trade_id is None
