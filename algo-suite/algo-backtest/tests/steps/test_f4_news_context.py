"""Steps for f4_news_context.feature — the F4 news-context filter.

Writes real production Spec 03 values (the true January-2020 GDELT daily Goldstein
Scale readings, and real-shaped `SymbolSentimentFeature` rows) through the same
`ParquetRepository` writer + model classes `algo-score` uses, into `tmp_path` — a real
repository round-trip over real data, not a hand-invented fixture, kept small/portable
rather than the full 44640-row production month (see `f4_news_context.feature`'s
Background for why the sentiment side is a real-shaped sample rather than real
production output: TD-48).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.f4_news_context import (
    F4NewsContextFilter,
    NewsContextConfig,
    NewsContextIndex,
    load_news_context_index,
    parse_news_context_config,
)
from algo_backtest.chain.model import ExecutionState, FilterResult
from algo_core.repository.parquet import ParquetRepository
from algo_score.events.models import GdeltFeature
from algo_score.events.paths import feature_path as event_feature_path
from algo_score.paths import symbol_path
from algo_score.scorers.models import SymbolSentimentFeature
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/f4_news_context.feature")

# The true per-minute GDELT event_intensity for a handful of real January-2020 minutes,
# read directly from the actual materialized `data/parquet/events/_features/gdelt/
# year=2020/month=01/data.parquet` (44640 real rows, built by `algo-score events --kind
# gdelt`). 2020-01-01 is the month's most conflictual real day; 2020-01-15 is calm.
_REAL_JAN_2020_MINUTES: dict[str, float] = {
    "2020-01-01T00:00:00+00:00": -1.5791368337311142,
    "2020-01-01T00:05:00+00:00": -1.5791368337311142,
    "2020-01-15T00:00:00+00:00": 0.5615042436044383,
    "2020-01-15T00:05:00+00:00": 0.5615042436044383,
}


@dataclass
class _F4Ctx:
    """Per-scenario fixture context: written Parquet paths, config, result/error seen."""

    data_root: Path
    event_rows: list[GdeltFeature] = field(default_factory=list)
    sentiment_rows: list[SymbolSentimentFeature] = field(default_factory=list)
    event_parquet_written: bool = False
    config: NewsContextConfig | None = None
    result: FilterResult | None = None
    error: Exception | None = None
    index_error: Exception | None = None
    loaded_index: NewsContextIndex | None = None
    section: dict[str, Any] = field(default_factory=dict)
    parsed_config: NewsContextConfig | None = None
    parse_error: Exception | None = None


@pytest.fixture
def f4_ctx(tmp_path: Path) -> _F4Ctx:
    """A fresh per-scenario F4 context rooted at an isolated `tmp_path` data root."""
    return _F4Ctx(data_root=tmp_path)


def _parse_ts(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def _parse_threshold(raw: str) -> float | None:
    return None if raw == "null" else float(raw)


@given("the real January 2020 GDELT event-feature Parquet")
def _real_gdelt_parquet(f4_ctx: _F4Ctx) -> None:
    f4_ctx.event_rows = [
        GdeltFeature(timestamp=_parse_ts(ts), event_intensity=intensity)
        for ts, intensity in _REAL_JAN_2020_MINUTES.items()
    ]
    path = event_feature_path(f4_ctx.data_root, "gdelt", 2020, 1)
    ParquetRepository(GdeltFeature, path).put(f4_ctx.event_rows)
    f4_ctx.event_parquet_written = True


@given(parsers.parse("no GDELT event-feature Parquet exists for {year_month}"))
def _no_gdelt_parquet(f4_ctx: _F4Ctx, year_month: str) -> None:
    # Nothing written at f4_ctx.data_root for this month: the mandatory-file fail-fast
    # path is exercised by construction (no ParquetRepository.put() call happens).
    assert year_month  # the scenario names the month only for readability


@given(
    parsers.parse(
        'a real SymbolSentimentFeature row for "{symbol}" at "{ts}" with polarity {polarity:g}'
    )
)
def _real_sentiment_row(f4_ctx: _F4Ctx, symbol: str, ts: str, polarity: float) -> None:
    row = SymbolSentimentFeature(
        timestamp=_parse_ts(ts),
        symbol=symbol,
        polarity=polarity,
        confidence=0.8,
        n_articles=3,
        scorer="lm",
        model_version="lm-fixture-v1",
    )
    f4_ctx.sentiment_rows.append(row)
    path = symbol_path(f4_ctx.data_root, "lm", 2020, 1)
    ParquetRepository(SymbolSentimentFeature, path).put(f4_ctx.sentiment_rows)


@given(
    parsers.parse(
        'a real SymbolSentimentFeature row for "{symbol}" at "{ts}" with a null polarity'
    )
)
def _real_sentiment_row_null_polarity(f4_ctx: _F4Ctx, symbol: str, ts: str) -> None:
    row = SymbolSentimentFeature(
        timestamp=_parse_ts(ts),
        symbol=symbol,
        polarity=None,
        confidence=0.0,
        n_articles=0,
        scorer="lm",
        model_version="lm-fixture-v1",
    )
    f4_ctx.sentiment_rows.append(row)
    path = symbol_path(f4_ctx.data_root, "lm", 2020, 1)
    ParquetRepository(SymbolSentimentFeature, path).put(f4_ctx.sentiment_rows)


@given(
    parsers.parse(
        "a news-context veto threshold of {veto} and no sentiment threshold"
    )
)
def _config_no_sentiment(f4_ctx: _F4Ctx, veto: str) -> None:
    f4_ctx.config = NewsContextConfig(
        event_intensity_veto_threshold=_parse_threshold(veto),
        sentiment_direction_threshold=None,
    )


@given(
    parsers.parse(
        "a news-context veto threshold of {veto} and sentiment threshold {direction:g}"
    )
)
def _config_with_sentiment(f4_ctx: _F4Ctx, veto: str, direction: float) -> None:
    f4_ctx.config = NewsContextConfig(
        event_intensity_veto_threshold=_parse_threshold(veto),
        sentiment_direction_threshold=direction,
    )


def _build_filter(f4_ctx: _F4Ctx, pair: str) -> F4NewsContextFilter:
    assert f4_ctx.config is not None
    index = load_news_context_index(f4_ctx.data_root, pair, 2020, 1)
    return F4NewsContextFilter(index=index, config=f4_ctx.config)


@when(parsers.parse('F4 applies to timestamp "{ts}" for pair "{pair}"'))
def _apply(f4_ctx: _F4Ctx, ts: str, pair: str) -> None:
    news_filter = _build_filter(f4_ctx, pair)
    state = ExecutionState(timestamp=_parse_ts(ts), pair=pair, features={})
    f4_ctx.result = news_filter.apply(state)


@when(parsers.parse('F4 applies to timestamp "{ts}" for pair "{pair}" and fails'))
def _apply_expect_failure(f4_ctx: _F4Ctx, ts: str, pair: str) -> None:
    news_filter = _build_filter(f4_ctx, pair)
    state = ExecutionState(timestamp=_parse_ts(ts), pair=pair, features={})
    try:
        f4_ctx.result = news_filter.apply(state)
    except ValueError as exc:
        f4_ctx.error = exc


@when(parsers.parse('the news-context index is loaded for "{pair}"'))
def _load_index(f4_ctx: _F4Ctx, pair: str) -> None:
    f4_ctx.loaded_index = load_news_context_index(f4_ctx.data_root, pair, 2020, 1)


@when(parsers.parse("loading the news-context index for {year_month} fails"))
def _load_index_fails(f4_ctx: _F4Ctx, year_month: str) -> None:
    year, month = (int(part) for part in year_month.split("-"))
    try:
        load_news_context_index(f4_ctx.data_root, "EURUSD", year, month)
    except ValueError as exc:
        f4_ctx.index_error = exc


@then("F4's result vetoes")
def _vetoes(f4_ctx: _F4Ctx) -> None:
    assert f4_ctx.result is not None
    assert f4_ctx.result.veto is True


@then("F4's result does not veto")
def _no_veto(f4_ctx: _F4Ctx) -> None:
    assert f4_ctx.result is not None
    assert f4_ctx.result.veto is False


@then(parsers.parse('F4\'s recommendation is "{reco}"'))
def _recommendation(f4_ctx: _F4Ctx, reco: str) -> None:
    assert f4_ctx.result is not None
    assert f4_ctx.result.recommendation.value == reco


@then(parsers.parse('F4\'s filter_name is "{name}"'))
def _filter_name(f4_ctx: _F4Ctx, name: str) -> None:
    assert f4_ctx.result is not None
    assert f4_ctx.result.filter_name == name


@then(parsers.parse('F4\'s reason mentions "{fragment}"'))
def _reason_mentions(f4_ctx: _F4Ctx, fragment: str) -> None:
    assert f4_ctx.result is not None
    assert fragment in f4_ctx.result.reason


@then(parsers.parse('F4 enriches "{key}" with value {value:g}'))
def _enriches(f4_ctx: _F4Ctx, key: str, value: float) -> None:
    assert f4_ctx.result is not None
    assert f4_ctx.result.enrichment[key] == pytest.approx(value)


@then(parsers.parse('F4\'s metadata "{key}" is {expected}'))
def _metadata(f4_ctx: _F4Ctx, key: str, expected: str) -> None:
    assert f4_ctx.result is not None
    assert f4_ctx.result.metadata[key] is (expected == "true")


@then(parsers.parse('the loaded index has no sentiment entry for "{pair}" at "{ts}"'))
def _index_no_sentiment_entry(f4_ctx: _F4Ctx, pair: str, ts: str) -> None:
    assert f4_ctx.loaded_index is not None
    assert (_parse_ts(ts), pair) not in f4_ctx.loaded_index.sentiment_polarity


@then(parsers.parse('the failure names "{fragment}"'))
def _failure_names(f4_ctx: _F4Ctx, fragment: str) -> None:
    error = f4_ctx.index_error if f4_ctx.index_error is not None else f4_ctx.error
    assert error is not None, "expected a captured failure but none was raised"
    assert fragment in str(error)


_SECTION_DEFAULTS: dict[str, Any] = {
    "event_intensity_veto_threshold": -0.5,
    "sentiment_direction_threshold": 0.15,
}


@given(
    parsers.parse(
        "a news_context section with event_intensity_veto_threshold={veto}, "
        "sentiment_direction_threshold={direction}"
    )
)
def _news_context_section(f4_ctx: _F4Ctx, veto: str, direction: str) -> None:
    f4_ctx.section = {
        "event_intensity_veto_threshold": yaml.safe_load(veto),
        "sentiment_direction_threshold": yaml.safe_load(direction),
    }


@given(parsers.parse('a news_context section missing "{missing_key}"'))
def _news_context_section_missing(f4_ctx: _F4Ctx, missing_key: str) -> None:
    f4_ctx.section = {k: v for k, v in _SECTION_DEFAULTS.items() if k != missing_key}


@given(parsers.parse('a news_context section whose "{key}" is the string "{value}"'))
def _news_context_section_string(f4_ctx: _F4Ctx, key: str, value: str) -> None:
    f4_ctx.section = {**_SECTION_DEFAULTS, key: value}


@when(parsers.parse('the news-context config is parsed for strategy "{strategy}"'))
def _parse_config(f4_ctx: _F4Ctx, strategy: str) -> None:
    f4_ctx.parsed_config = parse_news_context_config(f4_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the news-context config for strategy "{strategy}" fails'))
def _parse_config_fails(f4_ctx: _F4Ctx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_news_context_config(f4_ctx.section, strategy=strategy)
    f4_ctx.parse_error = exc_info.value


@then(parsers.parse("the parsed news-context config has event_intensity_veto_threshold {expected}"))
def _parsed_veto(f4_ctx: _F4Ctx, expected: str) -> None:
    assert f4_ctx.parsed_config is not None
    assert f4_ctx.parsed_config.event_intensity_veto_threshold == _parse_threshold(expected)


@then(parsers.parse("the parsed news-context config has sentiment_direction_threshold {expected}"))
def _parsed_direction(f4_ctx: _F4Ctx, expected: str) -> None:
    assert f4_ctx.parsed_config is not None
    assert f4_ctx.parsed_config.sentiment_direction_threshold == _parse_threshold(expected)


@then(parsers.parse('the news-context config failure names "{fragment}"'))
def _parse_failure_names(f4_ctx: _F4Ctx, fragment: str) -> None:
    assert f4_ctx.parse_error is not None
    assert fragment in str(f4_ctx.parse_error)
