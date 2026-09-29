"""Steps for news_window.feature — F4's multi-month index and host-side pre-flight check."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from algo_backtest.chain.filters.f4_news_context import (
    NewsContextIndex,
    load_news_context_window,
    news_build_command,
    news_coverage_problems,
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
    problems: list[str] | None = None
    start: date | None = None
    end: date | None = None


@pytest.fixture
def window_ctx(tmp_path: Path) -> _WindowCtx:
    """A fresh per-scenario context over an empty tmp data root."""
    return _WindowCtx(root=tmp_path)


def _write_grid(root: Path, first: datetime, after: datetime, intensity: float) -> None:
    """Every minute in [first, after) at a constant event_intensity, in first's partition."""
    minutes = int((after - first).total_seconds() // 60)
    rows = [
        GdeltFeature(timestamp=first + timedelta(minutes=i), event_intensity=intensity)
        for i in range(minutes)
    ]
    path = event_feature_path(root, "gdelt", first.year, first.month)
    ParquetRepository(GdeltFeature, path).put(rows)


def _write_month(root: Path, year: int, month: int, intensity: float) -> None:
    """Every minute of one month at a constant event_intensity."""
    first = datetime(year, month, 1, tzinfo=UTC)
    after = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=UTC)
    _write_grid(root, first, after, intensity)


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


@given(
    parsers.parse("GDELT event features for 2020-01 built only from 2020-01-01 through {last}")
)
def _partial_month(window_ctx: _WindowCtx, last: str) -> None:
    after = datetime.combine(date.fromisoformat(last) + timedelta(days=1), datetime.min.time(), UTC)
    _write_grid(window_ctx.root, datetime(2020, 1, 1, tzinfo=UTC), after, 1.5)


@given(
    parsers.parse("GDELT event features for all of 2020-01 except {gap_first} through {gap_last}")
)
def _gapped_month(window_ctx: _WindowCtx, gap_first: str, gap_last: str) -> None:
    def midnight(day: date) -> datetime:
        return datetime.combine(day, datetime.min.time(), UTC)

    gap_start = midnight(date.fromisoformat(gap_first))
    gap_end = midnight(date.fromisoformat(gap_last) + timedelta(days=1))
    rows = [
        GdeltFeature(timestamp=minute, event_intensity=1.5)
        for minute in (
            datetime(2020, 1, 1, tzinfo=UTC) + timedelta(minutes=i) for i in range(31 * 1440)
        )
        if not gap_start <= minute < gap_end
    ]
    path = event_feature_path(window_ctx.root, "gdelt", 2020, 1)
    ParquetRepository(GdeltFeature, path).put(rows)


@when(parsers.parse("news coverage is checked for {start} to {end}"))
def _check_coverage(window_ctx: _WindowCtx, start: str, end: str) -> None:
    window_ctx.start, window_ctx.end = date.fromisoformat(start), date.fromisoformat(end)
    window_ctx.problems = news_coverage_problems(
        window_ctx.root, "EURUSD", window_ctx.start, window_ctx.end
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


@then("the coverage problems name the missing 2020-02 partition")
def _names_missing_feb(window_ctx: _WindowCtx) -> None:
    expected = str(event_feature_path(window_ctx.root, "gdelt", 2020, 2))
    assert window_ctx.problems and any(expected in p for p in window_ctx.problems)


@then(parsers.parse('the build command is "{command}"'))
def _build_command(window_ctx: _WindowCtx, command: str) -> None:
    assert window_ctx.start is not None and window_ctx.end is not None
    assert news_build_command(window_ctx.start, window_ctx.end) == command


@then(parsers.parse('the coverage problems name decision minute "{minute}"'))
def _names_minute(window_ctx: _WindowCtx, minute: str) -> None:
    assert window_ctx.problems == [f"no GDELT event_intensity at decision minute {minute}"]


@then("there are no coverage problems")
def _no_problems(window_ctx: _WindowCtx) -> None:
    assert window_ctx.problems == []


@then("the window's sentiment source is absent")
def _source_absent(window_ctx: _WindowCtx) -> None:
    assert window_ctx.index is not None and window_ctx.index.sentiment_source_present is False


@then("the window's sentiment source is present")
def _source_present(window_ctx: _WindowCtx) -> None:
    assert window_ctx.index is not None and window_ctx.index.sentiment_source_present is True


@then(
    parsers.parse(
        'the coverage problems name {count:d} decision minutes from "{first}" to "{last}"'
    )
)
def _names_range(window_ctx: _WindowCtx, count: int, first: str, last: str) -> None:
    assert window_ctx.problems == [
        f"no GDELT event_intensity at {count} decision minutes (first {first}, last {last})"
    ]
