"""Steps for candle_catalog.feature: the expanded multilabel catalog with real TA-Lib."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pytest
import talib
from algo_backtest.perception.candle_catalog import CandleCatalog, legacy_label
from algo_backtest.perception.candle_contract import (
    CATALOG,
    READY,
    WARMUP,
    CandleConfig,
    CandleEvidence,
    ClosedBar,
    PatternHit,
)
from algo_backtest.perception.candlestick import detect_pattern
from algo_backtest.perception.heikin_ashi import OHLC
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/candle_catalog.feature")

_HOUR = timedelta(hours=1)
_T0 = datetime(2024, 1, 1, tzinfo=UTC)
_CONTEXT = OHLC(1000, 1060, 980, 1040)
_PRIORS = {"bearish": OHLC(1000, 1010, 890, 900), "bullish": OHLC(900, 1010, 890, 1000)}
# The legacy recognition fixtures of test_candlestick_detector.py, verbatim (that module is
# not importable under pytest's importlib import mode).
_FLOAT_CONTEXT = OHLC(10, 10.6, 9.8, 10.4)
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
_LEGACY_SIX = _BULLISH | {"bearish_engulfing", "shooting_star", "evening_star"}


@pytest.fixture
def cat_ctx() -> dict[str, Any]:
    """Per-scenario state: configuration, staged OHLC bars and evidence."""
    return {"config": CandleConfig(), "bars": []}


def _raw_signals(bars: list[OHLC], penetration: float = 0.3) -> dict[str, int]:
    """Call TA-Lib directly, independently of the catalog."""
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


def _closed(bars: list[OHLC]) -> list[ClosedBar]:
    """Hourly UTC closed bars from 01:00 for the given OHLC list."""
    return [ClosedBar(_T0 + _HOUR * (i + 1), *bar.values()) for i, bar in enumerate(bars)]


def _stream(config: CandleConfig, bars: list[OHLC]) -> list[CandleEvidence]:
    """Evidence per bar from a fresh catalog."""
    catalog = CandleCatalog(config, "EURUSD")
    return [catalog.update(bar) for bar in _closed(bars)]


def _ids(raw: str) -> list[str]:
    """A comma-separated id list; the empty string is the empty list."""
    return [item for item in raw.split(",") if item]


def _ready_ids(evidence: CandleEvidence) -> list[str]:
    """The READY hit ids of one evidence."""
    return [hit.id for hit in evidence.ready_hits]


# --- staging --------------------------------------------------------------------------


@given(parsers.parse('the catalog restricted to "{rules}"'))
def restricted(cat_ctx: dict[str, Any], rules: str) -> None:
    """A configuration enabling only the listed rules, in the listed order."""
    cat_ctx["config"] = CandleConfig(enabled_rules=tuple(_ids(rules)))


@given("the default catalog")
def default_catalog(cat_ctx: dict[str, Any]) -> None:
    """The default configuration: every admitted rule."""
    cat_ctx["config"] = CandleConfig()


@given(parsers.parse("the closed bars ({open:g}, {high:g}, {low:g}, {close:g})"))
def single_bar(cat_ctx: dict[str, Any], open: float, high: float, low: float, close: float) -> None:
    """One closed bar."""
    cat_ctx["bars"] = [OHLC(open, high, low, close)]


@given(
    parsers.re(
        r"the closed bars: the (?P<prior>\w+) prior,? then "
        r"\((?P<open>[^,]+), (?P<high>[^,]+), (?P<low>[^,]+), (?P<close>[^)]+)\)"
    ),
    converters={"open": float, "high": float, "low": float, "close": float},
)
def prior_then(
    cat_ctx: dict[str, Any], prior: str, open: float, high: float, low: float, close: float
) -> None:
    """The named prior followed by the final bar."""
    cat_ctx["bars"] = [_PRIORS[prior], OHLC(open, high, low, close)]


@given(
    parsers.parse(
        "the closed bars: {count:d} context candles, the {prior} prior, then "
        "({open:g}, {high:g}, {low:g}, {close:g})"
    )
)
def context_prior_then(
    cat_ctx: dict[str, Any],
    count: int,
    prior: str,
    open: float,
    high: float,
    low: float,
    close: float,
) -> None:
    """Integer context candles, the named prior, then the final bar."""
    cat_ctx["bars"] = [_CONTEXT] * count + [_PRIORS[prior], OHLC(open, high, low, close)]


@given(
    parsers.parse(
        "the closed bars: {before:d} float context candles, ({o1:g}, {h1:g}, {l1:g}, {c1:g}), "
        "{between:d} float context candles, then ({o2:g}, {h2:g}, {l2:g}, {c2:g})"
    )
)
def float_context_shape(
    cat_ctx: dict[str, Any],
    before: int,
    o1: float,
    h1: float,
    l1: float,
    c1: float,
    between: int,
    o2: float,
    h2: float,
    l2: float,
    c2: float,
) -> None:
    """Float context candles around a dip, then the final bar."""
    cat_ctx["bars"] = (
        [_FLOAT_CONTEXT] * before
        + [OHLC(o1, h1, l1, c1)]
        + [_FLOAT_CONTEXT] * between
        + [OHLC(o2, h2, l2, c2)]
    )


@given(parsers.parse("four flat-bodied prior bars closing at {c1:g}, {c2:g}, {c3:g}, {c4:g}"))
def flat_bodied_priors(cat_ctx: dict[str, Any], c1: float, c2: float, c3: float, c4: float) -> None:
    """Four bars (c, c + 10, c - 10, c) fixing net(3) = c4 - c1."""
    cat_ctx["bars"] = [OHLC(c, c + 10, c - 10, c) for c in (c1, c2, c3, c4)]


@given(parsers.parse("a final closed bar ({open:g}, {high:g}, {low:g}, {close:g})"))
def final_bar(cat_ctx: dict[str, Any], open: float, high: float, low: float, close: float) -> None:
    """Append the bar under test."""
    cat_ctx["bars"].append(OHLC(open, high, low, close))


@given(
    parsers.parse('the legacy recognition fixture for "{pattern}" with {count:d} context candles')
)
def legacy_fixture(cat_ctx: dict[str, Any], pattern: str, count: int) -> None:
    """Float context candles followed by the legacy recognition shape."""
    cat_ctx["bars"] = [_FLOAT_CONTEXT] * count + _FIXTURES[pattern]
    cat_ctx["pattern"] = pattern


@given(parsers.parse('the legacy boundary fixture "{case}"'))
def legacy_boundary(cat_ctx: dict[str, Any], case: str) -> None:
    """One equal engulfing edge (TA-Lib 80) or a star closing 40 percent into the body."""
    if case.endswith("one equal body edge"):
        pattern = f"{case.split()[0]}_engulfing"
        pair = list(_FIXTURES[pattern])
        pair[-1] = replace(pair[-1], open=pair[0].close)
        shape = pair
    else:
        pattern = f"{case.split()[0]}_star"
        shape = list(_FIXTURES[pattern])
        shape[-1] = replace(shape[-1], close=8.8 if pattern == "morning_star" else 11.2)
    cat_ctx["bars"] = [_FLOAT_CONTEXT] * 20 + shape
    cat_ctx["pattern"] = pattern


@given(parsers.parse("{count:d} context candles"))
def context_only(cat_ctx: dict[str, Any], count: int) -> None:
    """Only integer context candles."""
    cat_ctx["bars"] = [_CONTEXT] * count


@given(parsers.parse("{count:d} flat closed bars ({open:g}, {high:g}, {low:g}, {close:g})"))
def flat_bars(
    cat_ctx: dict[str, Any], count: int, open: float, high: float, low: float, close: float
) -> None:
    """Repeated flat bars."""
    cat_ctx["bars"] = [OHLC(open, high, low, close)] * count


@given(parsers.re(r'READY hits "(?P<hits>[^"]*)"'))
def ready_hits(cat_ctx: dict[str, Any], hits: str) -> None:
    """Hits from ``id`` or ``id:WARMUP`` items, READY with the catalog polarity by default."""
    staged = []
    for item in _ids(hits):
        rule, _, status = item.partition(":")
        status = status or READY
        polarity = CATALOG[rule].polarity if status == READY else 0
        staged.append(PatternHit(rule, polarity, "1", status))
    cat_ctx["hits"] = tuple(staged)


@given(
    "the legacy corpora: every legacy recognition fixture with 20 context candles, the "
    "overlapping hammer and engulfing fixtures, and the varied 500-candle history of "
    "test_candlestick_detector.py"
)
def legacy_corpora(cat_ctx: dict[str, Any]) -> None:
    """The recognition, overlap and varied corpora of the legacy detector's feature."""
    corpora = [[_FLOAT_CONTEXT] * 20 + shape for shape in _FIXTURES.values()]
    bearish = [OHLC(9.7, 9.85, 9.5, 9.8), OHLC(9.85, 9.87, 8.5, 9.65)]
    bullish = [replace(bar, open=bar.close, close=bar.open) for bar in bearish]
    corpora += [[_FLOAT_CONTEXT] * 20 + bearish, [_FLOAT_CONTEXT] * 20 + bullish]
    varied: list[OHLC] = []
    for scale in (0.125, 1.0, 8.0):
        for shape in _FIXTURES.values():
            varied.extend(
                OHLC(*(price * scale for price in bar.values()))
                for bar in [_FLOAT_CONTEXT] * 30 + shape
            )
    rng = np.random.default_rng(20260927)
    for _ in range(150):
        open_, close = rng.uniform(5, 15, 2)
        varied.append(OHLC(open_, max(open_, close) + 0.7, min(open_, close) - 0.3, close))
    assert len(varied) >= 500
    cat_ctx["corpora"] = corpora + [varied]


# --- actions --------------------------------------------------------------------------


@when("the catalog evaluates the final bar")
def evaluate(cat_ctx: dict[str, Any]) -> None:
    """Stream every staged bar; keep the per-bar evidence and the final one."""
    cat_ctx["evidences"] = _stream(cat_ctx["config"], cat_ctx["bars"])
    cat_ctx["evidence"] = cat_ctx["evidences"][-1]


@when("the same prefix is streamed before a morning-star suffix and before an evening-star suffix")
def diverging_suffixes(cat_ctx: dict[str, Any]) -> None:
    """Replay the identical prefix ahead of two opposite futures."""
    prefix = cat_ctx["bars"]
    cat_ctx["prefix_runs"] = [
        _stream(cat_ctx["config"], prefix + [_FLOAT_CONTEXT] * 20 + _FIXTURES[pattern])[
            : len(prefix)
        ]
        for pattern in ("morning_star", "evening_star")
    ]


@when("the legacy label is derived")
def derive_label(cat_ctx: dict[str, Any]) -> None:
    """Apply the legacy selector to the staged hits."""
    cat_ctx["label"] = legacy_label(cat_ctx["hits"])


@when(
    "every prefix of every corpus is evaluated by the catalog and by "
    "perception.candlestick.detect_pattern"
)
def evaluate_corpora(cat_ctx: dict[str, Any]) -> None:
    """Stream each corpus through a fresh catalog and batch-evaluate every prefix."""
    cat_ctx["labels"], cat_ctx["oracle"], cat_ctx["retained"] = [], [], []
    for corpus in cat_ctx["corpora"]:
        catalog = CandleCatalog(cat_ctx["config"], "EURUSD")
        labels, oracle = [], []
        for end, bar in enumerate(_closed(corpus), 1):
            labels.append(legacy_label(catalog.update(bar).hits))
            oracle.append(detect_pattern(corpus[:end]))
            cat_ctx["retained"].append(catalog.history.history_count)
        cat_ctx["labels"].append(labels)
        cat_ctx["oracle"].append(oracle)


# --- assertions -----------------------------------------------------------------------


@then(parsers.re(r'the READY hits are "(?P<hits>[^"]*)" with polarity 0 each'))
def assert_neutral_hits(cat_ctx: dict[str, Any], hits: str) -> None:
    """Exactly the listed READY hits, all neutral."""
    assert _ready_ids(cat_ctx["evidence"]) == _ids(hits)
    assert all(hit.polarity == 0 for hit in cat_ctx["evidence"].ready_hits)


@then(parsers.re(r'the READY hits are "(?P<hits>[^"]*)"$'))
def assert_ready_hits(cat_ctx: dict[str, Any], hits: str) -> None:
    """Exactly the listed READY hits, in order, each with its registered polarity."""
    assert _ready_ids(cat_ctx["evidence"]) == _ids(hits)
    assert all(hit.polarity == CATALOG[hit.id].polarity for hit in cat_ctx["evidence"].ready_hits)


@then(parsers.parse('the evidence status is "{status}"'))
def assert_status(cat_ctx: dict[str, Any], status: str) -> None:
    """The overall readiness."""
    assert cat_ctx["evidence"].status == status


@then(parsers.parse("real TA-Lib gives the engulfing score {score:d} on those bars"))
def assert_engulfing_score(cat_ctx: dict[str, Any], score: int) -> None:
    """Native engulfing magnitude on the staged bars."""
    raw = _raw_signals(cat_ctx["bars"])
    assert raw["bullish_engulfing"] + raw["bearish_engulfing"] == score


@then(parsers.parse('the READY hits include "{pattern}" with polarity {polarity:d}'))
def assert_includes_polarity(cat_ctx: dict[str, Any], pattern: str, polarity: int) -> None:
    """The named READY hit is present with the given polarity."""
    hits = {hit.id: hit.polarity for hit in cat_ctx["evidence"].ready_hits}
    assert hits.get(pattern) == polarity


@then(parsers.parse('the READY hits include "{pattern}"'))
def assert_includes(cat_ctx: dict[str, Any], pattern: str) -> None:
    """The named READY hit is present."""
    assert pattern in _ready_ids(cat_ctx["evidence"])


@then(parsers.parse('the real TA-Lib output confirms "{pattern}"'))
def assert_native(cat_ctx: dict[str, Any], pattern: str) -> None:
    """Native TA-Lib fires the legacy pattern with the expected sign."""
    assert _raw_signals(cat_ctx["bars"])[pattern] == (100 if pattern in _BULLISH else -100)


@then(parsers.parse('the hit for "{pattern}" has status "{status}"'))
def assert_hit_status(cat_ctx: dict[str, Any], pattern: str, status: str) -> None:
    """The named rule's readiness on the final bar."""
    statuses = {hit.id: hit.status for hit in cat_ctx["evidence"].hits}
    assert statuses.get(pattern) == status


@then(parsers.parse('real TA-Lib gives the score {score:d} for "{pattern}"'))
def assert_native_score(cat_ctx: dict[str, Any], score: int, pattern: str) -> None:
    """Native TA-Lib's exact score on the boundary fixture."""
    assert _raw_signals(cat_ctx["bars"])[pattern] == score


@then("the hits are exactly, in order:")
def assert_hits_table(cat_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    """The complete hit tuple, WARMUP entries included, in id order."""
    expected = [(row[0], int(row[1]), row[2]) for row in datatable[1:]]
    assert [(hit.id, hit.polarity, hit.status) for hit in cat_ctx["evidence"].hits] == expected


@then(parsers.re(r'the WARMUP hit ids are exactly "(?P<ids>[^"]*)"'))
def assert_warmup_ids(cat_ctx: dict[str, Any], ids: str) -> None:
    """Exactly the listed rules are still warming."""
    warming = [hit.id for hit in cat_ctx["evidence"].hits if hit.status == WARMUP]
    assert warming == _ids(ids)


@then("real TA-Lib reports hammer 100 on those bars")
def assert_native_hammer(cat_ctx: dict[str, Any]) -> None:
    """Native TA-Lib confirms the hammer on the opposing-hits bars."""
    assert _raw_signals(cat_ctx["bars"])["hammer"] == 100


@then(parsers.parse('the legacy label of those hits is "{label}"'))
def assert_legacy_label(cat_ctx: dict[str, Any], label: str) -> None:
    """The legacy selector over the evidence hits."""
    assert legacy_label(cat_ctx["evidence"].hits) == label


@then("the legacy label of those hits is None")
def assert_legacy_label_none(cat_ctx: dict[str, Any]) -> None:
    """No legacy label."""
    assert legacy_label(cat_ctx["evidence"].hits) is None


@then(parsers.re(r'the READY hit ids are exactly "(?P<ids>[^"]*)"'))
def assert_ready_ids(cat_ctx: dict[str, Any], ids: str) -> None:
    """The READY ids in order."""
    assert _ready_ids(cat_ctx["evidence"]) == _ids(ids)


@then(
    parsers.parse(
        'the same bars through the catalog restricted to "{rules}" give identical evidence'
    )
)
def assert_order_independent(cat_ctx: dict[str, Any], rules: str) -> None:
    """A differently ordered enabled_rules yields equal evidence."""
    other = CandleConfig(enabled_rules=tuple(_ids(rules)))
    assert _stream(other, cat_ctx["bars"]) == cat_ctx["evidences"]


@then("the per-bar evidence over the prefix is identical under both suffixes")
def assert_prefix_invariance(cat_ctx: dict[str, Any]) -> None:
    """Future bars do not change already observed evidence."""
    first, second = cat_ctx["prefix_runs"]
    assert first == second
    assert len(first) == len(cat_ctx["bars"])


@then(parsers.parse('the final prefix hits include "{pattern}"'))
def assert_prefix_final(cat_ctx: dict[str, Any], pattern: str) -> None:
    """The prefix ends with the expected recognition."""
    assert pattern in _ready_ids(cat_ctx["prefix_runs"][0][-1])


@then(parsers.parse('the legacy label is "{label}"'))
def assert_label(cat_ctx: dict[str, Any], label: str) -> None:
    """The derived legacy label (``none`` means None)."""
    assert cat_ctx["label"] == (None if label == "none" else label)


@then("the legacy label of the catalog hits equals detect_pattern on every prefix")
def assert_corpora_equal(cat_ctx: dict[str, Any]) -> None:
    """Frozen legacy equality over every prefix of every corpus."""
    assert cat_ctx["labels"] == cat_ctx["oracle"]


@then("the legacy labels over the 500-candle history emit all six legacy names")
def assert_corpora_vocabulary(cat_ctx: dict[str, Any]) -> None:
    """The varied corpus exercises every legacy label."""
    assert set(cat_ctx["labels"][-1]) == _LEGACY_SIX | {None}


@then("the catalog history never retains more than max_history bars")
def assert_bounded(cat_ctx: dict[str, Any]) -> None:
    """History stays within the configured bound throughout the replay."""
    assert max(cat_ctx["retained"]) <= cat_ctx["config"].max_history
    assert max(cat_ctx["retained"]) == cat_ctx["config"].max_history
