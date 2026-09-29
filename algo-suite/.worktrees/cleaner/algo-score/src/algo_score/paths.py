"""Filesystem paths for sentiment scorer outputs."""

from __future__ import annotations

from pathlib import Path


def sentiment_path(data_root: Path, scorer: str, year: int, month: int) -> Path:
    """Return the minute-bucket sentiment output path."""
    return _partition_path(data_root, scorer, year, month)


def article_score_path(data_root: Path, scorer: str, year: int, month: int) -> Path:
    """Return the per-article scorer output path."""
    return _partition_path(data_root, f"{scorer}_articles", year, month)


def currency_path(data_root: Path, scorer: str, year: int, month: int) -> Path:
    """Return the per-currency sentiment output path."""
    return _partition_path(data_root, f"{scorer}_currency", year, month)


def symbol_path(data_root: Path, scorer: str, year: int, month: int) -> Path:
    """Return the per-FX-symbol sentiment output path."""
    return _partition_path(data_root, f"{scorer}_symbol", year, month)


def _partition_path(data_root: Path, dataset: str, year: int, month: int) -> Path:
    """Return a year/month sentiment Parquet partition path."""
    return (
        data_root
        / "parquet"
        / "sentiment"
        / dataset
        / f"year={year:04d}"
        / f"month={month:02d}"
        / "data.parquet"
    )
