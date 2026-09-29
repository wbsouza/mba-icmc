"""Steps for lean_smoke_guard.feature — the pre-run data check (no Docker reached)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.cli import app
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/lean_smoke_guard.feature")


@pytest.fixture
def guard_ctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Clean ALGO_ env + an empty data root (no lean-data); no Docker needed."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ALGO_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    return {}


@given("a data root with no materialized EUR/USD lean-data")
def _empty_data_root(guard_ctx: dict[str, Any]) -> None:
    pass  # the fixture already points at an empty data root


@when("I run the lean-smoke command")
def _run(guard_ctx: dict[str, Any]) -> None:
    guard_ctx["cli"] = CliRunner().invoke(app, ["lean-smoke"])


@then("it exits with code 2")
def _exit_2(guard_ctx: dict[str, Any]) -> None:
    assert guard_ctx["cli"].exit_code == 2, guard_ctx["cli"].output


@then("the error tells me to run materialize first")
def _materialize_hint(guard_ctx: dict[str, Any]) -> None:
    assert "materialize" in guard_ctx["cli"].output