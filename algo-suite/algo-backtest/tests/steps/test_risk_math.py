"""Steps for risk_math.feature — fixed-fractional lot-size formula."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from algo_backtest.rules.risk_math import calculate_lot_size
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/risk_math.feature")


@dataclass
class _LotSizeCtx:
    """Per-scenario inputs to `calculate_lot_size` plus the outcome (result xor error)."""

    balance: float = 0.0
    risk: float = 0.0
    pip_value: float = 0.0
    stop_loss_pips: float = 0.0
    result: float | None = None
    error: Exception | None = None


@pytest.fixture
def lot_ctx() -> _LotSizeCtx:
    return _LotSizeCtx()


@given(parsers.parse("an account balance of {balance:g}"))
def _balance(lot_ctx: _LotSizeCtx, balance: float) -> None:
    lot_ctx.balance = balance


@given(parsers.parse("a risk fraction of {risk:g}"))
def _risk(lot_ctx: _LotSizeCtx, risk: float) -> None:
    lot_ctx.risk = risk


@given(parsers.parse("a pip value of {pip_value:g}"))
def _pip_value(lot_ctx: _LotSizeCtx, pip_value: float) -> None:
    lot_ctx.pip_value = pip_value


@given(parsers.parse("a stop-loss distance of {stop_loss_pips:g} pips"))
def _stop_loss_pips(lot_ctx: _LotSizeCtx, stop_loss_pips: float) -> None:
    lot_ctx.stop_loss_pips = stop_loss_pips


@when("I compute the lot size")
def _compute(lot_ctx: _LotSizeCtx) -> None:
    try:
        lot_ctx.result = calculate_lot_size(
            account_balance=lot_ctx.balance,
            risk=lot_ctx.risk,
            pip_value=lot_ctx.pip_value,
            stop_loss_pips=lot_ctx.stop_loss_pips,
        )
    except ValueError as exc:
        lot_ctx.error = exc


@then(parsers.parse("the computed lot size is {expected:g}"))
def _assert_lot_size(lot_ctx: _LotSizeCtx, expected: float) -> None:
    assert lot_ctx.error is None, f"unexpected error: {lot_ctx.error}"
    assert lot_ctx.result == pytest.approx(expected)


@then("computing the lot size fails with a non-positive-input error")
def _assert_rejected(lot_ctx: _LotSizeCtx) -> None:
    assert isinstance(lot_ctx.error, ValueError)
    assert "must be positive" in str(lot_ctx.error)
