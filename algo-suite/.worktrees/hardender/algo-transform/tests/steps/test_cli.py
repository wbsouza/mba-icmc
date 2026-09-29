"""Step definitions for cli.feature (Typer CliRunner wiring)."""

from __future__ import annotations

from math import ceil
from pathlib import Path

import pytest
from algo_transform.cli import app
from algo_transform.readers.gdelt import expected_slots, raw_path
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/cli.feature")

runner = CliRunner()


@given("a writable data root")
def _writable(
    context: dict[str, object], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ALGO_DATA_ROOT", str(tmp_path))
    context["data_root"] = tmp_path


@given("a GDELT coverage series where 2015-05 through 2015-07 each cover at least 80% of the month")
def _gdelt_coverage_series(context: dict[str, object]) -> None:
    root = context["data_root"]
    assert isinstance(root, Path)
    for year, month in ((2015, 5), (2015, 6), (2015, 7)):
        slots = expected_slots(year, month)
        for slot in slots[: ceil(len(slots) * 0.8)]:
            path = raw_path(root, slot)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"")


@when(parsers.parse('I invoke the CLI with "{args}"'))
def _invoke(context: dict[str, object], args: str) -> None:
    context["result"] = runner.invoke(app, args.split())


@when(parsers.parse('I run "{args}"'))
def _run(context: dict[str, object], args: str) -> None:
    context["result"] = runner.invoke(app, ["run", *args.split()])


def _result(context: dict[str, object]):  # type: ignore[no-untyped-def]
    return context["result"]


@then("the run exits 0")
def _exit_zero(context: dict[str, object]) -> None:
    assert _result(context).exit_code == 0


@then("the run exits non-zero")
def _exit_nonzero(context: dict[str, object]) -> None:
    assert _result(context).exit_code != 0


@then("the output is non-empty")
def _non_empty(context: dict[str, object]) -> None:
    assert _result(context).stdout.strip()


@then(parsers.parse('the output contains "{needle}"'))
def _contains(context: dict[str, object], needle: str) -> None:
    assert needle in _result(context).stdout


@then(parsers.parse('the output contains case-insensitively "{needle}"'))
def _contains_ci(context: dict[str, object], needle: str) -> None:
    assert needle in _result(context).stdout.lower()


@then(parsers.parse('the output mentions a valid month range "{a}" or "{b}"'))
def _contains_either(context: dict[str, object], a: str, b: str) -> None:
    stdout = _result(context).stdout
    assert a in stdout or b in stdout


@then(parsers.parse('the output reports "{needle}" exactly {count:d} times'))
def _contains_count(context: dict[str, object], needle: str, count: int) -> None:
    assert _result(context).stdout.count(needle) == count  # one line per month


@then(parsers.parse('the output states the selected window "{window}"'))
def _selected_window(context: dict[str, object], window: str) -> None:
    assert window in _result(context).stdout


@then("the coverage matrix is written to parquet/_meta/coverage.parquet")
def _coverage_matrix_written(context: dict[str, object]) -> None:
    root = context["data_root"]
    assert isinstance(root, Path)
    assert (root / "parquet" / "_meta" / "coverage.parquet").is_file()


@then("a coverage-matrix figure is written")
def _coverage_figure_written(context: dict[str, object]) -> None:
    root = context["data_root"]
    assert isinstance(root, Path)
    assert (root / "parquet" / "_meta" / "coverage-matrix.pdf").is_file()
