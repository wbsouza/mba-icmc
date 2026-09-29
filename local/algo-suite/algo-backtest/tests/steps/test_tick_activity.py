"""BDD for exact canonical Parquet tick lookup and causal activity gating."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta, timezone

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from algo_backtest.chain.filters.volume_strength import (
    VolumeConfig,
    VolumeStrengthFilter,
    parse_volume_config,
)
from algo_backtest.chain.model import ExecutionState, Recommendation
from algo_backtest.perception.tick_activity import TickActivityIndex, activity_provenance
from algo_backtest.perception.volume import RelativeTickActivity
from algo_core import layout
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/tick_activity.feature")

JANUARY = datetime(2020, 1, 1, tzinfo=UTC)
FEBRUARY = datetime(2020, 2, 1, tzinfo=UTC)


@pytest.fixture
def activity_context(tmp_path):
    """Create a fresh reader and canonical paths within a real temporary root."""
    instrument = build_instrument("EURUSD")
    return {
        "data_root": tmp_path,
        "instrument": instrument,
        "reader": TickActivityIndex(tmp_path, instrument),
        "january": layout.price_path_for(tmp_path, instrument, "m1", 2020, 1),
        "february": layout.price_path_for(tmp_path, instrument, "m1", 2020, 2),
        "originals": {},
    }


def write_bars(path, timestamp, counts):
    """Write production QuoteBars through the real canonical repository."""
    bars = [
        QuoteBar(
            timestamp=timestamp + timedelta(minutes=offset),
            bid_open=1.1,
            bid_high=1.2,
            bid_low=1.0,
            bid_close=1.1,
            ask_open=1.2,
            ask_high=1.3,
            ask_low=1.1,
            ask_close=1.2,
            tick_count=count,
        )
        for offset, count in enumerate(counts)
    ]
    ParquetRepository(QuoteBar, path).put(bars)


@given("canonical tick counts for EURUSD in January and February")
def canonical_prices(activity_context):
    """Use differing counts and a very active future minute to expose wrong joins."""
    for month, timestamp, counts in (
        ("january", JANUARY, [12, 0, 9000]),
        ("february", FEBRUARY, [23]),
    ):
        path = activity_context[month]
        write_bars(path, timestamp, counts)
        activity_context["originals"][path] = path.read_bytes()


@given("an empty canonical price root")
def empty_prices(activity_context):
    """Keep both month paths absent until the reader is exercised."""
    assert not activity_context["january"].exists()
    assert not activity_context["february"].exists()


@when("January minutes are read out of order")
def read_exact_minutes(activity_context):
    """Resolve exact keys, including a zero, without any nearest-time fallback."""
    activity_context["counts"] = [
        activity_context["reader"].count_at(JANUARY + timedelta(minutes=i), fill_forward=False)
        for i in (2, 0, 1)
    ]


@then("each minute has its own canonical count")
def exact_counts(activity_context):
    """The future minute cannot change earlier observations."""
    assert activity_context["counts"] == [9000, 12, 0]


@then("the canonical source files are unchanged")
def unchanged_sources(activity_context):
    """Compare complete Parquet bytes after successful and failed reads."""
    for path, original in activity_context["originals"].items():
        assert path.read_bytes() == original


@when("January is read with an unreadable February partition")
def lazy_month(activity_context):
    """A corrupt unrequested partition proves that the reader opens only January."""
    activity_context["february"].write_bytes(b"invalid parquet")
    assert activity_context["reader"].count_at(JANUARY, fill_forward=False) == 12


@then("January is available from the month cache after its file is removed")
def cached_month(activity_context):
    """Remove only the temporary fixture; further same-month reads need no disk access."""
    activity_context["january"].unlink()
    assert (
        activity_context["reader"].count_at(JANUARY + timedelta(minutes=2), fill_forward=False)
        == 9000
    )


@when("February is restored and read")
def next_month(activity_context):
    """Reading the next month must evict the previous dictionary."""
    path = activity_context["february"]
    path.write_bytes(activity_context["originals"][path])
    assert activity_context["reader"].count_at(FEBRUARY, fill_forward=False) == 23


@then("returning to the removed January partition fails with remediation")
def evicted_month(activity_context):
    """A missing January file exposes accidental caching of multiple months."""
    with pytest.raises(ValueError, match="download/transform"):
        activity_context["reader"].count_at(JANUARY, fill_forward=False)


@when("an absent real January minute is requested")
def missing_minute(activity_context):
    """Try a gap bounded by real earlier and later evidence."""
    path = activity_context["january"]
    bars = ParquetRepository(QuoteBar, path).read_all()
    bars.append(bars[-1].model_copy(update={"timestamp": JANUARY + timedelta(hours=2)}))
    ParquetRepository(QuoteBar, path).put(bars)
    with pytest.raises(ValueError) as error:
        activity_context["reader"].count_at(JANUARY + timedelta(hours=1), fill_forward=False)
    activity_context["error"] = str(error.value)


@when("a real January minute is requested")
def failed_real_minute(activity_context):
    """Capture malformed-source failures from the public API."""
    with pytest.raises(ValueError) as error:
        activity_context["reader"].count_at(JANUARY, fill_forward=False)
    activity_context["error"] = str(error.value)


@when("the stored real January minute is requested")
def stored_real_minute(activity_context):
    """Read a valid on-disk observation through the public interface."""
    activity_context["count"] = activity_context["reader"].count_at(JANUARY, fill_forward=False)


@when("loading the corrupt February partition fails")
def corrupt_next_month(activity_context):
    """A failed switch must leave the already validated January cache intact."""
    with pytest.raises(ValueError, match="download/transform"):
        activity_context["reader"].count_at(FEBRUARY, fill_forward=False)


@when("a January fill-forward minute is requested")
@when("a stored January minute is requested as fill-forward")
def fill_forward(activity_context):
    """Only an explicitly flagged synthetic bar returns zero without reading prices."""
    activity_context["count"] = activity_context["reader"].count_at(JANUARY, fill_forward=True)


@then(parsers.parse("the tick count is {count:d}"))
def tick_count(activity_context, count):
    """Check that the public result is an integer count."""
    assert type(activity_context["count"]) is int
    assert activity_context["count"] == count


@when(parsers.parse("a lookup uses timestamp {timestamp} and fill-forward {fill_forward}"))
def invalid_lookup_time(activity_context, timestamp, fill_forward):
    """Pass malformed times directly, including fill-forward input validation."""
    value = {"null": None, "text": "2020-01-01"}.get(timestamp)
    if timestamp not in {"null", "text"}:
        value = datetime.fromisoformat(timestamp)
    with pytest.raises(ValueError) as error:
        activity_context["reader"].count_at(value, fill_forward=json.loads(fill_forward))
    activity_context["error"] = str(error.value)


@when(parsers.parse("a lookup uses a fill-forward flag of {flag}"))
def invalid_fill_flag(activity_context, flag):
    """Truthy input cannot silently invent a zero count."""
    with pytest.raises(ValueError) as error:
        activity_context["reader"].count_at(JANUARY, fill_forward=json.loads(flag))
    activity_context["error"] = str(error.value)


def invalid_table(defect):
    """Represent corrupt values in real Arrow columns without Pydantic coercion."""
    counts = {
        "negative count": -1,
        "fractional count": 1.5,
        "boolean count": True,
        "string count": "12",
        "null count": None,
        "integral float count": 12.0,
    }
    timestamps = {
        "naive time": JANUARY.replace(tzinfo=None),
        "non-UTC time": JANUARY.replace(tzinfo=timezone(timedelta(hours=1))),
        "second time": JANUARY + timedelta(seconds=1),
        "microsecond time": JANUARY + timedelta(microseconds=1),
        "null time": None,
        "string time": JANUARY.isoformat(),
        "wrong month": FEBRUARY,
    }
    columns = {
        "timestamp": [timestamps.get(defect, JANUARY)],
        "tick_count": [counts.get(defect, 12)],
    }
    if defect == "duplicate minutes":
        columns = {"timestamp": [JANUARY, JANUARY], "tick_count": [12, 13]}
    if defect in {"nanosecond time", "valid nanosecond time"}:
        columns["timestamp"] = pa.array(
            [1577836800000000000 + (defect == "nanosecond time")],
            type=pa.timestamp("ns", tz="UTC"),
        )
    if defect == "absent tick column":
        del columns["tick_count"]
    if defect == "absent time column":
        del columns["timestamp"]
    table = pa.table(columns)
    return table.slice(0, 0) if defect == "empty rows" else table


@given(parsers.parse("a January canonical partition containing {defect}"))
def malformed_partition(activity_context, defect):
    """Persist invalid fixtures as actual Parquet, except deliberately corrupt bytes."""
    path = activity_context["january"]
    path.parent.mkdir(parents=True)
    if defect == "corrupt parquet":
        path.write_bytes(b"not a parquet file")
    else:
        pq.write_table(invalid_table(defect), path)
    activity_context["originals"][path] = path.read_bytes()


@then(parsers.parse('tick lookup fails mentioning "{reason}" and "{remediation}"'))
@then(parsers.parse('activity validation fails mentioning "{reason}" and "{remediation}"'))
def actionable_error(activity_context, reason, remediation):
    """Every failure explains the data problem and the remedy."""
    assert reason in activity_context["error"]
    assert remediation in activity_context["error"]


@when("the invalid partition is repaired and the same reader retries")
def repaired_partition(activity_context):
    """Retrying a failed load must re-read a fully validated month."""
    write_bars(activity_context["january"], JANUARY, [12])
    activity_context["count"] = activity_context["reader"].count_at(JANUARY, fill_forward=False)


@given(parsers.parse("a relative activity lookback of {lookback:d}"))
def relative_lookback(activity_context, lookback):
    """Initialize an empty causal history."""
    activity_context["activity"] = RelativeTickActivity(lookback)


@when(parsers.parse("the closed tick counts are {counts}"))
def closed_counts(activity_context, counts):
    """Collect per-bar evidence before any future count is processed."""
    activity_context["strengths"] = [
        activity_context["activity"].update(count) for count in json.loads(counts)
    ]


@then(parsers.parse("the activity sequence is {expected}"))
def activity_sequence(activity_context, expected):
    """Check warm-up, zero baselines, zero observations and rolling eviction."""
    for actual, wanted in zip(activity_context["strengths"], json.loads(expected), strict=True):
        if wanted is None:
            assert actual is None
        else:
            assert actual == pytest.approx(wanted)


@when(parsers.parse("relative activity is configured with lookback {lookback}"))
def invalid_lookback(activity_context, lookback):
    """Reject unusable history sizes without coercion."""
    with pytest.raises(ValueError) as error:
        RelativeTickActivity(json.loads(lookback))
    activity_context["error"] = str(error.value)


@when(parsers.parse("count {count} is rejected between valid counts"))
def rejected_count(activity_context, count):
    """A failed update must leave valid baseline history untouched."""
    indicator = activity_context["activity"]
    assert indicator.update(10) is None
    with pytest.raises(ValueError) as error:
        indicator.update(json.loads(count))
    activity_context["error"] = str(error.value)
    assert indicator.update(20) is None


@then("the following valid count still uses only the valid history")
def valid_history(activity_context):
    """The baseline remains the arithmetic mean of 10 and 20."""
    assert activity_context["activity"].update(30) == 2


def apply_gate(value, threshold=1):
    """Evaluate actual feature evidence with the production filter."""
    features = {} if value == "missing" else {"relative_tick_activity": value}
    return VolumeStrengthFilter(VolumeConfig(min_relative_activity=threshold)).apply(
        ExecutionState(JANUARY, "EURUSD", features)
    )


@then(parsers.parse("the volume veto sequence at threshold 1 is {expected}"))
def warmup_gate(activity_context, expected):
    """Gate the exact warm-up boundary and the following zero-count bar."""
    results = [apply_gate(value) for value in activity_context["strengths"]]
    assert [result.veto for result in results] == json.loads(expected)
    assert all(result.recommendation == Recommendation.ABSTAIN for result in results)


@when(parsers.parse("the volume gate sees {activity} at threshold {threshold}"))
def gate_evidence(activity_context, activity, threshold):
    """Distinguish an absent key from explicit unavailable evidence."""
    value = "missing" if activity == "missing" else json.loads(activity)
    activity_context["threshold"] = float(threshold)
    activity_context["evidence"] = None if value == "missing" else value
    activity_context["result"] = apply_gate(value, float(threshold))


@then(parsers.parse("the volume gate abstains with veto {veto} and quote-count metadata"))
def gate_metadata(activity_context, veto):
    """Both warm and unavailable outcomes retain the quote-activity audit basis."""
    result = activity_context["result"]
    assert result.recommendation == Recommendation.ABSTAIN
    assert result.veto is json.loads(veto)
    assert result.metadata["basis"] == "quote_tick_count"
    assert result.metadata["threshold"] == activity_context["threshold"]
    assert result.metadata["relative_activity"] == activity_context["evidence"]


@when(parsers.parse("the volume gate rejects activity {activity}"))
def invalid_gate_evidence(activity_context, activity):
    """Malformed numeric evidence cannot bypass the veto threshold."""
    with pytest.raises(ValueError) as error:
        apply_gate(json.loads(activity))
    activity_context["error"] = str(error.value)


@when(parsers.parse("volume configuration {config} is parsed"))
def invalid_config(activity_context, config):
    """Exercise strict configuration and unknown-key validation."""
    with pytest.raises(ValueError) as error:
        parse_volume_config(json.loads(config), strategy="volume-test")
    activity_context["error"] = str(error.value)


@when("valid volume configuration is parsed")
def valid_config(activity_context):
    """Retain both strategy-provided settings."""
    activity_context["config"] = parse_volume_config(
        {"lookback": 3, "min_relative_activity": 2}, strategy="volume-test"
    )


@then("its lookback is 3 and its threshold is 2")
def configured_values(activity_context):
    """The parser must neither discard nor replace the user's settings."""
    assert activity_context["config"] == VolumeConfig(lookback=3, min_relative_activity=2)


@given("canonical tick counts spanning December and January")
def year_boundary_prices(activity_context):
    """Persist adjacent year partitions using the same canonical writer."""
    canonical_prices(activity_context)
    path = layout.price_path_for(
        activity_context["data_root"], activity_context["instrument"], "m1", 2019, 12
    )
    write_bars(path, datetime(2019, 12, 31, tzinfo=UTC), [15])
    activity_context["december"] = path
    activity_context["originals"][path] = path.read_bytes()


@when(parsers.parse("activity provenance covers {start} through {end}"))
def collect_provenance(activity_context, start, end):
    """Hash a real date window without deriving prices or modifying Parquet."""
    activity_context["window"] = (date.fromisoformat(start), date.fromisoformat(end))
    activity_context["manifest"] = activity_provenance(
        activity_context["data_root"], activity_context["instrument"], *activity_context["window"]
    )


@then(parsers.parse("the activity manifest hashes exact bytes for {months}"))
def exact_provenance(activity_context, months):
    """Use independent byte-array SHA-256 and require portable paths in calendar order."""
    root = activity_context["data_root"]
    paths = [activity_context[month] for month in months.split(",")]
    expected = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }
    assert activity_context["manifest"] == expected
    assert list(activity_context["manifest"]) == list(expected)


@when("only the first January tick count is changed")
def changed_tick_count(activity_context):
    """Rewrite one real tick_count while preserving every timestamp and OHLC field."""
    repository = ParquetRepository(QuoteBar, activity_context["january"])
    bars = repository.read_all()
    before = bars[0].model_dump(exclude={"tick_count"})
    bars[0] = bars[0].model_copy(update={"tick_count": bars[0].tick_count + 1})
    assert bars[0].model_dump(exclude={"tick_count"}) == before
    repository.put(bars)


@when("activity provenance is collected again for the same window")
def recollect_provenance(activity_context):
    """A second call must read current bytes rather than reuse cached digests."""
    activity_context["updated_manifest"] = activity_provenance(
        activity_context["data_root"], activity_context["instrument"], *activity_context["window"]
    )


@then("only the January digest changes and matches the new exact bytes")
def changed_digest(activity_context):
    """A tick-only mutation is visible while the untouched month's digest stays stable."""
    before, after = activity_context["manifest"], activity_context["updated_manifest"]
    path = activity_context["january"]
    key = path.relative_to(activity_context["data_root"]).as_posix()
    assert before.keys() == after.keys()
    assert [name for name in before if before[name] != after[name]] == [key]
    assert after[key] == hashlib.sha256(path.read_bytes()).hexdigest()


@when("identical canonical files are copied to a different root")
def relocated_prices(activity_context):
    """Copy only temporary fixture bytes to mimic a different container mount root."""
    root = activity_context["data_root"]
    relocated = root / "relocated"
    for path, content in activity_context["originals"].items():
        destination = relocated / path.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    activity_context["relocated_manifest"] = activity_provenance(
        relocated, activity_context["instrument"], *activity_context["window"]
    )


@then("the relocated activity manifest is identical")
def portable_provenance(activity_context):
    """Absolute mount paths must not affect artifact identity."""
    assert activity_context["relocated_manifest"] == activity_context["manifest"]


@given("the February canonical file is absent")
def remove_february_fixture(activity_context):
    """Remove only the temporary month fixture to exercise real missing-file IO."""
    activity_context["february"].unlink()


@when("activity provenance is requested across the missing month")
def missing_provenance_month(activity_context):
    """A successfully hashed earlier month must not conceal the later missing file."""
    with pytest.raises(ValueError) as error:
        activity_provenance(
            activity_context["data_root"],
            activity_context["instrument"],
            date(2020, 1, 31),
            date(2020, 2, 1),
        )
    activity_context["error"] = str(error.value)


@when("activity provenance is requested with reversed dates")
def reversed_provenance_dates(activity_context):
    """Reject reversed windows rather than returning an unbound empty manifest."""
    with pytest.raises(ValueError) as error:
        activity_provenance(
            activity_context["data_root"],
            activity_context["instrument"],
            date(2020, 2, 1),
            date(2020, 1, 31),
        )
    activity_context["error"] = str(error.value)
