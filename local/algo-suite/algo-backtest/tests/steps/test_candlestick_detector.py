"""BDD recognition and validation with real TA-Lib and synthetic OHLC fixtures."""

from __future__ import annotations

import json
from dataclasses import replace
from itertools import permutations
from typing import Any

import numpy as np
import pytest
import talib
from algo_backtest.perception.candlestick import CandleDetector, detect_pattern, select_pattern
from algo_backtest.perception.heikin_ashi import OHLC
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/candlestick_detector.feature")

_CONTEXT = OHLC(10, 10.6, 9.8, 10.4)
_FIXTURES = {
    "bullish_engulfing": [OHLC(10, 10.1, 8.9, 9), OHLC(8.8, 10.4, 8.7, 10.3)],
    "bearish_engulfing": [OHLC(9, 10.1, 8.9, 10), OHLC(10.2, 10.3, 8.7, 8.8)],
    "hammer": [OHLC(9.7, 9.82, 8.5, 9.8)],
    "shooting_star": [OHLC(10.6, 12, 10.58, 10.7)],
    "morning_star": [
        OHLC(10, 10.1, 7.9, 8),
        OHLC(7.5, 7.7, 7.4, 7.6),
        OHLC(7.8, 9.5, 7.7, 9.4),
    ],
    "evening_star": [
        OHLC(10, 12.1, 9.9, 12),
        OHLC(12.5, 12.7, 12.4, 12.6),
        OHLC(12.2, 12.3, 10.5, 10.6),
    ],
}
_BULLISH = {"bullish_engulfing", "hammer", "morning_star"}
_BEARISH = {"bearish_engulfing", "shooting_star", "evening_star"}


@pytest.fixture
def candle_ctx() -> dict[str, Any]:
    """Keep candle detector scenarios isolated from other step modules."""
    return {}


def _raw_signals(bars: list[OHLC], penetration: float = 0.3) -> dict[str, int]:
    """Call TA-Lib directly without the production detector or selection helper."""
    arrays = np.asarray([bar.values() for bar in bars], dtype=np.float64).T
    engulfing = int(talib.CDLENGULFING(*arrays)[-1])
    return {
        "bullish_engulfing": engulfing if engulfing > 0 else 0,
        "bearish_engulfing": engulfing if engulfing < 0 else 0,
        "hammer": int(talib.CDLHAMMER(*arrays)[-1]),
        "shooting_star": int(talib.CDLSHOOTINGSTAR(*arrays)[-1]),
        "morning_star": int(talib.CDLMORNINGSTAR(*arrays, penetration=penetration)[-1]),
        "evening_star": int(talib.CDLEVENINGSTAR(*arrays, penetration=penetration)[-1]),
    }


def _oracle(bars: list[OHLC]) -> str | None:
    """Resolve a full prefix with an independent explicit directional policy."""
    raw = _raw_signals(bars)
    bullish = sorted(name for name in _BULLISH if raw[name] > 0)
    bearish = sorted(name for name in _BEARISH if raw[name] < 0)
    if bullish and bearish:
        return None
    active = bullish + bearish
    return active[0] if active else None


@given(parsers.parse('a recognition fixture for "{pattern}" with {count:d} context candles'))
def recognition_fixture(candle_ctx: dict[str, Any], pattern: str, count: int) -> None:
    """Place an unambiguous recognition shape after a controllable warmup."""
    candle_ctx["bars"] = [_CONTEXT] * count + _FIXTURES[pattern]


@given(parsers.parse("{count:d} flat recognition candles"))
def flat_fixture(candle_ctx: dict[str, Any], count: int) -> None:
    """Allow equal OHLC prices, including completely empty input."""
    candle_ctx["bars"] = [OHLC(10, 10, 10, 10)] * count


@when("the recognition candles are processed by batch and streaming detectors")
def process_candles(candle_ctx: dict[str, Any]) -> None:
    """Evaluate both public entry points without replacing native recognizers."""
    bars = candle_ctx["bars"]
    detector = CandleDetector()
    outputs = [detector.update(bar) for bar in bars]
    candle_ctx.update(batch=detect_pattern(bars), streaming=outputs[-1] if outputs else None)


@then(parsers.parse('both detectors report "{pattern}"'))
def assert_recognition(candle_ctx: dict[str, Any], pattern: str) -> None:
    """Pin exact public names rather than accepting any nonempty signal."""
    expected = None if pattern == "none" else pattern
    assert candle_ctx["batch"] == expected
    assert candle_ctx["streaming"] == expected


@then(parsers.parse('the real TA-Lib output confirms "{pattern}"'))
def assert_native_recognition(candle_ctx: dict[str, Any], pattern: str) -> None:
    """Require a native hit with the expected sign for the recognition fixture."""
    assert _raw_signals(candle_ctx["bars"])[pattern] == (100 if pattern in _BULLISH else -100)


@given(parsers.parse('an engulfing fixture with direction "{direction}" and one equal body edge'))
def edge_touch(candle_ctx: dict[str, Any], direction: str) -> None:
    """TA-Lib recognizes an engulfing candle with one equal edge at magnitude 80."""
    pair = list(_FIXTURES[f"{direction}_engulfing"])
    pair[-1] = replace(pair[-1], open=pair[0].close)
    candle_ctx["bars"] = [_CONTEXT] * 20 + pair


@then(parsers.parse("real TA-Lib gives the engulfing score {score:d}"))
def assert_edge_score(candle_ctx: dict[str, Any], score: int) -> None:
    """Distinguish native 80 hits from implementations that only accept 100."""
    raw = _raw_signals(candle_ctx["bars"])
    assert raw["bullish_engulfing"] + raw["bearish_engulfing"] == score


@given(parsers.parse('a "{pattern}" fixture closing 40 percent into the first body'))
def star_penetration(candle_ctx: dict[str, Any], pattern: str) -> None:
    """Use a third candle that clears 0.3 penetration but fails 0.5."""
    bars = list(_FIXTURES[pattern])
    bars[-1] = replace(bars[-1], close=8.8 if pattern == "morning_star" else 11.2)
    candle_ctx.update(bars=[_CONTEXT] * 20 + bars, star=pattern)


@then("real TA-Lib recognizes that star at penetration 0.3 but not 0.5")
def assert_penetration(candle_ctx: dict[str, Any]) -> None:
    """Ensure the test actually distinguishes the chosen penetration setting."""
    assert _raw_signals(candle_ctx["bars"], 0.3)[candle_ctx["star"]] != 0
    assert _raw_signals(candle_ctx["bars"], 0.5)[candle_ctx["star"]] == 0


@given("a varied recognition history spanning at least 500 candles and all six patterns")
def varied_history(candle_ctx: dict[str, Any]) -> None:
    """Exercise repeated buffer eviction, differing price scales, gaps and mixed bodies."""
    bars = []
    for scale in (0.125, 1.0, 8.0):
        for shape in _FIXTURES.values():
            bars.extend(
                OHLC(*(price * scale for price in bar.values())) for bar in [_CONTEXT] * 30 + shape
            )
    rng = np.random.default_rng(20260927)
    for _ in range(150):
        open_, close = rng.uniform(5, 15, 2)
        bars.append(OHLC(open_, max(open_, close) + 0.7, min(open_, close) - 0.3, close))
    assert len(bars) >= 500
    candle_ctx["bars"] = bars


@when("every recognition prefix is evaluated independently with real TA-Lib")
def process_prefixes(candle_ctx: dict[str, Any]) -> None:
    """Compare each streaming result to full batch and native full-prefix evaluation."""
    detector = CandleDetector()
    bars = candle_ctx["bars"]
    candle_ctx.update(detector=detector, outputs=[], batches=[], oracle=[], retained=[])
    for end, bar in enumerate(bars, 1):
        candle_ctx["outputs"].append(detector.update(bar))
        candle_ctx["batches"].append(detect_pattern(bars[:end]))
        candle_ctx["oracle"].append(_oracle(bars[:end]))
        candle_ctx["retained"].append(len(detector._candles))


@then("streaming and batch signals match the independent oracle at every prefix")
def assert_prefixes(candle_ctx: dict[str, Any]) -> None:
    """Cover warmup, signal changes and rollovers, not only the final observation."""
    assert candle_ctx["outputs"] == candle_ctx["oracle"]
    assert candle_ctx["batches"] == candle_ctx["oracle"]


@then("the history actually emits all six supported names")
def assert_vocabulary(candle_ctx: dict[str, Any]) -> None:
    """Prevent an all-abstain implementation from satisfying parity alone."""
    assert set(candle_ctx["outputs"]) == _BULLISH | _BEARISH | {None}


@then("the streaming detector retains at most 64 candles")
def assert_bounded(candle_ctx: dict[str, Any]) -> None:
    """Bound retained history throughout the replay, after many evictions."""
    assert max(candle_ctx["retained"]) <= 64
    assert tuple(candle_ctx["detector"]._candles) == tuple(candle_ctx["bars"][-64:])


@when("the same prefix is streamed before two different future suffixes")
def diverging_futures(candle_ctx: dict[str, Any]) -> None:
    """Replay the identical prefix with strongly bullish and bearish future suffixes."""
    prefix = candle_ctx["bars"]
    candle_ctx["prefix_outputs"] = []
    for pattern in ("morning_star", "evening_star"):
        detector = CandleDetector()
        outputs = [detector.update(bar) for bar in prefix + [_CONTEXT] * 20 + _FIXTURES[pattern]]
        candle_ctx["prefix_outputs"].append(outputs[: len(prefix)])
    candle_ctx["prefix_oracle"] = [_oracle(prefix[:end]) for end in range(1, len(prefix) + 1)]


@then('the observed prefix signals are identical and end in "bullish_engulfing"')
def assert_causal(candle_ctx: dict[str, Any]) -> None:
    """Future observations do not participate in prefix decisions."""
    first, second = candle_ctx["prefix_outputs"]
    assert first == second == candle_ctx["prefix_oracle"]
    assert first[-1] == "bullish_engulfing"


@when("a flat candle follows the recognized pattern")
def clear_signal(candle_ctx: dict[str, Any]) -> None:
    """Return the current candle's recognition instead of a cached previous hit."""
    assert detect_pattern(candle_ctx["bars"]) == "bearish_engulfing"
    candle_ctx["bars"] += [OHLC(10, 10, 10, 10)]
    process_candles(candle_ctx)


@given(parsers.parse("raw pattern detections {detections}"))
def raw_mapping(candle_ctx: dict[str, Any], detections: str) -> None:
    """Load explicit native-style scores, including invalid boundary inputs."""
    candle_ctx["detections"] = json.loads(detections)


@given(parsers.parse('real overlapping hammer and "{direction}" engulfing candles'))
def overlapping_recognizers(candle_ctx: dict[str, Any], direction: str) -> None:
    """Use bodies satisfying native engulfing and lower shadows satisfying native hammer."""
    pair = [OHLC(9.7, 9.85, 9.5, 9.8), OHLC(9.85, 9.87, 8.5, 9.65)]
    if direction == "bullish":
        pair = [replace(bar, open=bar.close, close=bar.open) for bar in pair]
    candle_ctx["bars"] = [_CONTEXT] * 20 + pair


@then(parsers.parse('real TA-Lib reports both hammer and "{direction}" engulfing'))
def assert_native_overlap(candle_ctx: dict[str, Any], direction: str) -> None:
    """Prove abstention or priority is exercised by simultaneous actual recognizer hits."""
    raw = _raw_signals(candle_ctx["bars"])
    assert raw["hammer"] == 100
    assert raw[f"{direction}_engulfing"] == (100 if direction == "bullish" else -100)


@when("pattern selection runs in every insertion order")
def select_permutations(candle_ctx: dict[str, Any]) -> None:
    """Exercise every ordering so the winning name cannot depend on dict order."""
    candle_ctx["selections"] = [
        select_pattern(dict(items)) for items in permutations(candle_ctx["detections"].items())
    ]


@then(parsers.parse('every selection reports "{expected}"'))
def assert_selections(candle_ctx: dict[str, Any], expected: str) -> None:
    """Selection follows lexical priority within a sign and abstains on conflict."""
    assert set(candle_ctx["selections"]) == {None if expected == "none" else expected}


@when("pattern selection rejects the invalid mapping")
def reject_mapping(candle_ctx: dict[str, Any]) -> None:
    """Invalid vocabulary, types and contradictory signs fail at the public boundary."""
    with pytest.raises(ValueError) as error:
        select_pattern(candle_ctx["detections"])
    candle_ctx["error"] = str(error.value)


def _invalid_price(value: str) -> Any:
    """Represent non-JSON runtime numeric types without coercing malformed prices."""
    special = {"complex": 10 + 1j, "huge_integer": 10**400, "numpy_bool": np.bool_(True)}
    return special[value] if value in special else json.loads(value)


@given(parsers.parse('a candle whose "{field}" price is {value}'))
def invalid_field(candle_ctx: dict[str, Any], field: str, value: str) -> None:
    """Corrupt exactly one field of an otherwise valid candle."""
    candle_ctx["invalid"] = replace(_CONTEXT, **{field: _invalid_price(value)})


@given(parsers.parse("a candle with OHLC {prices}"))
def invalid_order(candle_ctx: dict[str, Any], prices: str) -> None:
    """Use valid numeric prices with impossible extrema."""
    candle_ctx["invalid"] = OHLC(*json.loads(prices))


@when("batch and streaming detection reject that candle")
def reject_candle(candle_ctx: dict[str, Any]) -> None:
    """Validate before eviction, with a full streaming buffer and malformed latest bar."""
    detector = CandleDetector()
    for bar in [_CONTEXT] * 63 + _FIXTURES["bullish_engulfing"][:1]:
        detector.update(bar)
    candle_ctx.update(detector=detector, before=tuple(detector._candles), errors=[])
    with pytest.raises(ValueError) as batch_error:
        detect_pattern([_CONTEXT, candle_ctx["invalid"]])
    with pytest.raises(ValueError) as stream_error:
        detector.update(candle_ctx["invalid"])
    candle_ctx["errors"] = [str(batch_error.value), str(stream_error.value)]


@then(parsers.parse('both errors identify "{field}" and a remedy'))
def assert_errors(candle_ctx: dict[str, Any], field: str) -> None:
    """Validation errors must name the field and explain the corrective action."""
    for message in candle_ctx["errors"]:
        assert field in message
        assert "repair" in message.lower()


@then("rejected input does not consume or evict streaming history")
def assert_unchanged(candle_ctx: dict[str, Any]) -> None:
    """A rejected candle leaves a warmed detector ready for the next valid signal."""
    detector = candle_ctx["detector"]
    assert tuple(detector._candles) == candle_ctx["before"]
    assert detector.update(_FIXTURES["bullish_engulfing"][-1]) == "bullish_engulfing"


@when("batch detection receives it before 80 valid candles")
def reject_old_candle(candle_ctx: dict[str, Any]) -> None:
    """The batch API validates the whole supplied sequence, including old history."""
    with pytest.raises(ValueError) as error:
        detect_pattern([candle_ctx["invalid"]] + [_CONTEXT] * 80)
    candle_ctx["error"] = str(error.value)


@then(parsers.parse('the detector error identifies "{field}" and a remedy'))
def assert_error(candle_ctx: dict[str, Any], field: str) -> None:
    """Fail-fast public errors identify a corrupt field and its remediation."""
    assert field in candle_ctx["error"]
    assert "repair" in candle_ctx["error"].lower()


@given(parsers.parse('valid recognition candles with "{kind}" prices'))
def numeric_prices(candle_ctx: dict[str, Any], kind: str) -> None:
    """Accept standard real scalar types while providing TA-Lib with float64 arrays."""
    converter = {"integer": int, "numpy_integer": np.int64, "numpy_float": np.float64}[kind]
    candle_ctx["bars"] = [
        OHLC(*(converter(round(price * 100)) for price in bar.values()))
        for bar in [_CONTEXT] * 20 + _FIXTURES["bullish_engulfing"]
    ]
