"""Offline regressions for the loss guard in LEAN RelativeStrengthIndex.cs:104.

The sine expectations are captured native observations at 2014-05-05 03:12
through 03:15 UTC (bar ends) from the closed-signal parity probe. Boundary
expectations independently use decimal midpoint-to-even, as Math.Round does.
"""

import math
from decimal import ROUND_HALF_EVEN, Decimal

import pytest
from algo_backtest.training import _rsi_value, rsi_series
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/rsi_native_rounding.feature")


@given(
    parsers.parse("the first {count:d} midpoint closes from the native sine-35 minute fixture"),
    target_fixture="rsi_closes",
)
def sine_closes(count: int) -> list[float]:
    """Reproduce native bid/ask midpoint inputs before the fixture's missing minute."""
    bids = [round(1.38 + 0.003 * math.sin((i + 1) / 35), 5) for i in range(count)]
    return [(bid + round(bid + 0.0001, 5)) / 2 for bid in bids]


@when("offline RSI is calculated with period 3", target_fixture="actual_rsi")
def sine_rsi(rsi_closes: list[float]) -> float:
    """Exercise the complete production Wilder recurrence through the failing minute."""
    return rsi_series(rsi_closes, 3)[-1]


@then(
    parsers.parse(
        "its last RSI matches native {expected} within 1e-9 absolute and zero relative tolerance"
    )
)
def native_rsi(actual_rsi: float, expected: str) -> None:
    """Preserve the native probe's existing strict comparison tolerance."""
    assert actual_rsi == pytest.approx(float(expected), abs=1e-9, rel=0)


@given(
    parsers.parse("Wilder average gain {gain} and average loss {loss}"),
    target_fixture="wilder_averages",
)
def wilder_averages(gain: str, loss: str) -> tuple[Decimal, Decimal]:
    """Keep the decimal boundary exact until passing inputs to production float code."""
    if loss == "nextafter(5e-11)":
        return Decimal(gain), Decimal.from_float(math.nextafter(5e-11, math.inf))
    return Decimal(gain), Decimal(loss)


@when("offline RSI evaluates those averages", target_fixture="actual_rsi")
def rsi_from_averages(wilder_averages: tuple[Decimal, Decimal]) -> float:
    """Exercise the production helper without mocking or replacing its guard."""
    gain, loss = wilder_averages
    return _rsi_value(float(gain), float(loss))


@then("it matches the decimal midpoint-to-even loss guard")
def decimal_guard(actual_rsi: float, wilder_averages: tuple[Decimal, Decimal]) -> None:
    """Apply the C# decimal guard, retaining the original divisor on its nonzero branch."""
    gain, loss = wilder_averages
    if loss.quantize(Decimal("1e-10"), rounding=ROUND_HALF_EVEN) == 0:
        assert actual_rsi == 100.0
    else:
        expected = Decimal(100) - Decimal(100) / (1 + gain / loss)
        assert actual_rsi == pytest.approx(float(expected), abs=1e-12, rel=0)
