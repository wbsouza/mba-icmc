"""Executable QA procedure for the Loughran-McDonald scorer.

The companion procedure is ``spec-algo-score-lm-scorer.qa.md``. This script
drives the public ``algo-score --scorer lm`` CLI and inspects the output
partitions that the operator would consume.
"""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from algo_score.cli import app
from click.testing import Result
from typer.testing import CliRunner

_RUNNER = CliRunner()


class QaFailure(AssertionError):
    """Raised when an executable QA check fails."""


def main() -> None:
    """Run the complete automated QA procedure."""
    scratch = _clean_scratch("qa-score-lm")
    original_env = os.environ.copy()
    try:
        _happy_path_polarity_confidence_and_bucketing(scratch / "happy")
        _empty_batch_abstains(scratch / "empty")
        _deterministic_scoring(scratch / "deterministic")
        _cache_hit_and_model_version_bump(scratch / "cache")
        _non_english_abstains(scratch / "non-english")
        _multi_currency_ambiguity_and_routing(scratch / "multi-currency")
        _article_without_currency_is_dropped(scratch / "dropped")
        _missing_price_bar_is_excluded(scratch / "price-grid")
        _output_is_namespaced_for_lm(scratch / "namespace")
        _cli_validation()
    finally:
        os.environ.clear()
        os.environ.update(original_env)


def _clean_scratch(name: str) -> Path:
    """Create an empty worktree-local scratch directory for this QA run."""
    root = Path(__file__).resolve().parents[4] / "tmp" / name
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def _happy_path_polarity_confidence_and_bucketing(data_root: Path) -> None:
    """Verify article scores, minute buckets, and model metadata."""
    _write_articles(data_root, _default_articles())
    result = _invoke(data_root)
    article_rows = _table(data_root, "lm_articles").to_pylist()
    sentiment_rows = _table(data_root, "lm").to_pylist()
    non_empty = [row for row in sentiment_rows if row["n_articles"]]
    _expect(result.exit_code == 0, "happy path exits 0")
    _expect(all(_score_in_range(row) for row in article_rows), "scores are bounded")
    _expect(non_empty and non_empty[0]["n_articles"] == 3, "minute bucket aggregates articles")
    _expect(all(row["model_version"] for row in sentiment_rows), "model_version is recorded")


def _empty_batch_abstains(data_root: Path) -> None:
    """Verify empty minutes are emitted as abstaining zero-count buckets."""
    _write_articles(data_root, _default_articles())
    result = _invoke(data_root)
    rows = _table(data_root, "lm").to_pylist()
    _expect(result.exit_code == 0, "empty-bucket run exits 0")
    _expect(any(row["n_articles"] == 0 for row in rows), "an empty bucket has n_articles=0")


def _deterministic_scoring(data_root: Path) -> None:
    """Verify identical input produces identical article score rows."""
    _write_articles(data_root, _default_articles())
    first = _invoke(data_root)
    first_rows = _table(data_root, "lm_articles").to_pylist()
    second = _invoke(data_root)
    second_rows = _table(data_root, "lm_articles").to_pylist()
    _expect(first.exit_code == 0 and second.exit_code == 0, "deterministic runs exit 0")
    _expect(first_rows == second_rows, "article score rows are deterministic")


def _cache_hit_and_model_version_bump(data_root: Path) -> None:
    """Verify cache reuse and model-version partition freshness."""
    _write_articles(data_root, _default_articles())
    first = _invoke(data_root, model_version="v1")
    second = _invoke(data_root, model_version="v1")
    bumped = _invoke(data_root, model_version="v2")
    versions = set(_table(data_root, "lm").column("model_version").to_pylist())
    _expect(first.exit_code == 0 and second.exit_code == 0, "cache runs exit 0")
    _expect("computed=0" in second.stdout, "second run uses cached scores")
    _expect(bumped.exit_code == 0 and "computed=3" in bumped.stdout, "version bump recomputes")
    _expect(versions == {"v2"}, "latest output partition contains only v2")


def _non_english_abstains(data_root: Path) -> None:
    """Verify non-English text abstains rather than fabricating polarity."""
    rows = _default_articles()
    rows.append(
        {
            "id": "fr1",
            "text": "défaillance économique sévère",
            "publish_ts": datetime(2020, 1, 5, 12, 1, tzinfo=UTC),
        }
    )
    _write_articles(data_root, rows)
    result = _invoke(data_root)
    row = _article_by_id(data_root, "fr1")
    _expect(result.exit_code == 0, "non-English run exits 0")
    _expect(row["abstained"] is True and row["polarity"] is None, "non-English abstains")


def _multi_currency_ambiguity_and_routing(data_root: Path) -> None:
    """Verify ambiguous currency text is flagged and routed to both currencies."""
    _write_articles(
        data_root,
        [
            {
                "id": "amb1",
                "text": "ECB gains as Federal Reserve faces dollar loss risk",
                "publish_ts": _minute(),
            },
            {"id": "ecb1", "text": "ECB raising rates", "publish_ts": _minute()},
            {"id": "fomc1", "text": "FOMC decision", "publish_ts": _minute()},
            {"id": "boj1", "text": "BOJ intervention", "publish_ts": _minute()},
        ],
    )
    result = _invoke(data_root)
    amb = _article_by_id(data_root, "amb1")
    currencies = {row["entity"] for row in _table(data_root, "lm_currency").to_pylist()}
    symbols = {row["symbol"] for row in _table(data_root, "lm_symbol").to_pylist()}
    _expect(result.exit_code == 0, "multi-currency run exits 0")
    _expect(amb["ambiguous"] is True and amb["confidence"] < 1.0, "ambiguous row is flagged")
    _expect({"EUR", "USD", "JPY"} <= currencies, "ECB/FOMC/BOJ route to currencies")
    _expect({"EURUSD", "USDJPY"} <= symbols, "USD macro news feeds both configured pairs")


def _article_without_currency_is_dropped(data_root: Path) -> None:
    """Verify unrelated articles are counted as dropped, not raised as errors."""
    _write_articles(
        data_root,
        [
            {
                "id": "br1",
                "text": "Brazil-only story about local politics",
                "publish_ts": _minute(),
            }
        ],
    )
    result = _invoke(data_root)
    currency_rows = _table(data_root, "lm_currency").to_pylist()
    _expect(result.exit_code == 0, "drop run exits 0")
    _expect("dropped=1" in result.stdout, "dropped article is counted")
    _expect(currency_rows == [], "unattributable article is excluded from currency output")


def _missing_price_bar_is_excluded(data_root: Path) -> None:
    """Verify scored minutes with no matching price bar are absent, not failures."""
    _write_articles(
        data_root,
        [{"id": "late1", "text": "ECB reports strong profit gains", "publish_ts": _late_minute()}],
    )
    _write_price_minutes(data_root, [_minute()])
    result = _invoke(data_root)
    timestamps = _table(data_root, "lm").column("timestamp").to_pylist()
    _expect(result.exit_code == 0, "price-grid run exits 0")
    _expect(_late_minute() not in timestamps, "missing price-bar minute is excluded")


def _output_is_namespaced_for_lm(data_root: Path) -> None:
    """Verify LM output path and scorer column stay namespaced."""
    _write_articles(data_root, _default_articles())
    result = _invoke(data_root)
    table = _table(data_root, "lm")
    _expect(result.exit_code == 0, "namespace run exits 0")
    _expect(_partition_path(data_root, "lm").is_file(), "lm output partition exists")
    _expect(set(table.column("scorer").to_pylist()) == {"lm"}, "scorer column is lm")


def _cli_validation() -> None:
    """Verify invalid CLI argument combinations fail fast with useful text."""
    cases = [
        (["--scorer", "nope", "--source", "gdelt", "--month", "2020-01"], "unknown scorer"),
        (
            [
                "--scorer",
                "lm",
                "--source",
                "gdelt",
                "--month",
                "2020-01",
                "--from",
                "2020-01-01",
                "--to",
                "2020-01-05",
            ],
            "--month or",
        ),
        (["--scorer", "lm", "--source", "gdelt", "--month", "2020/01"], "expected YYYY-MM"),
        (["--scorer", "lm", "--source", "gdelt", "--month", "2020-13"], "must be 01-12"),
        (["--scorer", "lm", "--source", "gdelt"], "provide --month"),
        (
            ["--scorer", "lm", "--source", "gdelt", "--from", "2020/01/05", "--to", "2020-01-07"],
            "expected YYYY-MM-DD",
        ),
        (
            ["--scorer", "lm", "--source", "gdelt", "--from", "2020-01-07", "--to", "2020-01-05"],
            "is after",
        ),
    ]
    for args, expected in cases:
        result = _RUNNER.invoke(app, args)
        _expect(result.exit_code != 0, f"{args} exits non-zero")
        _expect(expected in result.stdout, f"{args} output contains {expected!r}")


def _invoke(data_root: Path, model_version: str = "lm-v1") -> Result:
    """Invoke the LM scorer CLI with an isolated data root."""
    data_root.mkdir(parents=True, exist_ok=True)
    return _RUNNER.invoke(
        app,
        [
            "--scorer",
            "lm",
            "--source",
            "gdelt",
            "--month",
            "2020-01",
            "--model-version",
            model_version,
        ],
        env={"ALGO_DATA_ROOT": str(data_root)},
    )


def _default_articles() -> list[dict[str, object]]:
    """Return a three-article fixture with positive, negative, and neutral text."""
    return [
        {
            "id": "a1",
            "text": "ECB reports strong profit gains for the euro",
            "publish_ts": _minute(),
        },
        {
            "id": "a2",
            "text": "Federal Reserve sees weak loss risks for dollar",
            "publish_ts": _minute(),
        },
        {"id": "a3", "text": "BOJ policy statement", "publish_ts": _minute()},
    ]


def _write_articles(data_root: Path, rows: list[dict[str, object]]) -> None:
    """Write synthetic article fixture rows."""
    path = data_root / "parquet" / "news" / "gdelt" / "year=2020" / "month=01" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)


def _write_price_minutes(data_root: Path, minutes: list[datetime]) -> None:
    """Write an optional price-minute grid."""
    path = data_root / "parquet" / "price_minutes" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({"timestamp": minutes}), path)


def _table(data_root: Path, dataset: str) -> pa.Table:
    """Read a sentiment output table."""
    return pq.read_table(_partition_path(data_root, dataset))


def _partition_path(data_root: Path, dataset: str) -> Path:
    """Return the January 2020 sentiment partition for one dataset."""
    return data_root / "parquet" / "sentiment" / dataset / "year=2020" / "month=01" / "data.parquet"


def _article_by_id(data_root: Path, article_id: str) -> dict[str, object]:
    """Return one article-score row by id."""
    rows = _table(data_root, "lm_articles").to_pylist()
    return next(row for row in rows if row["article_id"] == article_id)


def _score_in_range(row: dict[str, object]) -> bool:
    """Return whether a scored article row has bounded polarity/confidence."""
    polarity = row["polarity"]
    confidence = row["confidence"]
    assert isinstance(confidence, float)
    return (polarity is None or -1.0 <= polarity <= 1.0) and 0.0 <= confidence <= 1.0


def _minute() -> datetime:
    """Return the default fixture minute."""
    return datetime(2020, 1, 5, 12, 0, tzinfo=UTC)


def _late_minute() -> datetime:
    """Return a fixture minute absent from the test price grid."""
    return datetime(2020, 1, 5, 22, 0, tzinfo=UTC)


def _expect(condition: bool, message: str) -> None:
    """Raise a readable QA failure when a condition is false."""
    if not condition:
        raise QaFailure(message)


if __name__ == "__main__":
    main()
