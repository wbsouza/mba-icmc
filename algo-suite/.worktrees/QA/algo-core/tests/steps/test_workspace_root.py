"""Step definitions for workspace_root.feature (pytest-bdd, TD-7).

Tests in this suite are written as Gherkin scenarios; this module binds the
steps to the algo-core fail-fast workspace-root guard.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from algo_core import layout
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/workspace_root.feature")


@pytest.fixture
def context() -> dict[str, object]:
    """Carries the start path and the raised error between steps."""
    return {}


@given("a start path with no algo-suite ancestor")
def _start_path(context: dict[str, object], tmp_path: Path) -> None:
    context["start"] = tmp_path / "nowhere"


@when("I resolve the workspace root from it")
def _resolve(context: dict[str, object]) -> None:
    start = context["start"]
    assert isinstance(start, Path)
    try:
        layout._workspace_root(start=start)
    except RuntimeError as exc:
        context["error"] = exc


@then(parsers.parse('it fails with a "{needle}" RuntimeError'))
def _fails(context: dict[str, object], needle: str) -> None:
    error = context.get("error")
    assert isinstance(error, RuntimeError)
    assert needle in str(error)
