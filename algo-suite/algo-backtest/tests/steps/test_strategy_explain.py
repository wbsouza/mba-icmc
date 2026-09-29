"""Steps for strategy_explain.feature — the explain-strategy CLI command."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_backtest.cli import app
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/strategy_explain.feature")


@pytest.fixture
def ectx() -> dict[str, Any]:
    """Holds the CLI result and any external strategies directory."""
    return {}


@given(
    parsers.parse(
        'an external strategies directory holding "{name}" extending "{base}" with extra '
        '"{extra_yaml}"'
    )
)
def _external_dir(
    ectx: dict[str, Any], tmp_path: Path, name: str, base: str, extra_yaml: str
) -> None:
    root = tmp_path / "strategies"
    (root / name).mkdir(parents=True)
    body: dict[str, Any] = {"extends": base, **(yaml.safe_load(extra_yaml) or {})}
    (root / name / "config.yaml").write_text(yaml.safe_dump(body))
    ectx["strategies_root"] = root


@when(parsers.parse('I run "{command}"'))
def _run(ectx: dict[str, Any], command: str) -> None:
    ectx["cli"] = CliRunner().invoke(app, command.split()[1:])


@when(parsers.parse('I run explain-strategy for "{name}" with that directory'))
def _run_external(ectx: dict[str, Any], name: str) -> None:
    ectx["cli"] = CliRunner().invoke(
        app, ["explain-strategy", name, "--strategies-dir", str(ectx["strategies_root"])]
    )


@then(parsers.parse("the explain command exits with code {code:d}"))
def _exit_code(ectx: dict[str, Any], code: int) -> None:
    assert ectx["cli"].exit_code == code, ectx["cli"].output


@then(parsers.parse('the explanation lists "{key}" from "{source}"'))
def _lists(ectx: dict[str, Any], key: str, source: str) -> None:
    lines = [line for line in ectx["cli"].output.splitlines() if line.startswith(f"{key} = ")]
    assert lines, f"no line for {key!r} in:\n{ectx['cli'].output}"
    assert lines[0].endswith(f"# {source}"), lines[0]


@then(parsers.parse('the explain output names "{fragment}"'))
def _names(ectx: dict[str, Any], fragment: str) -> None:
    assert fragment in ectx["cli"].output
