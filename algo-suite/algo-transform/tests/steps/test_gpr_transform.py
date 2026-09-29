"""Step definitions for gpr_transform.feature."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest
from algo_transform.cli import app
from algo_transform.readers.gpr import event_path, raw_path
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/gpr_transform.feature")

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


@given("a writable data root")
def _writable(context: dict[str, object]) -> None:
    assert _root(context).is_dir()


@given("a raw GPR file with rows for periods 2015-02 through 2015-04")
def _raw_gpr(context: dict[str, object]) -> None:
    path = raw_path(_root(context))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("period,gpr\n2015-02,91.4\n2015-03,92.0\n2015-04,93.5\n")


@given("no raw GPR file on disk")
def _no_raw_gpr(context: dict[str, object]) -> None:
    assert not raw_path(_root(context)).exists()


@given("a prior event partition exists for gpr")
def _prior_gpr(context: dict[str, object]) -> None:
    import pyarrow as pa

    path = event_path(_root(context))
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({"gpr": [91.4]}), path)


@when('I transform "gpr"')
def _transform_gpr(context: dict[str, object]) -> None:
    context["result"] = runner.invoke(app, ["run", "--source", "gpr"])


@then("an event Parquet partition exists at parquet/events/gpr")
def _partition_exists(context: dict[str, object]) -> None:
    assert event_path(_root(context)).is_file()


@then("it contains one row per period in the raw file")
def _row_count(context: dict[str, object]) -> None:
    assert pq.read_table(event_path(_root(context))).num_rows == 3


@then("the run exits 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert context["result"].exit_code == 0  # type: ignore[attr-defined]


@then("no event Parquet partition exists at parquet/events/gpr")
def _partition_absent(context: dict[str, object]) -> None:
    assert not event_path(_root(context)).exists()


@then("the report says the input is missing")
def _missing(context: dict[str, object]) -> None:
    assert "missing" in context["result"].stdout.lower()  # type: ignore[attr-defined]


@then("the run exits non-zero")
def _exit_nonzero(context: dict[str, object]) -> None:
    assert context["result"].exit_code != 0  # type: ignore[attr-defined]


@then("the report status is SKIPPED")
def _skipped(context: dict[str, object]) -> None:
    assert "skipped" in context["result"].stdout.lower()  # type: ignore[attr-defined]
