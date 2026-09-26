"""Steps for news_window.feature — F4's multi-month index and host-side pre-flight check."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from algo_backtest.chain.filters.f4_news_context import (
    NewsContextIndex,
    load_news_context_window,
    missing_event_partitions,
)
from algo_core.repository.parquet import ParquetRepository
from algo_score.events.models import GdeltFeature
from algo_score.events.paths import feature_path as event_feature_path
from algo_score.paths import symbol_path
from algo_score.scorers.models import SymbolSentimentFeature
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/news_window.feature")


@dataclass
class _WindowCtx:
    """Per-scenario fixture context."""

    root: Path
    index: NewsContextIndex | None = None
    error: ValueError | None = None
    missing: list[Path] | None = None


@pytest.fixture
def window_ctx(tmp_path: Path) -> _WindowCtx:
    """A fresh per-scenario context over an empty tmp data root."""
    return _WindowCtx(root=tmp_path)


def _write_month(root: Path, year: int, month: int, intensity: float) -> None:
    """Every minute of one month at a constant event_intensity."""
    first = datetime(year, month, 1, tzinfo=UTC)
    after = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=UTC)
    minutes = int((after - first).total_seconds() // 60)
    rows = [
        GdeltFeature(timestamp=first + timedelta(minutes=i), event_intensity=intensity)
        for i in range(minutes)
    ]
    ParquetRepository(GdeltFeature, event_feature_path(root, "gdelt", year, month)).put(rows)


def _write_sentiment(root: Path, year: int, month: int) -> None:
    """One EURUSD sentiment row at noon on the month's last day in the window fixture."""
    row = SymbolSentimentFeature(
        timestamp=datetime(year, month, 31 if month == 1 else 1, 12, 0, tzinfo=UTC),
        symbol="EURUSD", polarity=0.4, confidence=0.8, n_articles=3, scorer="lm",
        model_version="lm-fixture-v1",
    )
    ParquetRepository(SymbolSentimentFeature, symbol_path(root, "lm", year, month)).put([row])


@given(
    parsers.parse(
        "GDELT event features for 2020-01 at intensity {jan:g} and for 2020-02 at intensity {feb:g}"
    )
)
def _two_months(window_ctx: _WindowCtx, jan: float, feb: float) -> None:
    _write_month(window_ctx.root, 2020, 1, jan)
    _write_month(window_ctx.root, 2020, 2, feb)


@given(parsers.parse("GDELT event features for 2020-01 at intensity {jan:g} only"))
def _one_month(window_ctx: _WindowCtx, jan: float) -> None:
    _write_month(window_ctx.root, 2020, 1, jan)


@given("EURUSD sentiment Parquet exists for 2020-01 only")
def _sentiment_jan(window_ctx: _WindowCtx) -> None:
    _write_sentiment(window_ctx.root, 2020, 1)


@given("EURUSD sentiment Parquet exists for 2020-01 and 2020-02")
def _sentiment_both(window_ctx: _WindowCtx) -> None:
    _write_sentiment(window_ctx.root, 2020, 1)
    _write_sentiment(window_ctx.root, 2020, 2)


@when(parsers.parse('the news-context window {start} to {end} is loaded for "{pair}"'))
def _load(window_ctx: _WindowCtx, start: str, end: str, pair: str) -> None:
    window_ctx.index = load_news_context_window(
        window_ctx.root, pair, date.fromisoformat(start), date.fromisoformat(end)
    )


@when(parsers.parse("loading the news-context window {start} to {end} fails"))
def _load_fails(window_ctx: _WindowCtx, start: str, end: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        load_news_context_window(
            window_ctx.root, "EURUSD", date.fromisoformat(start), date.fromisoformat(end)
        )
    window_ctx.error = excinfo.value


@when(parsers.parse("the missing event partitions for {start} to {end} are listed"))
def _list_missing(window_ctx: _WindowCtx, start: str, end: str) -> None:
    window_ctx.missing = missing_event_partitions(
        window_ctx.root, date.fromisoformat(start), date.fromisoformat(end)
    )


@then(parsers.parse('the index has event_intensity {value:g} at "{ts}"'))
def _intensity_at(window_ctx: _WindowCtx, value: float, ts: str) -> None:
    assert window_ctx.index is not None
    assert window_ctx.index.event_intensity[datetime.fromisoformat(ts)] == value


@then(parsers.parse('the index has sentiment {value:g} for "{pair}" at "{ts}"'))
def _sentiment_at(window_ctx: _WindowCtx, value: float, pair: str, ts: str) -> None:
    assert window_ctx.index is not None
    assert window_ctx.index.sentiment_polarity[(datetime.fromisoformat(ts), pair)] == value


@then(parsers.parse('the window failure names "{fragment}"'))
def _failure_names(window_ctx: _WindowCtx, fragment: str) -> None:
    assert window_ctx.error is not None and fragment in str(window_ctx.error)


@then(parsers.parse('the missing partitions are "{months}"'))
def _missing_are(window_ctx: _WindowCtx, months: str) -> None:
    assert window_ctx.missing is not None
    expected = [
        event_feature_path(window_ctx.root, "gdelt", int(ym[:4]), int(ym[5:7]))
        for ym in (m.strip() for m in months.split(","))
    ]
    assert window_ctx.missing == expected


@then("the window's sentiment source is absent")
def _source_absent(window_ctx: _WindowCtx) -> None:
    assert window_ctx.index is not None and window_ctx.index.sentiment_source_present is False


@then("the window's sentiment source is present")
def _source_present(window_ctx: _WindowCtx) -> None:
    assert window_ctx.index is not None and window_ctx.index.sentiment_source_present is True
