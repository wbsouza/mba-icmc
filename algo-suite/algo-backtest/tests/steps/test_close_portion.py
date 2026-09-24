"""Steps for close_portion.feature — the partial-close ladder mechanic."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from algo_backtest.rules.close_portion import CloseLadder, build_close_ladder
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/close_portion.feature")


@dataclass
class _CloseLadderCtx:
    """Per-scenario original lot size + rung portions, plus the outcome (ladder xor error)."""

    original_lot_size: float = 0.0
    portions: list[float] = field(default_factory=list)
    ladder: CloseLadder | None = None
    error: Exception | None = None


@pytest.fixture
def ladder_ctx() -> _CloseLadderCtx:
    return _CloseLadderCtx()


@given(parsers.parse("an original lot size of {lot_size:g}"))
def _lot_size(ladder_ctx: _CloseLadderCtx, lot_size: float) -> None:
    ladder_ctx.original_lot_size = lot_size


@given(parsers.parse("a close-portion ladder of {portions}"))
def _portions(ladder_ctx: _CloseLadderCtx, portions: str) -> None:
    ladder_ctx.portions = [float(p.strip()) for p in portions.split(",")]


@when("I build the close ladder")
def _build(ladder_ctx: _CloseLadderCtx) -> None:
    try:
        ladder_ctx.ladder = build_close_ladder(ladder_ctx.original_lot_size, ladder_ctx.portions)
    except ValueError as exc:
        ladder_ctx.error = exc


@then(parsers.parse("rung {n:d} closes {lot_to_close:g} lots with {remaining:g} remaining"))
def _assert_rung(
    ladder_ctx: _CloseLadderCtx, n: int, lot_to_close: float, remaining: float
) -> None:
    assert ladder_ctx.error is None, f"unexpected error: {ladder_ctx.error}"
    assert ladder_ctx.ladder is not None
    rung = ladder_ctx.ladder.rungs[n - 1]
    assert rung.level == n
    assert rung.lot_to_close == pytest.approx(lot_to_close)
    assert rung.lot_remaining == pytest.approx(remaining)


@then("building the ladder fails with an over-close error")
def _assert_over_close(ladder_ctx: _CloseLadderCtx) -> None:
    assert isinstance(ladder_ctx.error, ValueError)
    assert "over-close" in str(ladder_ctx.error)


@then("building the ladder fails with an invalid-portion error")
def _assert_invalid_portion(ladder_ctx: _CloseLadderCtx) -> None:
    assert isinstance(ladder_ctx.error, ValueError)
    assert "must be in (0, 1]" in str(ladder_ctx.error)


@then("building the ladder fails with a non-positive-lot error")
def _assert_non_positive_lot(ladder_ctx: _CloseLadderCtx) -> None:
    assert isinstance(ladder_ctx.error, ValueError)
    assert "original_lot_size" in str(ladder_ctx.error)
