"""Steps for confluence_relative_intensity.feature — F4's `intensity_relative` mode
(story 21, T4).

The news index is built in memory (the Parquet round-trip is proven by
`test_f4_news_context.py`); the monthly snapshots and the current intensity's
availability are injected exactly as `chain/wiring.py` will after T12.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.f4_news_context import (
    F4NewsContextFilter,
    NewsContextConfig,
    NewsContextIndex,
    news_context_mapping,
    parse_news_context_config,
)
from algo_backtest.chain.intensity_history import IntensitySnapshot
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_relative_intensity.feature")

_CLOCK_MINUTES = 60


@dataclass
class _RelativeCtx:
    """Per-scenario context: the index, config, injected snapshots/availability, result."""

    event_intensity: dict[datetime, float] = field(default_factory=dict)
    sentiment_polarity: dict[tuple[datetime, str], float] = field(default_factory=dict)
    availability: dict[datetime, datetime] = field(default_factory=dict)
    snapshots: dict[datetime, IntensitySnapshot] | None = field(default_factory=dict)
    section: dict[str, Any] = field(default_factory=dict)
    config: NewsContextConfig | None = None
    result: FilterResult | None = None
    error: Exception | None = None
    parsed_config: NewsContextConfig | None = None
    parse_error: Exception | None = None


@pytest.fixture
def relative_ctx() -> _RelativeCtx:
    """A fresh per-scenario relative-mode context."""
    return _RelativeCtx()


def _utc(raw: str) -> datetime:
    """An ISO timestamp (`Z` or offset) as an aware UTC datetime."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _cell(raw: str) -> Any:
    """A flow-YAML cell (`null`, `-0.5`, `-1`, ...)."""
    return yaml.safe_load(raw)


def _result(relative_ctx: _RelativeCtx) -> FilterResult:
    """The applied result, failing loudly if F4 raised instead."""
    assert relative_ctx.result is not None, f"no result; captured error: {relative_ctx.error}"
    return relative_ctx.result


@given("an in-memory news index with no sentiment source")
def _bare_index(relative_ctx: _RelativeCtx) -> None:
    relative_ctx.event_intensity = {}
    relative_ctx.sentiment_polarity = {}


# --- Sections ---


@given(
    parsers.parse(
        "a news_context section with direction_source intensity_relative, veto {veto:S} and "
        "intensity_sign {sign:d}"
    )
)
def _relative_section(relative_ctx: _RelativeCtx, veto: str, sign: int) -> None:
    relative_ctx.section = {
        "event_intensity_veto_threshold": _cell(veto),
        "sentiment_direction_threshold": None,
        "direction_source": "intensity_relative",
        "intensity_sign": sign,
    }
    relative_ctx.config = parse_news_context_config(relative_ctx.section, strategy="scenario")


@given(
    parsers.parse(
        "a news_context section with direction_source intensity_relative, veto {veto:S}, "
        "sentiment null and intensity_sign {sign:S}"
    )
)
def _relative_section_for_parsing(relative_ctx: _RelativeCtx, veto: str, sign: str) -> None:
    """`absent` leaves `intensity_sign` out; the config is parsed by a later When."""
    relative_ctx.section = {
        "event_intensity_veto_threshold": _cell(veto),
        "sentiment_direction_threshold": None,
        "direction_source": "intensity_relative",
    }
    if sign != "absent":
        relative_ctx.section["intensity_sign"] = _cell(sign)


@given(
    parsers.parse(
        "a news_context section with direction_source intensity, veto {veto:g}, buy {buy:g}, "
        "sell {sell:g} and intensity_sign {sign:d}"
    )
)
def _static_section(
    relative_ctx: _RelativeCtx, veto: float, buy: float, sell: float, sign: int
) -> None:
    relative_ctx.section = {
        "event_intensity_veto_threshold": veto,
        "sentiment_direction_threshold": None,
        "direction_source": "intensity",
        "intensity_buy_threshold": buy,
        "intensity_sell_threshold": sell,
        "intensity_sign": sign,
    }
    relative_ctx.config = parse_news_context_config(relative_ctx.section, strategy="scenario")


@given(
    parsers.parse(
        "a news_context section with direction_source sentiment, veto {veto:g} and sentiment "
        "threshold {threshold:g}"
    )
)
def _sentiment_section(relative_ctx: _RelativeCtx, veto: float, threshold: float) -> None:
    relative_ctx.section = {
        "event_intensity_veto_threshold": veto,
        "sentiment_direction_threshold": threshold,
        "direction_source": "sentiment",
    }
    relative_ctx.config = parse_news_context_config(relative_ctx.section, strategy="scenario")


@given(
    parsers.parse(
        "a news_context section with direction_source {source:S}, intensity_buy_threshold "
        "{buy:S}, intensity_sell_threshold {sell:S} and intensity_sign {sign:S}"
    )
)
def _section_with_thresholds(
    relative_ctx: _RelativeCtx, source: str, buy: str, sell: str, sign: str
) -> None:
    """`absent` leaves a key out; every other cell is flow-style YAML."""
    section: dict[str, Any] = {
        "event_intensity_veto_threshold": -0.5,
        "sentiment_direction_threshold": None,
        "direction_source": source,
    }
    for key, cell in (
        ("intensity_buy_threshold", buy),
        ("intensity_sell_threshold", sell),
        ("intensity_sign", sign),
    ):
        if cell != "absent":
            section[key] = _cell(cell)
    relative_ctx.section = section


@given(
    parsers.parse(
        "a news_context section with event_intensity_veto_threshold={veto:S}, "
        "sentiment_direction_threshold={threshold:S}"
    )
)
def _legacy_section(relative_ctx: _RelativeCtx, veto: str, threshold: str) -> None:
    relative_ctx.section = {
        "event_intensity_veto_threshold": _cell(veto),
        "sentiment_direction_threshold": _cell(threshold),
    }


# --- Injected snapshots, intensities and availability ---


def _snapshot(
    cutoff: datetime,
    *,
    status: str,
    q_low: float | None,
    q_high: float | None,
    sample_count: int,
    source_hash: str,
) -> IntensitySnapshot:
    """A snapshot as `IntensityHistory.snapshot_for` would freeze it for `cutoff`'s month."""
    last_close = cutoff - timedelta(minutes=_CLOCK_MINUTES)
    return IntensitySnapshot(
        cutoff=cutoff,
        window_start=cutoff - timedelta(days=30),
        clock_minutes=_CLOCK_MINUTES,
        q_low=q_low,
        q_high=q_high,
        sample_count=sample_count,
        max_closed_at=last_close,
        max_available_at=last_close,
        source_hash=source_hash,
        quantile_method="linear",
        schema_version=1,
        status=status,
    )


@given(
    parsers.parse(
        'a READY intensity snapshot for cutoff "{cutoff}" with q10 {q_low:g}, q90 {q_high:g}, '
        'sample_count {count:d} and source_hash "{source_hash}"'
    )
)
def _ready_snapshot(
    relative_ctx: _RelativeCtx,
    cutoff: str,
    q_low: float,
    q_high: float,
    count: int,
    source_hash: str,
) -> None:
    assert relative_ctx.snapshots is not None
    relative_ctx.snapshots[_utc(cutoff)] = _snapshot(
        _utc(cutoff),
        status="READY",
        q_low=q_low,
        q_high=q_high,
        sample_count=count,
        source_hash=source_hash,
    )


@given(
    parsers.parse('a WARMUP intensity snapshot for cutoff "{cutoff}" with sample_count {count:d}')
)
def _warmup_snapshot(relative_ctx: _RelativeCtx, cutoff: str, count: int) -> None:
    assert relative_ctx.snapshots is not None
    relative_ctx.snapshots[_utc(cutoff)] = _snapshot(
        _utc(cutoff),
        status="WARMUP",
        q_low=None,
        q_high=None,
        sample_count=count,
        source_hash="warmup",
    )


@given("no intensity snapshot source")
def _no_snapshots(relative_ctx: _RelativeCtx) -> None:
    relative_ctx.snapshots = None


@given(
    parsers.parse(
        'the event intensity at "{timestamp}" is {intensity:g}, available at "{available}"'
    )
)
def _intensity_with_availability(
    relative_ctx: _RelativeCtx, timestamp: str, intensity: float, available: str
) -> None:
    relative_ctx.event_intensity[_utc(timestamp)] = intensity
    relative_ctx.availability[_utc(timestamp)] = _utc(available)


@given(parsers.parse('the event intensity at "{timestamp}" is {intensity:g}'))
def _intensity_only(relative_ctx: _RelativeCtx, timestamp: str, intensity: float) -> None:
    relative_ctx.event_intensity[_utc(timestamp)] = intensity


@given(parsers.parse('the sentiment polarity for "{pair}" at "{timestamp}" is {polarity:g}'))
def _polarity(relative_ctx: _RelativeCtx, pair: str, timestamp: str, polarity: float) -> None:
    relative_ctx.sentiment_polarity[(_utc(timestamp), pair)] = polarity


# --- Applying ---


def _build(relative_ctx: _RelativeCtx) -> F4NewsContextFilter:
    """F4 from the scenario's parsed config and injected sources."""
    assert relative_ctx.config is not None
    index = NewsContextIndex(
        event_intensity=dict(relative_ctx.event_intensity),
        sentiment_polarity=dict(relative_ctx.sentiment_polarity),
        sentiment_source_present=False,
    )
    availability = dict(relative_ctx.availability) if relative_ctx.availability else None
    return F4NewsContextFilter(
        index=index,
        config=relative_ctx.config,
        snapshots=relative_ctx.snapshots,
        availability=availability,
    )


@when(parsers.parse('relative F4 applies to timestamp "{timestamp}" for pair "{pair}"'))
def _apply(relative_ctx: _RelativeCtx, timestamp: str, pair: str) -> None:
    state = ExecutionState(timestamp=_utc(timestamp), pair=pair, features={})
    relative_ctx.result = _build(relative_ctx).apply(state)


@when(parsers.parse('relative F4 applies to timestamp "{timestamp}" for pair "{pair}" and fails'))
def _apply_fails(relative_ctx: _RelativeCtx, timestamp: str, pair: str) -> None:
    news_filter = _build(relative_ctx)
    state = ExecutionState(timestamp=_utc(timestamp), pair=pair, features={})
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        news_filter.apply(state)
    relative_ctx.error = exc_info.value


@when("relative F4 is built without a snapshot source and fails")
def _build_without_snapshots_fails(relative_ctx: _RelativeCtx) -> None:
    relative_ctx.snapshots = None
    relative_ctx.availability = {}
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _build(relative_ctx)
    relative_ctx.error = exc_info.value


# --- Result assertions ---


@then(parsers.parse('relative F4\'s recommendation is "{reco}"'))
def _recommendation(relative_ctx: _RelativeCtx, reco: str) -> None:
    result = _result(relative_ctx)
    assert result.recommendation == Recommendation(reco), result.reason


@then("relative F4's result does not veto")
def _no_veto(relative_ctx: _RelativeCtx) -> None:
    assert _result(relative_ctx).veto is False


@then("relative F4's result vetoes")
def _vetoes(relative_ctx: _RelativeCtx) -> None:
    assert _result(relative_ctx).veto is True


@then(parsers.parse('relative F4\'s filter_name is "{name}"'))
def _filter_name(relative_ctx: _RelativeCtx, name: str) -> None:
    assert _result(relative_ctx).filter_name == name


@then(parsers.parse('relative F4 enriches "{key}" with value {value:g}'))
def _enriches(relative_ctx: _RelativeCtx, key: str, value: float) -> None:
    assert _result(relative_ctx).enrichment[key] == pytest.approx(value)


@then(parsers.parse('relative F4\'s reason mentions "{fragment}"'))
def _reason_mentions(relative_ctx: _RelativeCtx, fragment: str) -> None:
    assert fragment in _result(relative_ctx).reason, _result(relative_ctx).reason


@then(parsers.parse('relative F4\'s metadata "{key}" is {raw:S}'))
def _metadata_is(relative_ctx: _RelativeCtx, key: str, raw: str) -> None:
    """The cell is flow YAML: a quoted string, a number, `null`, `true`/`false`."""
    actual = _result(relative_ctx).metadata[key]
    expected = _cell(raw)
    if isinstance(expected, float):
        assert actual == pytest.approx(expected), (key, actual, expected)
    else:
        assert actual == expected, (key, actual, expected)


@then(parsers.parse('relative F4\'s metadata has no key "{key}"'))
def _metadata_lacks(relative_ctx: _RelativeCtx, key: str) -> None:
    assert key not in _result(relative_ctx).metadata


@then(parsers.parse('the relative F4 failure names "{fragment}"'))
def _failure_names(relative_ctx: _RelativeCtx, fragment: str) -> None:
    assert relative_ctx.error is not None, "expected a failure but none was raised"
    assert fragment in str(relative_ctx.error), str(relative_ctx.error)


# --- Config parsing ---


@when(parsers.parse('the news-context config is parsed for strategy "{strategy}"'))
def _parse(relative_ctx: _RelativeCtx, strategy: str) -> None:
    relative_ctx.parsed_config = parse_news_context_config(relative_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the news-context config for strategy "{strategy}" fails'))
def _parse_fails(relative_ctx: _RelativeCtx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_news_context_config(relative_ctx.section, strategy=strategy)
    relative_ctx.parse_error = exc_info.value


@then(
    parsers.parse(
        'the parsed news-context config has direction_source "{source}", buy {buy:S}, sell '
        "{sell:S} and sign {sign:S}"
    )
)
def _parsed(relative_ctx: _RelativeCtx, source: str, buy: str, sell: str, sign: str) -> None:
    config = relative_ctx.parsed_config
    assert config is not None
    assert config.direction_source == source
    assert config.intensity_buy_threshold == _cell(buy)
    assert config.intensity_sell_threshold == _cell(sell)
    assert config.intensity_sign == int(sign)


@then(
    parsers.parse(
        'the news-context mapping records direction_source "{source}" and intensity_sign {sign:d}'
    )
)
def _mapping_records(relative_ctx: _RelativeCtx, source: str, sign: int) -> None:
    assert relative_ctx.parsed_config is not None
    mapping = news_context_mapping(relative_ctx.parsed_config)
    assert mapping["direction_source"] == source
    assert mapping["intensity_sign"] == sign


@then(parsers.parse('the news-context mapping has no key "{key}"'))
def _mapping_lacks(relative_ctx: _RelativeCtx, key: str) -> None:
    assert relative_ctx.parsed_config is not None
    assert key not in news_context_mapping(relative_ctx.parsed_config)


@then(parsers.parse('the news-context config failure names "{fragment}"'))
def _parse_failure_names(relative_ctx: _RelativeCtx, fragment: str) -> None:
    assert relative_ctx.parse_error is not None
    assert fragment in str(relative_ctx.parse_error), str(relative_ctx.parse_error)
