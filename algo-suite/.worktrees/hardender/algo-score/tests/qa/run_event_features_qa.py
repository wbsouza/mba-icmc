"""Executable QA procedure for algo-score event features.

The companion procedure is ``spec-algo-score-event-features.qa.md``. This
script drives only the public ``algo-score events`` CLI and inspects the
operator-visible Parquet artifacts it writes.
"""

from __future__ import annotations

import os
import shutil
from datetime import UTC, date, datetime
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
    scratch = _clean_scratch("qa-score-event-features")
    original_env = os.environ.copy()
    try:
        _gpr_happy_path(scratch / "gpr-happy")
        _gpr_missing_day_carries_forward(scratch / "gpr-gap")
        _gpr_before_first_not_fabricated(scratch / "gpr-before-first")
        _gdelt_happy_path(scratch / "gdelt-happy")
        _gdelt_gap_and_before_first(scratch / "gdelt-gap-before-first")
        _unknown_kind_fails_fast(scratch / "unknown-kind")
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


def _gpr_happy_path(data_root: Path) -> None:
    """Verify daily GPR values expand to one minute-grid row per minute."""
    _write_gpr(data_root, [(date(2020, 1, 5), 10.0), (date(2020, 1, 6), 20.0)])
    result = _invoke(data_root, "gpr", "2020-01-05", "2020-01-06")
    table = _event_table(data_root, "gpr")
    _expect(result.exit_code == 0, "GPR happy path exits 0")
    _expect(table.num_rows == 2 * 24 * 60, "GPR output has one row per minute")
    _expect(_minute_value(table, "gpr", "2020-01-05T12:00:00+00:00") == 10.0, "day 1 value")
    _expect(_minute_value(table, "gpr", "2020-01-06T12:00:00+00:00") == 20.0, "day 2 value")
    _expect("gpr" in table.column_names, "GPR column is named gpr")
    _expect("sentiment" not in table.column_names, "GPR output is not named sentiment")


def _gpr_missing_day_carries_forward(data_root: Path) -> None:
    """Verify GPR gaps carry the last known value without interpolation."""
    _write_gpr(data_root, [(date(2020, 1, 5), 10.0), (date(2020, 1, 7), 30.0)])
    result = _invoke(data_root, "gpr", "2020-01-05", "2020-01-07")
    table = _event_table(data_root, "gpr")
    _expect(result.exit_code == 0, "GPR gap run exits 0")
    _expect(_minute_value(table, "gpr", "2020-01-06T12:00:00+00:00") == 10.0, "gap fill")
    _expect(_minute_value(table, "gpr", "2020-01-06T23:59:00+00:00") == 10.0, "no midpoint")


def _gpr_before_first_not_fabricated(data_root: Path) -> None:
    """Verify GPR has nulls before the first real observation."""
    _write_gpr(data_root, [(date(2020, 1, 6), 20.0), (date(2020, 1, 7), 30.0)])
    result = _invoke(data_root, "gpr", "2020-01-05", "2020-01-07")
    table = _event_table(data_root, "gpr")
    _expect(result.exit_code == 0, "GPR before-first run exits 0")
    value = _minute_value(table, "gpr", "2020-01-05T12:00:00+00:00")
    _expect(value is None, "GPR before first observation is null")


def _gdelt_happy_path(data_root: Path) -> None:
    """Verify GDELT Goldstein values aggregate to event_intensity."""
    _write_gdelt(
        data_root,
        [
            (date(2020, 1, 5), -4.0, 100.0),
            (date(2020, 1, 5), 2.0, 200.0),
            (date(2020, 1, 5), 6.0, 300.0),
            (date(2020, 1, 6), 3.0, -999.0),
        ],
    )
    result = _invoke(data_root, "gdelt", "2020-01-05", "2020-01-06")
    table = _event_table(data_root, "gdelt")
    expected = 1.3333333333333333
    _expect(result.exit_code == 0, "GDELT happy path exits 0")
    _expect(table.num_rows == 2 * 24 * 60, "GDELT output has one row per minute")
    _expect(
        _minute_value(table, "event_intensity", "2020-01-05T14:34:00+00:00") == expected,
        "GDELT daily mean uses Goldstein scale",
    )
    _expect("event_intensity" in table.column_names, "GDELT column is event_intensity")
    _expect("sentiment" not in table.column_names, "GDELT output is not sentiment")
    _expect("avg_tone" not in table.column_names, "avg_tone is not folded into output")


def _gdelt_gap_and_before_first(data_root: Path) -> None:
    """Verify GDELT mirrors GPR forward-fill and no-fabrication behavior."""
    _write_gdelt(
        data_root,
        [(date(2020, 1, 5), 10.0, 1.0), (date(2020, 1, 7), 30.0, 1.0)],
    )
    result = _invoke(data_root, "gdelt", "2020-01-05", "2020-01-07")
    table = _event_table(data_root, "gdelt")
    _expect(result.exit_code == 0, "GDELT gap run exits 0")
    _expect(
        _minute_value(table, "event_intensity", "2020-01-06T12:00:00+00:00") == 10.0,
        "GDELT gap carries forward",
    )

    before_root = data_root / "before-first"
    _write_gdelt(before_root, [(date(2020, 1, 6), 20.0, 1.0)])
    result = _invoke(before_root, "gdelt", "2020-01-05", "2020-01-07")
    table = _event_table(before_root, "gdelt")
    _expect(result.exit_code == 0, "GDELT before-first run exits 0")
    value = _minute_value(table, "event_intensity", "2020-01-05T12:00:00+00:00")
    _expect(value is None, "GDELT before first observation is null")


def _unknown_kind_fails_fast(data_root: Path) -> None:
    """Verify unknown event kinds name the known kind set."""
    result = _invoke(data_root, "nope", "2020-01-01", "2020-01-02")
    _expect(result.exit_code != 0, "unknown event kind exits non-zero")
    _expect("gdelt" in result.stdout and "gpr" in result.stdout, "known event kinds are named")


def _invoke(data_root: Path, kind: str, start: str, end: str) -> Result:
    """Invoke the event-feature CLI with an isolated data root."""
    data_root.mkdir(parents=True, exist_ok=True)
    return _RUNNER.invoke(
        app,
        ["events", "--kind", kind, "--from", start, "--to", end],
        env={"ALGO_DATA_ROOT": str(data_root)},
    )


def _write_gpr(data_root: Path, rows: list[tuple[date, float]]) -> None:
    """Write canonical GPR event input rows."""
    path = data_root / "parquet" / "events" / "gpr" / "data.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table({"period": [row[0] for row in rows], "gpr": [row[1] for row in rows]}),
        path,
    )


def _write_gdelt(data_root: Path, rows: list[tuple[date, float, float]]) -> None:
    """Write canonical GDELT event input rows."""
    path = data_root / "parquet" / "events" / "gdelt" / "year=2020" / "month=01" / "data.parquet"
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


def _event_table(data_root: Path, kind: str) -> pa.Table:
    """Read the January 2020 event-feature output table."""
    path = (
        data_root
        / "parquet"
        / "events"
        / "_features"
        / kind
        / "year=2020"
        / "month=01"
        / "data.parquet"
    )
    return pq.read_table(path)


def _minute_value(table: pa.Table, column: str, stamp: str) -> float | None:
    """Return a feature value for one UTC minute."""
    timestamps = table.column("timestamp").to_pylist()
    values = table.column(column).to_pylist()
    return values[timestamps.index(datetime.fromisoformat(stamp).astimezone(UTC))]


def _expect(condition: bool, message: str) -> None:
    """Raise a readable QA failure when a condition is false."""
    if not condition:
        raise QaFailure(message)


if __name__ == "__main__":
    main()
