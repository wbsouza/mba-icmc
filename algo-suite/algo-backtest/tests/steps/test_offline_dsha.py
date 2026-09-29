"""Host acceptance oracles for the DSHA train/serve replay boundary."""

from datetime import datetime, timedelta

import pytest
from algo_backtest.perception.heikin_ashi import OHLC
from algo_backtest.perception.offline import (
    OfflineDoubleSmoothedHeikinAshi,
    OfflineMultiTimeframeHeikinAshi,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/offline_dsha.feature")


@given("an offline DSHA with default periods")
def _default(ctx):
    """Allocate the production smoothing lengths."""
    ctx["indicator"] = OfflineDoubleSmoothedHeikinAshi()


@given(parsers.parse("an offline DSHA with periods {first:d} and {second:d}"))
def _indicator(ctx, first, second):
    """Allocate independently configured smoothing histories."""
    ctx["indicator"] = OfflineDoubleSmoothedHeikinAshi(first, second)


@when("six candles have OHLC 10 14 8 12")
def _six(ctx):
    """Feed fewer candles than the complete two-pass warm-up."""
    for _ in range(6):
        ctx["indicator"].update(OHLC(10, 14, 8, 12))


@then("offline DSHA refuses premature output")
def _unready(ctx):
    """Require an explicit readiness error, including the direction accessor."""
    assert not ctx["indicator"].is_ready
    with pytest.raises(ValueError, match="not ready"):
        _ = ctx["indicator"].smoothed_values
    with pytest.raises(ValueError, match="not ready"):
        _ = ctx["indicator"].direction


@when("the seventh candle has OHLC 14 18 12 16")
def _seventh(ctx):
    """Change all first-pass fields at the readiness boundary."""
    ctx["indicator"].update(OHLC(14, 18, 12, 16))


@then("offline smoothed buffers match 94/9 112/9 11 103/9")
def _oracle(ctx):
    """Use the same hand-computed oracle as the independent native probe."""
    assert ctx["indicator"].is_ready
    assert ctx["indicator"].smoothed_values == pytest.approx(
        (94 / 9, 112 / 9, 11, 103 / 9), rel=0, abs=1e-10
    )
    assert ctx["indicator"].direction == -1


@when("flat candles at 1 3 8 are replayed")
def _flat_seed(ctx):
    """Seed Wilder from nonconstant samples whose mean is exactly four."""
    for value in (1, 3, 8):
        ctx["indicator"].update(OHLC(value, value, value, value))


@when("a flat candle at 10 is replayed")
def _flat_next(ctx):
    """Exercise recurrence after the SMA initialization boundary."""
    ctx["indicator"].update(OHLC(10, 10, 10, 10))


@then(parsers.parse("offline smoothed buffers equal {near:g} {far:g} {open_:g} {close:g}"))
def _values(ctx, near, far, open_, close):
    """Check all transformed fields rather than direction alone."""
    assert ctx["indicator"].smoothed_values == (near, far, open_, close)


@given(parsers.parse(
    "offline timeframes with periods {first:d} and {second:d} over {higher:d} minutes"
))
def _timeframes(ctx, first, second, higher):
    """Allocate a minute-stream replay with a separately warmed higher history."""
    ctx["timeframes"] = OfflineMultiTimeframeHeikinAshi(first, second, higher)


@when(parsers.parse("{count:d} minutes of OHLC 10 14 8 12 start at {start}"))
@when(parsers.parse("four minutes of OHLC 10 14 8 12 start at {start}"))
def _minutes(ctx, start, count=4):
    """Pass explicit minute START times, never preaggregated future data."""
    for minute in range(count):
        ctx["timeframes"].update(
            datetime.fromisoformat(start) + timedelta(minutes=minute), OHLC(10, 14, 8, 12)
        )


@when(parsers.parse("OHLC {o:g} {h:g} {low:g} {c:g} arrives at {timestamp}"))
def _minute(ctx, o, h, low, c, timestamp):
    """Deliver one completed minute, allowing real gaps in the input stream."""
    ctx["timeframes"].update(datetime.fromisoformat(timestamp), OHLC(o, h, low, c))


@then("offline timeframes refuse premature output")
def _timeframes_unready(ctx):
    """Prevent incomplete higher buckets becoming training features."""
    assert not ctx["timeframes"].is_ready
    with pytest.raises(ValueError, match="not ready"):
        ctx["timeframes"].features()


@then(parsers.parse("offline primary and higher directions are {primary:g} and {higher:g}"))
def _directions(ctx, primary, higher):
    """Check both feature names and exact values, including historical ties."""
    assert ctx["timeframes"].is_ready
    assert ctx["timeframes"].features() == {
        "trend_direction": primary, "higher_tf_trend_direction": higher,
    }


@when(parsers.parse("offline timeframes are constructed with {first:d} {second:d} {higher:d}"))
def _invalid(ctx, first, second, higher):
    """Capture invalid constructor inputs before any data replay."""
    with pytest.raises(ValueError) as error:
        OfflineMultiTimeframeHeikinAshi(first, second, higher)
    ctx["error"] = str(error.value)


@then("offline construction fails with a period remediation")
def _invalid_message(ctx):
    """Make the failure actionable for an invalid strategy configuration."""
    assert "must be" in ctx["error"]
    assert "period" in ctx["error"] or "higher_tf_minutes" in ctx["error"]
