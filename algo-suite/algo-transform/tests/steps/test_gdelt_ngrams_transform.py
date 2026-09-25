"""Step definitions for gdelt_ngrams_transform.feature."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from algo_score.scorers.models import NewsArticle
from algo_transform.cli import app
from algo_transform.readers.gdelt_ngrams import (
    GdeltNgramsMinute,
    expected_minutes,
    news_path,
    raw_path,
)
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/gdelt_ngrams_transform.feature")

runner = CliRunner()


@pytest.fixture
def context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Per-scenario mutable context."""
    monkeypatch.setenv("ALGO_DATA_ROOT", str(tmp_path))
    return {"data_root": tmp_path}


def _root(context: dict[str, object]) -> Path:
    root = context["data_root"]
    assert isinstance(root, Path)
    return root


def _article_payload() -> bytes:
    """Build one valid GDELT NGrams payload with real reconstructible article data."""
    records = [
        {"date": "20200102143400", "ngram": "hello world", "lang": "en", "type": "1",
         "pos": "0", "pre": "", "post": "example", "url": "https://example.com/a"},
        {"date": "20200102143400", "ngram": "world example", "lang": "en", "type": "1",
         "pos": "6", "pre": "hello", "post": "text", "url": "https://example.com/a"},
        {"date": "20200102143400", "ngram": "example text", "lang": "en", "type": "1",
         "pos": "12", "pre": "world", "post": "", "url": "https://example.com/a"},
    ]
    lines = "\n".join(json.dumps(r) for r in records) + "\n"
    return gzip.compress(lines.encode("utf-8"))


def _minute(date: str, time: str) -> GdeltNgramsMinute:
    year, month, day = (int(part) for part in date.split("-"))
    hour, minute = (int(part) for part in time.split(":"))
    return GdeltNgramsMinute(year=year, month=month, day=day, hour=hour, minute=minute)


@given("a writable data root")
def _writable(context: dict[str, object]) -> None:
    assert _root(context).is_dir()


@given(parsers.parse(
    "a complete raw GDELT NGrams month for {spec} with article data in minute {date} {time}"
))
def _complete_month(context: dict[str, object], spec: str, date: str, time: str) -> None:
    root = _root(context)
    year, month = (int(part) for part in spec.split("-"))
    for minute in expected_minutes(year, month):
        path = raw_path(root, minute)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    raw_path(root, _minute(date, time)).write_bytes(_article_payload())


@given(parsers.parse(
    "a complete raw GDELT NGrams month for {spec} where every minute is a durable MISSING marker"
))
def _all_missing_month(context: dict[str, object], spec: str) -> None:
    root = _root(context)
    year, month = (int(part) for part in spec.split("-"))
    for minute in expected_minutes(year, month):
        path = raw_path(root, minute)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")


@given(parsers.parse("the raw minute {date} {time} is removed"))
def _remove_minute(context: dict[str, object], date: str, time: str) -> None:
    raw_path(_root(context), _minute(date, time)).unlink()


@given(parsers.parse("the raw minute {date} {time} is corrupt"))
def _corrupt_minute(context: dict[str, object], date: str, time: str) -> None:
    raw_path(_root(context), _minute(date, time)).write_bytes(b"not-gzip-data")


@given("a prior complete news partition exists for gdelt_ngrams 2020-01")
def _prior_partition(context: dict[str, object]) -> None:
    path = news_path(_root(context), 2020, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({"id": ["x"], "text": ["y"], "publish_ts": [0]}), path)


@when(parsers.parse('I transform "{source}" for "{spec}"'))
def _transform(context: dict[str, object], source: str, spec: str) -> None:
    context["result"] = runner.invoke(app, ["run", "--source", source, "--month", spec])


@then("a news Parquet partition exists at parquet/news/gdelt for 2020-01")
def _partition_exists(context: dict[str, object]) -> None:
    assert news_path(_root(context), 2020, 1).is_file()


@then("it contains at least one news row")
def _has_row(context: dict[str, object]) -> None:
    table = pq.read_table(news_path(_root(context), 2020, 1))
    assert table.num_rows >= 1


@then("its rows validate as algo-score NewsArticle records")
def _news_article_contract(context: dict[str, object]) -> None:
    table = pq.read_table(news_path(_root(context), 2020, 1))
    for row in table.to_pylist():
        NewsArticle.model_validate(row)


@then("it contains zero news rows")
def _zero_rows(context: dict[str, object]) -> None:
    table = pq.read_table(news_path(_root(context), 2020, 1))
    assert table.num_rows == 0


@then("it has the id, text, and publish_ts columns")
def _has_article_schema(context: dict[str, object]) -> None:
    # `news_path` is a single file (per `_partition_exists` above); pyarrow still infers
    # hive `year=`/`month=` partition columns from its ancestor directories on read, so
    # this checks the real article columns are present, not that the column list is
    # exactly these three.
    table = pq.read_table(news_path(_root(context), 2020, 1))
    assert {"id", "text", "publish_ts"} <= set(table.column_names), table.column_names


@then("the run exits 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert context["result"].exit_code == 0  # type: ignore[attr-defined]


@then("no news Parquet partition exists at parquet/news/gdelt for 2020-01")
def _partition_absent(context: dict[str, object]) -> None:
    assert not news_path(_root(context), 2020, 1).exists()


@then("the report says the month is incomplete")
def _incomplete(context: dict[str, object]) -> None:
    assert "incomplete" in context["result"].stdout.lower()  # type: ignore[attr-defined]


@then("the report says the month is corrupt")
def _corrupt(context: dict[str, object]) -> None:
    assert "corrupt" in context["result"].stdout.lower()  # type: ignore[attr-defined]


@then("the report names the corrupt minute's raw path")
def _corrupt_path(context: dict[str, object]) -> None:
    stdout = context["result"].stdout  # type: ignore[attr-defined]
    assert "20200105090000.webngrams.json.gz" in stdout


@then("the report status is SKIPPED")
def _skipped(context: dict[str, object]) -> None:
    assert "skipped" in context["result"].stdout.lower()  # type: ignore[attr-defined]


@when(parsers.parse("I compute expected minutes for {year:d}-{month:d}"))
def _compute_expected_minutes(context: dict[str, object], year: int, month: int) -> None:
    context["minutes"] = expected_minutes(year, month)


@then(parsers.parse("there are {count:d} expected minutes"))
def _minute_count(context: dict[str, object], count: int) -> None:
    minutes = context["minutes"]
    assert isinstance(minutes, list)
    assert len(minutes) == count


@then(parsers.parse("the last expected day is {last_day:d}"))
def _last_day(context: dict[str, object], last_day: int) -> None:
    minutes = context["minutes"]
    assert isinstance(minutes, list)
    assert max(m.day for m in minutes) == last_day
