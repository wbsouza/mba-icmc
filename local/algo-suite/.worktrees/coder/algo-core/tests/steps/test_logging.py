"""Step definitions for logging.feature (pytest-bdd)."""

from __future__ import annotations

import pytest
from algo_core import logging as core_logging
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/logging.feature")


@pytest.fixture
def state() -> dict[str, object]:
    return {}


@when(parsers.parse('I resolve the log level "{name}"'))
def _resolve(state: dict[str, object], name: str) -> None:
    try:
        state["level"] = core_logging.resolve_level(name)
    except ValueError as error:
        state["error"] = error


@then(parsers.parse("the numeric level is {value:d}"))
def _level(state: dict[str, object], value: int) -> None:
    assert state["level"] == value


@then("resolving the level fails")
def _fail(state: dict[str, object]) -> None:
    assert isinstance(state.get("error"), ValueError)


@given(parsers.parse('logging is configured at level "{name}"'))
def _configure(name: str) -> None:
    core_logging.configure_logging(name)


@when(parsers.parse('I get a logger named "{name}"'))
def _get_logger(state: dict[str, object], name: str) -> None:
    state["logger"] = core_logging.get_logger(name)


@then("the logger exposes info and bind")
def _exposes(state: dict[str, object]) -> None:
    logger = state["logger"]
    assert hasattr(logger, "info")
    assert hasattr(logger, "bind")
