"""Step definitions for run_with_logging.feature (pytest-bdd, TD-4).

Tests in this suite are written as Gherkin scenarios; this module binds the
steps to the algo-core CLI boundary handler.
"""

from __future__ import annotations

import pytest
from algo_core.logging import run_with_logging
from pytest_bdd import parsers, scenarios, then, when

scenarios("../features/run_with_logging.feature")


@pytest.fixture
def context() -> dict[str, object]:
    """Carries the captured SystemExit or recorded calls between steps."""
    return {}


def _boom() -> None:
    """Raise an unhandled RuntimeError."""
    raise RuntimeError("kaboom")


def _exit_two() -> None:
    """Raise an explicit SystemExit with code 2."""
    raise SystemExit(2)


@when("I run a callable that raises RuntimeError")
def _run_boom(context: dict[str, object]) -> None:
    with pytest.raises(SystemExit) as exc:
        run_with_logging(_boom)
    context["exit"] = exc.value


@when("I run a callable that raises SystemExit 2")
def _run_exit_two(context: dict[str, object]) -> None:
    with pytest.raises(SystemExit) as exc:
        run_with_logging(_exit_two)
    context["exit"] = exc.value


@when("I run a callable that records a call")
def _run_ok(context: dict[str, object]) -> None:
    calls: list[int] = []

    def _ok() -> None:
        calls.append(1)

    run_with_logging(_ok)
    context["calls"] = calls


@then(parsers.parse("it exits with code {code:d}"))
def _exits_with(context: dict[str, object], code: int) -> None:
    exit_exc = context["exit"]
    assert isinstance(exit_exc, SystemExit)
    assert exit_exc.code == code


@then("the recorded calls are exactly one")
def _calls_one(context: dict[str, object]) -> None:
    assert context["calls"] == [1]
