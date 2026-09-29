"""Steps for cli_results_dir.feature — pure-logic coverage of `_fresh_results_dir`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from algo_backtest.cli import _fresh_results_dir
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/cli_results_dir.feature")


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    return {"data_root": tmp_path / "data"}


@given("a data root")
def _data_root(ctx: dict[str, Any]) -> None:
    pass  # the fixture's data_root need not exist beforehand


@when(parsers.parse('a fresh results directory is built for label "{label}"'))
def _build_one(ctx: dict[str, Any], label: str) -> None:
    ctx["result"] = _fresh_results_dir(ctx["data_root"], label)


@when(parsers.parse('two fresh results directories are built for label "{label}"'))
def _build_two(ctx: dict[str, Any], label: str) -> None:
    ctx["first"] = _fresh_results_dir(ctx["data_root"], label)
    ctx["second"] = _fresh_results_dir(ctx["data_root"], label)


@then(parsers.parse('the directory is under "{subpath}" in the data root'))
def _under(ctx: dict[str, Any], subpath: str) -> None:
    assert str(ctx["result"]).startswith(str(ctx["data_root"] / subpath))


@then("the directory exists on disk")
def _exists(ctx: dict[str, Any]) -> None:
    assert ctx["result"].is_dir()


@then("the two directories are different paths")
def _different(ctx: dict[str, Any]) -> None:
    assert ctx["first"] != ctx["second"]
