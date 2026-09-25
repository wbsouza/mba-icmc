"""Executable CLI-only QA procedure for TD-28.

This script mirrors ``spec-td28-gdelt-ngrams-article-text.qa.md``. It deliberately
drives ``algo-transform`` through its command-line interface and inspects only
files the operator would see in the data root -- no direct calls into
``algo_transform.*`` Python modules.
"""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq


@dataclass(frozen=True)
class CommandResult:
    """A completed CLI invocation."""

    code: int
    output: str


def main() -> None:
    """Run the full TD-28 QA checklist."""
    scratch = worktree_root() / "tmp"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="algo-transform-qa-td28-", dir=scratch) as tmp:
        root = Path(tmp)
        run_happy_path(root / "happy")
        run_incomplete_and_corrupt(root / "bad")
        run_all_missing_month(root / "all-missing")
        run_cli_flags(root / "cli-flags")
        run_score_consumer_contract(root / "contract")
        run_unsupported_source(root / "unsupported")


def run_happy_path(root: Path) -> None:
    """QA doc section 1: decode + transform happy path, idempotent skip, rebuild."""
    populate_ngrams_month(root, 2020, 1, article_urls=3)
    result = run_cli(root, "run", "--source", "gdelt_ngrams", "--month", "2020-01")
    assert_success(result, "written")
    partition = news_partition_path(root, 2020, 1)
    require(partition.is_file(), "GDELT NGrams news partition was not written")
    require(partition.stat().st_size > 0, "GDELT NGrams news partition is empty on disk")
    table = pq.read_table(partition)
    require(table.num_rows == 3, f"Expected 3 reconstructed article rows, got {table.num_rows}")
    ids = table.column("id").to_pylist()
    texts = table.column("text").to_pylist()
    require(all(value for value in ids), "A reconstructed row has a null/empty url (id)")
    require(all(value for value in texts), "A reconstructed row has empty reconstructed text")
    require(
        table.column("publish_ts").null_count == 0,
        "A reconstructed row has a null publish timestamp",
    )
    first_mtime = partition.stat().st_mtime_ns

    result = run_cli(root, "run", "--source", "gdelt_ngrams", "--month", "2020-01")
    assert_success(result, "skipped")
    require(partition.stat().st_mtime_ns == first_mtime, "SKIPPED re-run rewrote the partition")

    result = run_cli(root, "run", "--source", "gdelt_ngrams", "--month", "2020-01", "--rebuild")
    assert_success(result, "written")
    require(partition.is_file(), "--rebuild did not leave a partition behind")


def run_incomplete_and_corrupt(root: Path) -> None:
    """QA doc section 2: a missing minute, then a corrupt minute, write nothing."""
    populate_ngrams_month(root, 2020, 1, article_urls=3)
    missing = ngrams_raw_path(root, 2020, 1, 5, 9, 0)
    missing.unlink()
    result = run_cli(root, "run", "--source", "gdelt_ngrams", "--month", "2020-01")
    assert_failure(result, "incomplete")
    partition_dir = news_partition_dir(root, 2020, 1)
    require(not partition_dir.exists(), "Incomplete month wrote a news partition")

    corrupt = missing
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_bytes(b"not-gzip-data")
    result = run_cli(root, "run", "--source", "gdelt_ngrams", "--month", "2020-01")
    assert_failure(result, "corrupt")
    require(str(corrupt) in result.output, "Corrupt-month output did not name the raw path")
    require(not partition_dir.exists(), "Corrupt month wrote a news partition")


def run_all_missing_month(root: Path) -> None:
    """QA doc section 3: a durable-all-MISSING month is WRITTEN as an empty partition."""
    populate_ngrams_month(root, 2020, 2, article_urls=0)
    result = run_cli(root, "run", "--source", "gdelt_ngrams", "--month", "2020-02")
    assert_success(result, "written")
    partition = news_partition_path(root, 2020, 2)
    require(partition.is_file(), "All-MISSING month did not write a partition")
    require(pq.read_table(partition).num_rows == 0, "All-MISSING month partition is not empty")


def run_cli_flags(root: Path) -> None:
    """QA doc section 4: --symbol is rejected; a bare run still hits the completeness gate."""
    result = run_cli(
        root, "run", "--source", "gdelt_ngrams", "--symbol", "EURUSD", "--month", "2020-01"
    )
    assert_failure(result, "--symbol")
    result = run_cli(root, "run", "--source", "gdelt_ngrams", "--month", "2020-01")
    assert_failure(result, "incomplete")


def run_score_consumer_contract(root: Path) -> None:
    """QA doc section 5: news Parquet columns match algo-score's NewsArticle contract."""
    populate_ngrams_month(root, 2020, 1, article_urls=3)
    result = run_cli(root, "run", "--source", "gdelt_ngrams", "--month", "2020-01")
    assert_success(result, "written")
    table = pq.read_table(news_partition_path(root, 2020, 1))
    names = set(table.column_names)
    for column in ("id", "text", "publish_ts"):
        require(column in names, f"algo-score contract column missing: {column}")


def run_unsupported_source(root: Path) -> None:
    """QA doc section 6: gdelt_ngrams joining the known sources didn't break this check."""
    result = run_cli(root, "run", "--source", "nope", "--symbol", "EURUSD", "--month", "2020-01")
    assert_failure(result, "dukascopy")


def run_cli(root: Path, *args: str) -> CommandResult:
    """Run ``algo-transform`` through the installed console script."""
    env = os.environ.copy()
    env["ALGO_DATA_ROOT"] = str(root)
    completed = subprocess.run(
        ["uv", "run", "algo-transform", *args],
        cwd=algo_suite_root(),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return CommandResult(code=completed.returncode, output=completed.stdout)


def populate_ngrams_month(root: Path, year: int, month: int, *, article_urls: int) -> None:
    """Write a complete raw NGrams month: every minute a MISSING marker except one.

    When ``article_urls`` is 0, every minute (including 14:34) is a 0-byte marker
    -- the durable-all-MISSING case. Otherwise minute 14:34 on day 2 carries
    ``article_urls`` URLs' worth of real ngram fragments.
    """
    import calendar

    days = calendar.monthrange(year, month)[1]
    article_minute = (2, 14, 34) if article_urls > 0 and days >= 2 else None
    for day in range(1, days + 1):
        for hour in range(24):
            for minute in range(60):
                path = ngrams_raw_path(root, year, month, day, hour, minute)
                path.parent.mkdir(parents=True, exist_ok=True)
                if article_minute == (day, hour, minute):
                    path.write_bytes(ngrams_payload(article_urls))
                else:
                    path.write_bytes(b"")


def ngrams_payload(url_count: int) -> bytes:
    """Build a real-format gzip line-delimited-JSON NGrams payload for N URLs.

    Same fragment shape as tests/steps/test_gdelt_ngrams_decode.py's fixtures,
    verified against the real gdeltnews reconstruction library.
    """
    records: list[dict[str, str]] = []
    for index in range(url_count):
        url = f"https://example.test/qa-td28-article-{index}"
        records += [
            _fragment(url, "hello world", 0, post="example"),
            _fragment(url, "world example", 6, pre="hello", post="text"),
            _fragment(url, "example text", 12, pre="world"),
        ]
    lines = "\n".join(json.dumps(record) for record in records) + "\n"
    return gzip.compress(lines.encode("utf-8"))


def _fragment(url: str, ngram: str, pos: int, pre: str = "", post: str = "") -> dict[str, str]:
    return {
        "date": "20200102143400",
        "ngram": ngram,
        "lang": "en",
        "type": "1",
        "pos": str(pos),
        "pre": pre,
        "post": post,
        "url": url,
    }


def ngrams_raw_path(root: Path, year: int, month: int, day: int, hour: int, minute: int) -> Path:
    """Return the raw GDELT NGrams minute path (must match algo_download's convention)."""
    stamp = f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}00"
    return (
        root
        / "raw"
        / "gdelt_ngrams"
        / f"{year:04d}"
        / f"{month:02d}"
        / f"{day:02d}"
        / f"{stamp}.webngrams.json.gz"
    )


def news_partition_dir(root: Path, year: int, month: int) -> Path:
    """Return the news Parquet partition's containing directory."""
    return root / "parquet" / "news" / "gdelt" / f"year={year:04d}" / f"month={month:02d}"


def news_partition_path(root: Path, year: int, month: int) -> Path:
    """Return the canonical GDELT news Parquet file path."""
    return news_partition_dir(root, year, month) / "data.parquet"


def assert_success(result: CommandResult, needle: str) -> None:
    """Assert a successful command whose output contains ``needle``."""
    require(result.code == 0, f"Expected success, got {result.code}:\n{result.output}")
    require(needle.lower() in result.output.lower(), f"Output missing {needle!r}:\n{result.output}")


def assert_failure(result: CommandResult, needle: str) -> None:
    """Assert a failing command whose output contains ``needle``."""
    require(result.code != 0, f"Expected failure, got success:\n{result.output}")
    require(needle.lower() in result.output.lower(), f"Output missing {needle!r}:\n{result.output}")


def require(condition: bool, message: str) -> None:
    """Raise an assertion failure with ``message`` when ``condition`` is false."""
    if not condition:
        raise AssertionError(message)


def algo_suite_root() -> Path:
    """Return the algo-suite workspace root."""
    return Path(__file__).resolve().parents[3]


def worktree_root() -> Path:
    """Return the assigned SwarmForge worktree root."""
    return Path(__file__).resolve().parents[4]


if __name__ == "__main__":
    main()
