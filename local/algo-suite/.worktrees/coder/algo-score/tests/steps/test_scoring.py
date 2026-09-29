"""Step definitions for scoring.feature."""

from __future__ import annotations

import shlex
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from algo_score.cli import app
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/scoring.feature")

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


def _article_path(context: dict[str, object]) -> Path:
    return _root(context) / "parquet" / "news" / "gdelt" / "year=2020" / "month=01" / "data.parquet"


def _sentiment_path(context: dict[str, object]) -> Path:
    return (
        _root(context) / "parquet" / "sentiment" / "lm" / "year=2020" / "month=01" / "data.parquet"
    )


def _article_score_path(context: dict[str, object]) -> Path:
    return (
        _root(context)
        / "parquet"
        / "sentiment"
        / "lm_articles"
        / "year=2020"
        / "month=01"
        / "data.parquet"
    )


def _write_articles(context: dict[str, object], rows: list[dict[str, object]]) -> None:
    path = _article_path(context)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)


def _default_articles() -> list[dict[str, object]]:
    minute = datetime(2020, 1, 5, 12, 0, tzinfo=UTC)
    return [
        {"id": "a1", "text": "ECB reports strong profit gains for the euro", "publish_ts": minute},
        {
            "id": "a2",
            "text": "Federal Reserve sees weak loss risks for dollar",
            "publish_ts": minute,
        },
        {"id": "a3", "text": "BOJ policy statement", "publish_ts": minute},
    ]


def _run_lm(context: dict[str, object], *extra: str) -> None:
    context["result"] = runner.invoke(
        app, ["--scorer", "lm", "--source", "gdelt", "--month", "2020-01", *extra]
    )


def _sentiment_table(context: dict[str, object]) -> pa.Table:
    return pq.read_table(_sentiment_path(context))


def _article_score_table(context: dict[str, object]) -> pa.Table:
    return pq.read_table(_article_score_path(context))


@given("news articles with id, text, and UTC publish_ts")
def _articles(context: dict[str, object]) -> None:
    _write_articles(context, _default_articles())


@given("a minute bucket with no articles")
def _empty_minute(context: dict[str, object]) -> None:
    assert _article_path(context).exists()


@given("a fixed seed and a fixed model_version")
def _fixed_seed() -> None:
    """Document that the scorer is deterministic and needs no external seed."""
    pass


@given("an article already scored at the current model_version")
def _article_already_scored(context: dict[str, object]) -> None:
    _run_lm(context)
    assert context["result"].exit_code == 0  # type: ignore[attr-defined]


@given("articles scored at model_version v1")
def _articles_scored_v1(context: dict[str, object]) -> None:
    _run_lm(context, "--model-version", "v1")
    assert context["result"].exit_code == 0  # type: ignore[attr-defined]


@given("an article whose text is not English")
def _non_english_article(context: dict[str, object]) -> None:
    rows = _default_articles()
    rows.append(
        {
            "id": "fr1",
            "text": "défaillance économique sévère",
            "publish_ts": datetime(2020, 1, 5, 12, 1, tzinfo=UTC),
        }
    )
    _write_articles(context, rows)


@given("a headline mentioning two currencies with opposite tone")
def _ambiguous_headline(context: dict[str, object]) -> None:
    _write_articles(
        context,
        [
            {
                "id": "amb1",
                "text": "ECB gains as Federal Reserve faces dollar loss risk",
                "publish_ts": datetime(2020, 1, 5, 12, 0, tzinfo=UTC),
            }
        ],
    )


@given("an article scored with polarity and confidence")
def _one_scored_article(context: dict[str, object]) -> None:
    _write_articles(
        context,
        [
            {
                "id": "late1",
                "text": "ECB reports strong profit gains",
                "publish_ts": datetime(2020, 1, 5, 22, 0, tzinfo=UTC),
            }
        ],
    )


@given("its minute bucket has no corresponding price bar")
def _price_grid_without_article_minute(context: dict[str, object]) -> None:
    path = _root(context) / "parquet" / "price_minutes" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table({"timestamp": [datetime(2020, 1, 5, 12, 0, tzinfo=UTC)]}),
        path,
    )


@when(parsers.re(r'I run "(?P<command>[^"]+)"'))
def _run_command(context: dict[str, object], command: str) -> None:
    args = shlex.split(command)
    assert args[0] == "algo-score"
    context["result"] = runner.invoke(app, args[1:])


@when("scoring runs")
def _scoring_runs(context: dict[str, object]) -> None:
    _run_lm(context)


@when(parsers.re(r'I score the same articles twice with "(?P<scorer>[^"]+)"'))
def _score_twice(context: dict[str, object], scorer: str) -> None:
    assert scorer == "lm"
    _run_lm(context)
    first = _article_score_table(context).to_pylist()
    _run_lm(context)
    context["first_scores"] = first
    context["second_scores"] = _article_score_table(context).to_pylist()


@when(parsers.re(r'I re-run scoring with "(?P<scorer>[^"]+)"'))
def _rerun_scoring(context: dict[str, object], scorer: str) -> None:
    assert scorer == "lm"
    _run_lm(context)


@when(parsers.re(r'I score at model_version (?P<version>v\d+) with "(?P<scorer>[^"]+)"'))
def _score_version(context: dict[str, object], version: str, scorer: str) -> None:
    assert scorer == "lm"
    _run_lm(context, "--model-version", version)


@when("features are aligned to price minutes")
def _align_to_price_minutes(context: dict[str, object]) -> None:
    _run_lm(context)


@then("each article has polarity in [-1,1] and confidence in [0,1]")
def _article_score_ranges(context: dict[str, object]) -> None:
    assert context["result"].exit_code == 0  # type: ignore[attr-defined]
    for row in _article_score_table(context).to_pylist():
        if row["polarity"] is not None:
            assert -1.0 <= row["polarity"] <= 1.0
        assert 0.0 <= row["confidence"] <= 1.0


@then("minute buckets aggregate net polarity and article count")
def _bucket_aggregates(context: dict[str, object]) -> None:
    rows = _sentiment_table(context).to_pylist()
    non_empty = [row for row in rows if row["n_articles"]]
    assert non_empty
    assert non_empty[0]["n_articles"] == 3


@then("the output records the model_version")
def _model_version_recorded(context: dict[str, object]) -> None:
    versions = set(_sentiment_table(context).column("model_version").to_pylist())
    assert versions
    assert "" not in versions


@then("that bucket has n_articles 0")
def _empty_bucket(context: dict[str, object]) -> None:
    rows = _sentiment_table(context).to_pylist()
    assert any(row["n_articles"] == 0 for row in rows)


@then("it is treated as ABSTAIN downstream, not an error")
def _abstain_not_error(context: dict[str, object]) -> None:
    assert context["result"].exit_code == 0  # type: ignore[attr-defined]


@then("the polarity and confidence are identical both times")
def _deterministic(context: dict[str, object]) -> None:
    assert context["first_scores"] == context["second_scores"]


@then("the cached score is used")
def _cached_score_used(context: dict[str, object]) -> None:
    assert "computed=0" in context["result"].stdout  # type: ignore[attr-defined]


@then("no new inference is performed for that article")
def _no_new_inference(context: dict[str, object]) -> None:
    assert "computed=0" in context["result"].stdout  # type: ignore[attr-defined]


@then("they are re-scored")
def _rescored(context: dict[str, object]) -> None:
    assert "computed=3" in context["result"].stdout  # type: ignore[attr-defined]


@then("no partition mixes v1 and v2 scores")
def _no_mixed_versions(context: dict[str, object]) -> None:
    assert set(_sentiment_table(context).column("model_version").to_pylist()) == {"v2"}


@then("it abstains rather than producing a spurious polarity")
def _non_english_abstains(context: dict[str, object]) -> None:
    rows = _article_score_table(context).to_pylist()
    row = next(item for item in rows if item["article_id"] == "fr1")
    assert row["abstained"] is True
    assert row["polarity"] is None


@then("the article is marked ambiguous (low confidence), not forced to a side")
def _ambiguous(context: dict[str, object]) -> None:
    row = _article_score_table(context).to_pylist()[0]
    assert row["ambiguous"] is True
    assert row["confidence"] < 1.0


@then("a transparent dictionary polarity is produced")
def _dictionary_polarity(context: dict[str, object]) -> None:
    assert any(row["polarity"] is not None for row in _article_score_table(context).to_pylist())


@then("it is stored under scorer=lm")
def _stored_under_lm(context: dict[str, object]) -> None:
    assert _sentiment_path(context).is_file()
    assert set(_sentiment_table(context).column("scorer").to_pylist()) == {"lm"}


@then("that bucket is excluded from the price-aligned output")
def _bucket_excluded(context: dict[str, object]) -> None:
    timestamps = _sentiment_table(context).column("timestamp").to_pylist()
    assert datetime(2020, 1, 5, 22, 0, tzinfo=UTC) not in timestamps


@then("it is not treated as an error")
def _not_error(context: dict[str, object]) -> None:
    assert context["result"].exit_code == 0  # type: ignore[attr-defined]


@then("the CLI exits non-zero")
def _cli_exits_nonzero(context: dict[str, object]) -> None:
    assert context["result"].exit_code != 0  # type: ignore[attr-defined]


@then(parsers.re(r'the output contains "(?P<text>[^"]+)"'))
def _output_contains(context: dict[str, object], text: str) -> None:
    assert text in context["result"].stdout  # type: ignore[attr-defined]
