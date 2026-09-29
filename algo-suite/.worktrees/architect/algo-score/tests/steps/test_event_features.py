"""Step definitions for event_features.feature."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from algo_score.cli import app
from algo_score.events import gdelt, gpr
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/event_features.feature")

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


def _feature_path(context: dict[str, object], source: str) -> Path:
    return (
        _root(context)
        / "parquet"
        / "events"
        / "_features"
        / source
        / "year=2020"
        / "month=01"
        / "data.parquet"
    )


def _input_path(context: dict[str, object], source: str) -> Path:
    if source == "gpr":
        return _root(context) / "parquet" / "events" / "gpr" / "data.parquet"
    return (
        _root(context) / "parquet" / "events" / "gdelt" / "year=2020" / "month=01" / "data.parquet"
    )


def _flat_gdelt_path(context: dict[str, object]) -> Path:
    return _root(context) / "parquet" / "events" / "gdelt" / "data.parquet"


def _write_gpr(context: dict[str, object], rows: list[tuple[date, float]]) -> None:
    path = _input_path(context, "gpr")
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table({"period": [row[0] for row in rows], "gpr": [row[1] for row in rows]}),
        path,
    )


def _write_gdelt(context: dict[str, object], rows: list[tuple[date, float, float]]) -> None:
    _write_gdelt_at(_input_path(context, "gdelt"), rows)


def _write_flat_gdelt(context: dict[str, object], rows: list[tuple[date, float, float]]) -> None:
    _write_gdelt_at(_flat_gdelt_path(context), rows)


def _write_gdelt_at(path: Path, rows: list[tuple[date, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table(
            {
                "global_event_id": list(range(1, len(rows) + 1)),
                "event_date": [row[0] for row in rows],
                "event_code": ["042"] * len(rows),
                "goldstein_scale": [row[1] for row in rows],
                "avg_tone": [row[2] for row in rows],
                "actor1_code": ["USA"] * len(rows),
                "actor2_code": ["EUR"] * len(rows),
                "num_mentions": [1] * len(rows),
                "num_sources": [1] * len(rows),
                "num_articles": [1] * len(rows),
                "source_url": ["https://example.test"] * len(rows),
            }
        ),
        path,
    )


def _write_daily_series(
    context: dict[str, object], source: str, rows: list[tuple[date, float]]
) -> None:
    if source == "gpr":
        _write_gpr(context, rows)
        return
    _write_gdelt(context, [(day, value, 99.0) for day, value in rows])


def _read_output(context: dict[str, object], source: str) -> pa.Table:
    return pq.read_table(_feature_path(context, source))


def _column_values(context: dict[str, object], source: str, column: str) -> list[float | None]:
    return _read_output(context, source).column(column).to_pylist()


def _timestamps(context: dict[str, object], source: str) -> list[datetime]:
    return _read_output(context, source).column("timestamp").to_pylist()


def _minute_value(
    context: dict[str, object], source: str, column: str, when_: datetime
) -> float | None:
    timestamps = _timestamps(context, source)
    values = _column_values(context, source, column)
    return values[timestamps.index(when_)]


@given("canonical event Parquet exists for gdelt and gpr")
def _canonical_inputs(context: dict[str, object]) -> None:
    _write_gpr(
        context,
        [
            (date(2020, 1, 5), 10.0),
            (date(2020, 1, 6), 20.0),
            (date(2020, 1, 7), 30.0),
        ],
    )
    _write_gdelt(
        context,
        [
            (date(2020, 1, 5), 1.0, -10.0),
            (date(2020, 1, 6), 2.0, 0.0),
            (date(2020, 1, 7), 3.0, 10.0),
        ],
    )


@given(parsers.re(r"a daily (?P<source>gpr|gdelt) series$"))
def _daily_series(context: dict[str, object], source: str) -> None:
    context["source"] = source
    _write_daily_series(
        context,
        source,
        [
            (date(2020, 1, 5), 10.0),
            (date(2020, 1, 6), 20.0),
            (date(2020, 1, 7), 30.0),
        ],
    )


@given(parsers.re(r"a daily (?P<source>gpr|gdelt) series with a missing day"))
def _daily_series_with_gap(context: dict[str, object], source: str) -> None:
    context["source"] = source
    _write_daily_series(
        context,
        source,
        [
            (date(2020, 1, 5), 10.0),
            (date(2020, 1, 7), 30.0),
        ],
    )


@given(parsers.re(r"a daily (?P<source>gpr|gdelt) series whose first observation is on day 2"))
def _daily_series_starts_day_2(context: dict[str, object], source: str) -> None:
    context["source"] = source
    _write_daily_series(
        context,
        source,
        [
            (date(2020, 1, 6), 20.0),
            (date(2020, 1, 7), 30.0),
        ],
    )


@given("GDELT events on 2020-01-05 with goldstein_scale -4.0, 2.0, and 6.0")
def _gdelt_goldstein_rows(context: dict[str, object]) -> None:
    context["source"] = "gdelt"
    _write_gdelt(
        context,
        [
            (date(2020, 1, 5), -4.0, 100.0),
            (date(2020, 1, 5), 2.0, 200.0),
            (date(2020, 1, 5), 6.0, 300.0),
        ],
    )


@given("flat GDELT events on 2020-01-05 with goldstein_scale -4.0, 2.0, and 6.0")
def _flat_gdelt_goldstein_rows(context: dict[str, object]) -> None:
    context["source"] = "gdelt"
    _input_path(context, "gdelt").unlink()
    _write_flat_gdelt(
        context,
        [
            (date(2020, 1, 5), -4.0, 100.0),
            (date(2020, 1, 5), 2.0, 200.0),
            (date(2020, 1, 5), 6.0, 300.0),
        ],
    )


@when("I build event features")
def _build_event_features(context: dict[str, object]) -> None:
    source = context["source"]
    assert isinstance(source, str)
    context["result"] = runner.invoke(
        app, ["events", "--kind", source, "--from", "2020-01-05", "--to", "2020-01-07"]
    )


@when(parsers.re(r'I build event features for unknown kind "(?P<kind>[^"]+)"'))
def _build_unknown_event_features(context: dict[str, object], kind: str) -> None:
    context["result"] = runner.invoke(
        app, ["events", "--kind", kind, "--from", "2020-01-01", "--to", "2020-01-02"]
    )


@when(parsers.re(r"I build event features through the (?P<source>gpr|gdelt) helper"))
def _build_through_source_helper(context: dict[str, object], source: str) -> None:
    builder = gpr.build if source == "gpr" else gdelt.build
    context["report"] = builder(_root(context), date(2020, 1, 5), date(2020, 1, 7))


@then(parsers.re(r"each minute carries the most recent prior daily (?P<column>[a-z_]+) value"))
def _forward_filled(context: dict[str, object], column: str) -> None:
    source = context["source"]
    assert isinstance(source, str)
    assert _minute_value(context, source, column, datetime(2020, 1, 5, 0, 0, tzinfo=UTC)) == 10.0
    assert _minute_value(context, source, column, datetime(2020, 1, 6, 12, 0, tzinfo=UTC)) == 20.0
    assert _minute_value(context, source, column, datetime(2020, 1, 7, 23, 59, tzinfo=UTC)) == 30.0


@then(
    parsers.re(r"minutes in the missing day carry the last known prior (?P<column>[a-z_]+) value")
)
def _gap_carries_forward(context: dict[str, object], column: str) -> None:
    source = context["source"]
    assert isinstance(source, str)
    assert _minute_value(context, source, column, datetime(2020, 1, 6, 12, 0, tzinfo=UTC)) == 10.0


@then("no value is interpolated between the surrounding days")
def _not_interpolated(context: dict[str, object]) -> None:
    source = context["source"]
    assert isinstance(source, str)
    column = "gpr" if source == "gpr" else "event_intensity"
    assert _minute_value(context, source, column, datetime(2020, 1, 6, 23, 59, tzinfo=UTC)) == 10.0


@then(parsers.re(r"minutes before day 2 have no (?P<column>[a-z_]+) value"))
def _before_first_is_null(context: dict[str, object], column: str) -> None:
    source = context["source"]
    assert isinstance(source, str)
    assert _minute_value(context, source, column, datetime(2020, 1, 5, 12, 0, tzinfo=UTC)) is None


@then("that absence is not fabricated as zero")
def _absence_not_zero(context: dict[str, object]) -> None:
    source = context["source"]
    assert isinstance(source, str)
    column = "gpr" if source == "gpr" else "event_intensity"
    values = [
        _minute_value(context, source, column, datetime(2020, 1, 5, 0, 0, tzinfo=UTC)),
        _minute_value(context, source, column, datetime(2020, 1, 5, 23, 59, tzinfo=UTC)),
    ]
    assert values == [None, None]


@then(parsers.re(r"every minute of 2020-01-05 carries event_intensity (?P<expected>-?\d+\.\d+)"))
def _golden_intensity(context: dict[str, object], expected: str) -> None:
    table = _read_output(context, "gdelt")
    values = table.column("event_intensity").to_pylist()[: 24 * 60]
    assert set(values) == {float(expected)}


@then("avg_tone is not folded into event_intensity")
def _avg_tone_not_used(context: dict[str, object]) -> None:
    table = _read_output(context, "gdelt")
    assert "avg_tone" not in table.column_names
    assert "sentiment" not in table.column_names
    assert "polarity" not in table.column_names


@then("the run exits non-zero")
def _exit_nonzero(context: dict[str, object]) -> None:
    assert context["result"].exit_code != 0  # type: ignore[attr-defined]


@then("the output names the known event feature kinds")
def _known_kinds(context: dict[str, object]) -> None:
    stdout = context["result"].stdout  # type: ignore[attr-defined]
    assert "gdelt" in stdout
    assert "gpr" in stdout
