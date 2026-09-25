"""Steps for experiment_run_guard.feature — the pre-run spec-path check (no Docker reached)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from algo_backtest.cli import app
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/experiment_run_guard.feature")


@pytest.fixture
def guard_ctx(tmp_path: Path) -> dict[str, Any]:
    return {"spec_path": tmp_path / "does-not-exist.yaml"}


@given("a --spec path that does not exist")
def _missing_spec(guard_ctx: dict[str, Any]) -> None:
    pass  # the fixture's path is never written


@when("I run the experiment-run command")
def _run(guard_ctx: dict[str, Any]) -> None:
    guard_ctx["cli"] = CliRunner().invoke(
        app, ["experiment", "run", "--spec", str(guard_ctx["spec_path"])]
    )


@then("it exits with code 2")
def _exit_2(guard_ctx: dict[str, Any]) -> None:
    assert guard_ctx["cli"].exit_code == 2, guard_ctx["cli"].output


@then("the error names the missing spec path")
def _names_path(guard_ctx: dict[str, Any]) -> None:
    assert str(guard_ctx["spec_path"]) in guard_ctx["cli"].output
