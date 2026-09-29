"""Step definitions for gdelt_transform.feature."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from algo_transform.cli import app
from algo_transform.readers.gdelt import GdeltSlot, event_path, expected_slots, raw_path
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/gdelt_transform.feature")

runner = CliRunner()


@pytest.fixture
def context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Per-scenario mutable context."""
    monkeypatch.setenv("ALGO_DATA_ROOT", str(tmp_path))
    return {"data_root": tmp_path}


def _root(context: dict[str, object]) -> Path:
    """Return the scenario data root."""
    root = context["data_root"]
    assert isinstance(root, Path)
    return root


def _event_payload() -> bytes:
    """Build one valid GDELT Events zip."""
    row = [""] * 61
    row[0] = "1"
    row[1] = "20200102"
    row[5] = "USA"
    row[15] = "IRN"
    row[26] = "042"
    row[30] = "3.5"
    row[31] = "7"
    row[32] = "2"
    row[33] = "5"
    row[34] = "-1.25"
    row[60] = "https://example.test/1"
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("events.export.CSV", "\t".join(row))
    return buffer.getvalue()


@given("a writable data root")
def _writable(context: dict[str, object]) -> None:
    assert _root(context).is_dir()


@given(parsers.parse("a complete raw GDELT month for {spec} with event data in slot {date} {time}"))
def _complete_month(context: dict[str, object], spec: str, date: str, time: str) -> None:
    root = _root(context)
    year, month = (int(part) for part in spec.split("-"))
    for slot in expected_slots(year, month):
        path = raw_path(root, slot)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    year_s, month_s, day_s = (int(part) for part in date.split("-"))
    hour, minute = (int(part) for part in time.split(":"))
    slot = GdeltSlot(year=year_s, month=month_s, day=day_s, hour=hour, minute=minute)
    raw_path(root, slot).write_bytes(_event_payload())


@given(parsers.parse("the raw slot {date} {time} is removed"))
def _remove_slot(context: dict[str, object], date: str, time: str) -> None:
    year, month, day = (int(part) for part in date.split("-"))
    hour, minute = (int(part) for part in time.split(":"))
    slot = GdeltSlot(year=year, month=month, day=day, hour=hour, minute=minute)
    raw_path(_root(context), slot).unlink()


@given(parsers.parse("the raw slot {date} {time} is corrupt"))
def _corrupt_slot(context: dict[str, object], date: str, time: str) -> None:
    year, month, day = (int(part) for part in date.split("-"))
    hour, minute = (int(part) for part in time.split(":"))
    slot = GdeltSlot(year=year, month=month, day=day, hour=hour, minute=minute)
    raw_path(_root(context), slot).write_bytes(b"not-a-zip")


@given("a prior complete event partition exists for gdelt 2020-01")
def _prior_partition(context: dict[str, object]) -> None:
    path = event_path(_root(context), 2020, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa_table({"global_event_id": [1]}), path)


@when(parsers.parse('I transform "{source}" for "{spec}"'))
def _transform(context: dict[str, object], source: str, spec: str) -> None:
    context["result"] = runner.invoke(app, ["run", "--source", source, "--month", spec])


@then("an event Parquet partition exists at parquet/events/gdelt for 2020-01")
def _partition_exists(context: dict[str, object]) -> None:
    assert event_path(_root(context), 2020, 1).is_file()


@then("it contains at least one event row")
def _has_event(context: dict[str, object]) -> None:
    table = pq.read_table(event_path(_root(context), 2020, 1))
    assert table.num_rows >= 1


@then("the run exits 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert context["result"].exit_code == 0  # type: ignore[attr-defined]


@then("no event Parquet partition exists at parquet/events/gdelt for 2020-01")
def _partition_absent(context: dict[str, object]) -> None:
    assert not event_path(_root(context), 2020, 1).exists()


@then("the report says the month is incomplete")
def _incomplete(context: dict[str, object]) -> None:
    assert "incomplete" in context["result"].stdout.lower()  # type: ignore[attr-defined]


@then("the report says the month is corrupt")
def _corrupt(context: dict[str, object]) -> None:
    assert "corrupt" in context["result"].stdout.lower()  # type: ignore[attr-defined]


@then("the report names the corrupt slot's raw path")
def _corrupt_path(context: dict[str, object]) -> None:
    stdout = context["result"].stdout  # type: ignore[attr-defined]
    assert "20200105090000.export.CSV.zip" in stdout


@then("the report status is SKIPPED")
def _skipped(context: dict[str, object]) -> None:
    assert "skipped" in context["result"].stdout.lower()  # type: ignore[attr-defined]


def pa_table(values: dict[str, list[int]]):  # type: ignore[no-untyped-def]
    """Build a tiny Arrow table without importing pyarrow at module top for one helper."""
    import pyarrow as pa

    return pa.table(values)
