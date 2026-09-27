"""Steps for training_data.feature — the shared F7 training-data assembly."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from algo_backtest.chain.filters.f7_meta_learner import (
    FeatureFamily,
    TrainingRow,
    WalkForwardSplit,
    train_meta_learner,
    walk_forward_split,
)
from algo_backtest.chain.filters.f7_model_io import load_model, load_provenance
from algo_backtest.chain.price_features import PriceFeatureConfig
from algo_backtest.training import (
    atr_series,
    build_training_rows,
    lean_bar_stream,
    load_m1_bars,
    mid,
    save_model,
    swing_levels,
)
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/training_data.feature")

_EURUSD = build_instrument("EURUSD")
# The F1/F2/F3 features contract, written out literally (not derived from
# `price_features`, the function under test) so a renamed/dropped/extra key fails.
_LIVE_PRICE_KEYS = {
    "trend_direction",
    "trend_strength",
    "higher_tf_trend_direction",
    "rsi",
    "macd_hist",
    "candlestick_pattern",
    "atr_pips",
    "swing_low_pips",
    "swing_high_pips",
}


@dataclass
class _TrainCtx:
    """Per-scenario fixture context."""

    root: Path
    bars: list[QuoteBar] = field(default_factory=list)
    intensity: dict[datetime, float] = field(default_factory=dict)
    rows: list[TrainingRow] = field(default_factory=list)
    error: ValueError | None = None
    model_path: Path | None = None
    manifest: dict[str, object] = field(default_factory=dict)
    splits: list[WalkForwardSplit] = field(default_factory=list)
    atr: list[float] = field(default_factory=list)
    swings: list[tuple[float, float]] = field(default_factory=list)
    filled_at: datetime | None = None


@pytest.fixture
def train_ctx(tmp_path: Path) -> _TrainCtx:
    """A fresh per-scenario context over an empty tmp data root."""
    return _TrainCtx(root=tmp_path)


def _bar(ts: datetime, i: int) -> QuoteBar:
    """A deterministic zig-zag quote bar (both label classes appear)."""
    mid = 1.1000 + 0.0002 * ((i * 7) % 11)
    return QuoteBar(
        timestamp=ts, bid_open=mid, bid_high=mid, bid_low=mid, bid_close=mid,
        ask_open=mid + 1e-4, ask_high=mid + 1e-4, ask_low=mid + 1e-4, ask_close=mid + 1e-4,
        tick_count=1,
    )


@given(parsers.parse('EUR/USD m1 bars from "{first}" to "{last}"'))
def _bars(train_ctx: _TrainCtx, first: str, last: str) -> None:
    start, stop = datetime.fromisoformat(first), datetime.fromisoformat(last)
    minutes = int((stop - start).total_seconds() // 60) + 1
    bars = [_bar(start + timedelta(minutes=i), i) for i in range(minutes)]
    train_ctx.bars = bars
    by_month: dict[tuple[int, int], list[QuoteBar]] = {}
    for bar in bars:
        by_month.setdefault((bar.timestamp.year, bar.timestamp.month), []).append(bar)
    for (year, month), rows in by_month.items():
        ParquetRepository(QuoteBar, price_path_for(train_ctx.root, _EURUSD, "m1", year, month)).put(
            rows
        )


@given(
    parsers.parse(
        'event intensity {before:g} through "{last_before}" and {after:g} from "{first_after}"'
    )
)
def _intensity_step(
    train_ctx: _TrainCtx, before: float, last_before: str, after: float, first_after: str
) -> None:
    cutoff = datetime.fromisoformat(first_after)
    first = train_ctx.bars[0].timestamp
    for i in range(len(train_ctx.bars) + 1):
        minute = first + timedelta(minutes=i)
        train_ctx.intensity[minute] = before if minute < cutoff else after
    assert datetime.fromisoformat(last_before) + timedelta(minutes=1) == cutoff


@given(parsers.parse('event intensity {value:g} through "{last}" only'))
def _intensity_partial(train_ctx: _TrainCtx, value: float, last: str) -> None:
    minute, stop = train_ctx.bars[0].timestamp, datetime.fromisoformat(last)
    while minute <= stop:
        train_ctx.intensity[minute] = value
        minute += timedelta(minutes=1)


@when(parsers.parse("bars are loaded for the window {start} to {end}"))
def _load(train_ctx: _TrainCtx, start: str, end: str) -> None:
    train_ctx.bars = load_m1_bars(
        train_ctx.root, _EURUSD, date.fromisoformat(start), date.fromisoformat(end)
    )


@when(parsers.parse("loading bars for the window {start} to {end} fails"))
def _load_fails(train_ctx: _TrainCtx, start: str, end: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        load_m1_bars(train_ctx.root, _EURUSD, date.fromisoformat(start), date.fromisoformat(end))
    train_ctx.error = excinfo.value


@when(parsers.parse("price-only training rows are built for the window {start} to {end}"))
def _price_rows(train_ctx: _TrainCtx, start: str, end: str) -> None:
    bars = load_m1_bars(train_ctx.root, _EURUSD, date.fromisoformat(start), date.fromisoformat(end))
    train_ctx.rows = build_training_rows(bars, instrument=_EURUSD)


@when("news training rows are built")
def _news_rows(train_ctx: _TrainCtx) -> None:
    train_ctx.rows = build_training_rows(train_ctx.bars, train_ctx.intensity, instrument=_EURUSD)


@when("building news training rows fails")
def _news_rows_fail(train_ctx: _TrainCtx) -> None:
    with pytest.raises(ValueError) as excinfo:
        build_training_rows(train_ctx.bars, train_ctx.intensity, instrument=_EURUSD)
    train_ctx.error = excinfo.value


@when(parsers.parse('a model is saved with provenance strategy "{strategy}"'))
def _save(train_ctx: _TrainCtx, strategy: str) -> None:
    train_ctx.model_path = train_ctx.root / "out" / "f7_meta_learner.json"
    partition = price_path_for(train_ctx.root, _EURUSD, "m1", 2015, 2)
    rows = [
        TrainingRow(
            timestamp=datetime(2024, 1, 1 + day, tzinfo=UTC),
            features={"rsi": float(day * 10 + label), "macd_hist": 0.0},
            label=label,
        )
        for day in range(3)
        for label in (0, 1)
        for _ in range(20)
    ]
    split = walk_forward_split(
        rows, train_end=date(2024, 1, 1), validation_end=date(2024, 1, 2),
        test_end=date(2024, 1, 3),
    )
    model = train_meta_learner(families=(FeatureFamily.INDICATOR,), split=split)
    save_model(
        model, train_ctx.model_path, {"strategy": strategy},
        data_root=train_ctx.root, inputs=[partition],
    )
    train_ctx.manifest = load_provenance(train_ctx.model_path)


@then(parsers.parse('the first loaded bar is at "{ts}"'))
def _first_bar(train_ctx: _TrainCtx, ts: str) -> None:
    assert train_ctx.bars[0].timestamp == datetime.fromisoformat(ts)


@then(parsers.parse('the last loaded bar is at "{ts}"'))
def _last_bar(train_ctx: _TrainCtx, ts: str) -> None:
    assert train_ctx.bars[-1].timestamp == datetime.fromisoformat(ts)


@then(parsers.parse('the training failure names "{fragment}"'))
def _failure(train_ctx: _TrainCtx, fragment: str) -> None:
    assert train_ctx.error is not None and fragment in str(train_ctx.error), train_ctx.error


@then("every row's features have exactly the live price-feature keys")
def _price_keys(train_ctx: _TrainCtx) -> None:
    assert train_ctx.rows
    assert all(set(row.features) == _LIVE_PRICE_KEYS for row in train_ctx.rows)


@then(parsers.parse('the first row is for the bar starting "{ts}"'))
def _first_row(train_ctx: _TrainCtx, ts: str) -> None:
    assert train_ctx.rows[0].timestamp == datetime.fromisoformat(ts)


@then(parsers.parse("there are {count:d} rows"))
def _row_count(train_ctx: _TrainCtx, count: int) -> None:
    assert len(train_ctx.rows) == count


@then(parsers.parse('the row for the bar starting "{ts}" has news_event_intensity {value:g}'))
def _row_intensity(train_ctx: _TrainCtx, ts: str, value: float) -> None:
    row = next(r for r in train_ctx.rows if r.timestamp == datetime.fromisoformat(ts))
    assert row.features["news_event_intensity"] == value


@then("every row's news_sentiment_score is missing")
def _sentiment_missing(train_ctx: _TrainCtx) -> None:
    assert all(row.features["news_sentiment_score"] is None for row in train_ctx.rows)


@then("the saved model reloads")
def _reloads(train_ctx: _TrainCtx) -> None:
    assert train_ctx.model_path is not None
    assert load_model(train_ctx.model_path).families == (FeatureFamily.INDICATOR,)


@then("the provenance lists the 2015-02 price partition relative to the data root with its hash")
def _inputs(train_ctx: _TrainCtx) -> None:
    partition = price_path_for(train_ctx.root, _EURUSD, "m1", 2015, 2)
    relative = partition.relative_to(train_ctx.root).as_posix()
    inputs = train_ctx.manifest["inputs"]
    assert isinstance(inputs, dict)
    assert inputs == {relative: hashlib.sha256(partition.read_bytes()).hexdigest()}


@then(parsers.parse('the provenance\'s strategy is "{strategy}"'))
def _strategy(train_ctx: _TrainCtx, strategy: str) -> None:
    assert train_ctx.manifest["strategy"] == strategy
    assert train_ctx.manifest["horizon_minutes"] == 15
    packages = train_ctx.manifest["packages"]
    assert isinstance(packages, dict) and {"lightgbm", "scikit-learn"} <= set(packages)


_SHAPE_STEP = {"rising": 0.0001, "falling": -0.0001, "flat": 0.0}


def _quote(ts: datetime, mid: float) -> QuoteBar:
    """One quote bar at `mid` (1-pip spread)."""
    return QuoteBar(
        timestamp=ts, bid_open=mid, bid_high=mid, bid_low=mid, bid_close=mid,
        ask_open=mid + 1e-4, ask_high=mid + 1e-4, ask_low=mid + 1e-4, ask_close=mid + 1e-4,
        tick_count=1,
    )


@given(
    parsers.parse(
        '{count:d} EUR/USD m1 bars from "{first}" on a {shape} price path'
    )
)
def _shaped_bars(train_ctx: _TrainCtx, count: int, first: str, shape: str) -> None:
    start = datetime.fromisoformat(first)
    step = _SHAPE_STEP[shape]
    train_ctx.bars = [
        _quote(start + timedelta(minutes=i), 1.1000 + step * i) for i in range(count)
    ]


@when("training rows are built from those bars")
def _rows_from_bars(train_ctx: _TrainCtx) -> None:
    train_ctx.rows = build_training_rows(train_ctx.bars, instrument=_EURUSD)


@then(parsers.parse("every row's label is {label:d}"))
def _every_label(train_ctx: _TrainCtx, label: int) -> None:
    assert train_ctx.rows, "no rows built"
    assert {row.label for row in train_ctx.rows} == {label}


@then("every row's label time is the close of the bar 15 minutes after it")
def _label_times(train_ctx: _TrainCtx) -> None:
    for row in train_ctx.rows:
        assert row.label_time == row.timestamp + timedelta(minutes=16)


def _split(bars: list[QuoteBar]) -> WalkForwardSplit:
    """The fixed three-day walk-forward split these scenarios use."""
    return walk_forward_split(
        build_training_rows(bars, instrument=_EURUSD),
        train_end=date(2015, 2, 23),
        validation_end=date(2015, 2, 24),
        test_end=date(2015, 2, 25),
    )


@when(
    "the rows are split with train through 2015-02-23, validation 2015-02-24, test 2015-02-25"
)
def _split_rows(train_ctx: _TrainCtx) -> None:
    train_ctx.splits.append(_split(train_ctx.bars))


@when(
    "the same window is rebuilt with every 2015-02-25 price shifted up 50 pips and split again"
)
def _split_shifted(train_ctx: _TrainCtx) -> None:
    shifted = [
        _quote(bar.timestamp, mid(bar) - 5e-5 + 0.0050)
        if bar.timestamp.date() == date(2015, 2, 25)
        else bar
        for bar in train_ctx.bars
    ]
    train_ctx.splits.append(_split(shifted))


@then("the train and validation rows, features and labels, are identical in both runs")
def _fitting_spans_identical(train_ctx: _TrainCtx) -> None:
    original, shifted = train_ctx.splits
    assert original.test != shifted.test  # the held-out change is real
    assert original.train == shifted.train
    assert original.validation == shifted.validation


@then(parsers.parse("every train row's label time is no later than {limit}"))
def _train_label_times(train_ctx: _TrainCtx, limit: str) -> None:
    (split,) = train_ctx.splits
    assert all(
        r.label_time is not None and r.label_time <= datetime.fromisoformat(limit)
        for r in split.train
    )


@then(parsers.parse("every validation row's label time is no later than {limit}"))
def _validation_label_times(train_ctx: _TrainCtx, limit: str) -> None:
    (split,) = train_ctx.splits
    assert all(
        r.label_time is not None and r.label_time <= datetime.fromisoformat(limit)
        for r in split.validation
    )


def _ranged_quote(ts: datetime, close: float) -> QuoteBar:
    """A quote bar closing at `close` with a 2-pip range around it (1-pip spread)."""
    return QuoteBar(
        timestamp=ts, bid_open=close, bid_high=close + 1e-4, bid_low=close - 1e-4, bid_close=close,
        ask_open=close + 1e-4, ask_high=close + 2e-4, ask_low=close, ask_close=close + 1e-4,
        tick_count=1,
    )


@given(parsers.parse('EUR/USD m1 bars from "{first}" to "{last}" without "{gap}"'))
def _bars_with_gap(train_ctx: _TrainCtx, first: str, last: str, gap: str) -> None:
    start, stop = datetime.fromisoformat(first), datetime.fromisoformat(last)
    minutes = int((stop - start).total_seconds() // 60) + 1
    train_ctx.bars = [
        _ranged_quote(start + timedelta(minutes=i), 1.1000 + 0.0001 * i)
        for i in range(minutes)
        if start + timedelta(minutes=i) != datetime.fromisoformat(gap)
    ]


@when("the LEAN bar stream is built from those bars")
def _stream(train_ctx: _TrainCtx) -> None:
    train_ctx.bars = lean_bar_stream(train_ctx.bars)


@then(parsers.parse('no streamed bar starts between "{first}" and "{last}"'))
def _break_dropped(train_ctx: _TrainCtx, first: str, last: str) -> None:
    lo, hi = datetime.fromisoformat(first), datetime.fromisoformat(last)
    assert train_ctx.bars
    assert not [bar for bar in train_ctx.bars if lo <= bar.timestamp <= hi]
    assert any(bar.timestamp == hi + timedelta(minutes=1) for bar in train_ctx.bars)


@then(parsers.parse('the bar starting "{ts}" is filled forward from the one before it'))
def _filled(train_ctx: _TrainCtx, ts: str) -> None:
    at = datetime.fromisoformat(ts)
    stream = {bar.timestamp: bar for bar in train_ctx.bars}
    previous, filled = stream[at - timedelta(minutes=1)], stream[at]
    assert (filled.bid_close, filled.ask_close) == (previous.bid_close, previous.ask_close)
    assert filled.tick_count == 0
    train_ctx.filled_at = at


@then(
    "that filled-forward bar carries the previous bar's high and low, not a flat bar at its "
    "close"
)
def _filled_keeps_range(train_ctx: _TrainCtx) -> None:
    at = train_ctx.filled_at
    assert at is not None
    stream = {bar.timestamp: bar for bar in train_ctx.bars}
    previous, filled = stream[at - timedelta(minutes=1)], stream[at]
    assert previous.bid_high != previous.bid_close, "the fixture must have a real range"
    assert (filled.bid_high, filled.bid_low, filled.ask_high, filled.ask_low) == (
        previous.bid_high, previous.bid_low, previous.ask_high, previous.ask_low
    )
    assert (filled.bid_open, filled.ask_open) == (previous.bid_open, previous.ask_open)


_MINIMAL_PERIODS = {
    "ema_fast": 1, "ema_slow": 2, "ema_higher_tf": 3, "rsi_period": 1,
    "macd_fast": 1, "macd_slow": 2, "macd_signal": 1,
}


@given("the mid-price bars", target_fixture="train_ctx")
def _mid_bars(train_ctx: _TrainCtx, datatable: list[list[str]]) -> _TrainCtx:
    """Minute bars from a high/low/close table; bid = ask so each mid is the table value."""
    headers, *rows = datatable
    start = datetime(2015, 2, 27, tzinfo=UTC)
    train_ctx.bars = []
    for i, cells in enumerate(rows):
        bar = dict(zip(headers, (float(cell) for cell in cells), strict=True))
        train_ctx.bars.append(
            QuoteBar(
                timestamp=start + timedelta(minutes=i),
                bid_open=bar["close"], bid_high=bar["high"], bid_low=bar["low"],
                bid_close=bar["close"],
                ask_open=bar["close"], ask_high=bar["high"], ask_low=bar["low"],
                ask_close=bar["close"],
                tick_count=1,
            )
        )
    return train_ctx


@when(parsers.parse("the ATR series is computed with period {period:d}"))
def _atr(train_ctx: _TrainCtx, period: int) -> None:
    train_ctx.atr = atr_series(train_ctx.bars, period)


@when(parsers.parse("the swing levels are computed with a look-back of {lookback:d} bars"))
def _swings(train_ctx: _TrainCtx, lookback: int) -> None:
    train_ctx.swings = swing_levels(train_ctx.bars, lookback)


@when(
    parsers.parse(
        'training rows are built for instrument "{symbol}" with every period minimal, '
        "atr_period {atr_period:d}, swing_lookback_bars {lookback:d} and a 1-bar horizon"
    )
)
def _atr_rows(train_ctx: _TrainCtx, symbol: str, atr_period: int, lookback: int) -> None:
    train_ctx.rows = build_training_rows(
        train_ctx.bars,
        instrument=build_instrument(symbol),
        price_features_config=PriceFeatureConfig(
            **_MINIMAL_PERIODS, atr_period=atr_period, swing_lookback_bars=lookback
        ),
        horizon_minutes=1,
    )


@then(
    parsers.parse(
        "the swing low at bar {bar:d} is {low:g} and the swing high is {high:g}"
    )
)
def _swing_at(train_ctx: _TrainCtx, bar: int, low: float, high: float) -> None:
    assert train_ctx.swings[bar - 1] == (low, high), train_ctx.swings


@then(
    parsers.parse(
        "the row for bar {bar:d} has swing_low_pips {low:g} and swing_high_pips {high:g} "
        "to {digits:d} decimal places"
    )
)
def _row_swings(train_ctx: _TrainCtx, bar: int, low: float, high: float, digits: int) -> None:
    row = next(r for r in train_ctx.rows if r.timestamp == train_ctx.bars[bar - 1].timestamp)
    got = [row.features["swing_low_pips"], row.features["swing_high_pips"]]
    assert all(isinstance(value, float) for value in got), row.features
    rounded = [round(float(value), digits) for value in got if isinstance(value, float)]
    assert rounded == [round(low, digits), round(high, digits)], row.features


@then(parsers.parse("the ATR at bar {bar:d} is {atr:g} to {digits:d} decimal places"))
def _atr_at(train_ctx: _TrainCtx, bar: int, atr: float, digits: int) -> None:
    assert round(train_ctx.atr[bar - 1], digits) == round(atr, digits), train_ctx.atr


@then(
    parsers.parse(
        "the row for bar {bar:d} has atr_pips {atr_pips:g} to {digits:d} decimal places"
    )
)
def _row_atr_pips(train_ctx: _TrainCtx, bar: int, atr_pips: float, digits: int) -> None:
    row = next(r for r in train_ctx.rows if r.timestamp == train_ctx.bars[bar - 1].timestamp)
    value = row.features["atr_pips"]
    assert isinstance(value, float)
    assert round(value, digits) == round(atr_pips, digits), row.features


@then(parsers.parse("the first row is for bar {bar:d}"))
def _first_row_bar(train_ctx: _TrainCtx, bar: int) -> None:
    assert train_ctx.rows[0].timestamp == train_ctx.bars[bar - 1].timestamp
