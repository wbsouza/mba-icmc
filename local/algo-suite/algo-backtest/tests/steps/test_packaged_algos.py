"""Steps for packaged_algos.feature — shipped LEAN algos must at least parse.

These files are excluded from ruff/mypy (they import the container-only AlgorithmImports),
so this is the one gate that protects them: a SyntaxError in a shipped algorithm would
otherwise only surface inside a LEAN run.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import algo_backtest
from pytest_bdd import scenarios, then, when

scenarios("../features/packaged_algos.feature")

_ALGOS_DIR = Path(algo_backtest.__file__).parent / "algos"


@when("I parse every bundled algorithm file")
def _parse_all(ctx: dict[str, Any]) -> None:
    files = sorted(_ALGOS_DIR.rglob("main.py"))
    errors: dict[str, str] = {}
    for path in files:
        try:
            ast.parse(path.read_text())
        except SyntaxError as exc:
            errors[path.name] = str(exc)
    ctx["files"] = files
    ctx["errors"] = errors


@then("they are all syntactically valid")
def _all_valid(ctx: dict[str, Any]) -> None:
    assert ctx["files"], f"no bundled algorithms found under {_ALGOS_DIR}"
    assert ctx["errors"] == {}, ctx["errors"]
