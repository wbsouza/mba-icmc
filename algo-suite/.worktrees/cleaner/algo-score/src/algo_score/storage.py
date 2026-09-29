"""Storage adapters for sentiment scoring inputs, cache, and outputs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pyarrow.parquet as pq
from algo_core.cache.local import LocalCache
from algo_core.repository.parquet import ParquetRepository

from algo_score.paths import article_score_path, currency_path, sentiment_path, symbol_path
from algo_score.scorers.models import (
    ArticleScore,
    CurrencySentimentFeature,
    NewsArticle,
    SentimentFeature,
    SymbolSentimentFeature,
)


@dataclass(frozen=True)
class SentimentOutputPaths:
    """Paths written by one sentiment scoring run."""

    sentiment: Path
    articles: Path
    currencies: Path
    symbols: Path


class ScoreCache:
    """Read-through cache adapter for model-versioned article scores."""

    def __init__(self, data_root: Path, scorer: str) -> None:
        self._cache = LocalCache(ArticleScore, data_root / ".cache" / "algo-score" / scorer)

    def get_or_compute(self, key: str, compute: Callable[[], ArticleScore]) -> ArticleScore:
        """Return a cached score or compute and persist it."""
        return self._cache.get_or_compute(key, compute)


def read_articles(data_root: Path, source: str, start: date, end: date) -> list[NewsArticle]:
    """Read article fixtures from flat or year/month partitioned Parquet paths."""
    rows: list[NewsArticle] = []
    for path in _article_paths(data_root, source, start, end):
        if not path.exists():
            continue
        table = pq.read_table(path)  # type: ignore[no-untyped-call]
        rows.extend(NewsArticle.model_validate(row) for row in table.to_pylist())
    if not rows:
        raise ValueError(f"missing article fixture for source {source!r}")
    return rows


def read_price_minutes(data_root: Path) -> set[datetime] | None:
    """Read optional price-grid minutes used to align sentiment features."""
    price_root = data_root / "parquet" / "price_minutes"
    if not price_root.exists():
        return None
    minutes: set[datetime] = set()
    for path in sorted(price_root.rglob("*.parquet")):
        table = pq.read_table(path)  # type: ignore[no-untyped-call]
        minutes.update(table.column("timestamp").to_pylist())
    return minutes


def write_sentiment_outputs(
    data_root: Path,
    scorer: str,
    year: int,
    month: int,
    *,
    features: list[SentimentFeature],
    scores: list[ArticleScore],
    currency_rows: list[CurrencySentimentFeature],
    symbol_rows: list[SymbolSentimentFeature],
) -> SentimentOutputPaths:
    """Write all sentiment scoring outputs for one year/month partition."""
    paths = SentimentOutputPaths(
        sentiment=sentiment_path(data_root, scorer, year, month),
        articles=article_score_path(data_root, scorer, year, month),
        currencies=currency_path(data_root, scorer, year, month),
        symbols=symbol_path(data_root, scorer, year, month),
    )
    ParquetRepository(SentimentFeature, paths.sentiment).put(features)
    ParquetRepository(ArticleScore, paths.articles).put(scores)
    ParquetRepository(CurrencySentimentFeature, paths.currencies).put(currency_rows)
    ParquetRepository(SymbolSentimentFeature, paths.symbols).put(symbol_rows)
    return paths


def _article_paths(data_root: Path, source: str, start: date, end: date) -> list[Path]:
    """Return candidate article fixture paths for a source and date range."""
    root = data_root / "parquet" / "news" / source
    paths = [root / "data.parquet"]
    paths.extend(
        root / f"year={year:04d}" / f"month={month:02d}" / "data.parquet"
        for year, month in _months(start, end)
    )
    return paths


def _months(start: date, end: date) -> list[tuple[int, int]]:
    """Enumerate year/month partition keys across an inclusive date window."""
    cursor = date(start.year, start.month, 1)
    months: list[tuple[int, int]] = []
    while cursor <= end:
        months.append((cursor.year, cursor.month))
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
    return months
