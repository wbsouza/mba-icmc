"""BDD for real candle detection and causal quote-activity gates."""

import json
from datetime import UTC, datetime

import pytest
from algo_backtest.chain.filters.volume_strength import VolumeConfig, VolumeStrengthFilter
from algo_backtest.chain.model import ExecutionState, Recommendation
from algo_backtest.perception.candlestick import CandleDetector, detect_pattern, select_pattern
from algo_backtest.perception.heikin_ashi import OHLC
from algo_backtest.perception.volume import RelativeTickActivity
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/market_signals.feature")


@pytest.fixture
def signals():
    """Per-scenario state."""
    return {}


@given("a warmed candle detector followed by a bullish engulfing pair")
def candles(signals):
    """Use a real TA-Lib-compatible engulfing fixture, not mocked detector output."""
    signals["candles"] = [OHLC(10, 10.2, 9.8, 10)] * 70 + [
        OHLC(10, 10.1, 8.9, 9), OHLC(8.8, 10.4, 8.7, 10.3)]


@when("the candles are processed incrementally")
def incremental(signals):
    """Run the bounded production adapter."""
    detector = CandleDetector()
    signals["outputs"] = [detector.update(bar) for bar in signals["candles"]]
    signals["pattern"] = signals["outputs"][-1]


@then(parsers.parse('the latest pattern is "{name}"'))
def pattern_name(signals, name):
    """Assert the public feature vocabulary."""
    assert signals["pattern"] == name


@then("streaming patterns equal batch-prefix patterns")
def prefixes(signals):
    """Every prefix independently agrees, including when the bounded deque rolls over."""
    bars = signals["candles"]
    assert signals["outputs"] == [detect_pattern(bars[:i]) for i in range(1, len(bars) + 1)]


@when("bullish and bearish TA-Lib detections occur together")
def conflicts(signals):
    """Opposing evidence is ambiguous, regardless of integer magnitude."""
    signals["pattern"] = select_pattern({"hammer": 100, "bearish_engulfing": -80})


@then("the latest pattern is absent")
def no_pattern(signals):
    """Do not pick a side from conflicting detections."""
    assert signals["pattern"] is None


@given(parsers.parse("tick counts {counts} with a lookback of {lookback:d}"))
def counts(signals, counts, lookback):
    """Create a fixed history whose expected ratio is independently obvious."""
    signals["counts"] = [int(value) for value in counts.split(",")]
    signals["activity"] = RelativeTickActivity(lookback)


@when("quote activity is processed")
def activity(signals):
    """Process one closed bar at a time."""
    signals["strengths"] = [signals["activity"].update(n) for n in signals["counts"]]


@then(parsers.parse("relative activity is {expected:f}"))
def ratio(signals, expected):
    """Warm-up has no ratio; the current count is excluded from its own denominator."""
    assert signals["strengths"][:-1] == [None] * 3
    assert signals["strengths"][-1] == expected


@then("relative activity is unavailable")
def unavailable(signals):
    """A zero baseline cannot establish relative activity."""
    assert signals["strengths"][-1] is None


@when(parsers.parse("quote activity receives {value}"))
def invalid_activity(signals, value):
    """Exercise malformed values without coercion."""
    with pytest.raises(ValueError) as error:
        RelativeTickActivity(3).update(json.loads(value))
    signals["error"] = str(error.value)


@then("activity validation reports an error")
def activity_error(signals):
    """The failure identifies the corrupt source field."""
    assert "tick_count" in signals["error"]


@given(parsers.parse("a volume gate threshold of 1.0 and relative activity {strength}"))
def gate_input(signals, strength):
    """Explicitly represent unavailable input as null."""
    signals["state"] = ExecutionState(datetime(2020, 1, 1, tzinfo=UTC), "EURUSD",
                                      {"relative_tick_activity": json.loads(strength)})


@when("the volume gate is applied")
def gate(signals):
    """Apply the real filter."""
    signals["result"] = VolumeStrengthFilter(VolumeConfig()).apply(signals["state"])


@then(parsers.parse("the volume recommendation is ABSTAIN with veto {veto}"))
def gate_outcome(signals, veto):
    """High activity merely permits downstream filters to decide."""
    assert signals["result"].recommendation == Recommendation.ABSTAIN
    assert signals["result"].veto is json.loads(veto)
