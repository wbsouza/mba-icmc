"""Step definitions for layout.feature (pytest-bdd).

Tests in this suite are written as Gherkin scenarios; this module binds the
steps to the algo-core layout/config conventions.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from algo_core import config, layout
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/layout.feature")


@pytest.fixture
def context() -> dict[str, Path]:
    """Carries resolved paths between When and Then steps."""
    return {}


# --- Given -----------------------------------------------------------------


@given("no ALGO_DATA_ROOT is set")
def _clear_data_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(layout.ENV_DATA_ROOT, raising=False)


@given(parsers.parse('ALGO_DATA_ROOT is set to "{value}"'))
def _set_data_root(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(layout.ENV_DATA_ROOT, value)


@given("no ALGO_CONF_DIR is set")
def _clear_conf_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.ENV_CONF_DIR, raising=False)
    monkeypatch.delenv(layout.ENV_DATA_ROOT, raising=False)


@given(parsers.parse('ALGO_CONF_DIR is set to "{value}"'))
def _set_conf_dir(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(config.ENV_CONF_DIR, value)


# --- When ------------------------------------------------------------------


@when("I resolve the data root")
def _resolve_data_root(context: dict[str, Path]) -> None:
    context["data_root"] = layout.data_root()


@when("I resolve the config paths")
def _resolve_config_paths(context: dict[str, Path]) -> None:
    context["conf_dir"] = config.conf_dir()
    context["global"] = config.global_config_path()
    context["download"] = config.tool_config_path("download")


# --- Then ------------------------------------------------------------------


@then(parsers.parse('the data root is named "{name}" inside the algo-suite workspace'))
def _data_root_named(context: dict[str, Path], name: str) -> None:
    root = context["data_root"]
    assert root.name == name
    assert root.parent.name == "algo-suite"


@then(parsers.parse('the data root path is "{value}"'))
def _data_root_path(context: dict[str, Path], value: str) -> None:
    assert context["data_root"] == Path(value)


@then(parsers.parse('the conf dir is named "{name}"'))
def _conf_dir_named(context: dict[str, Path], name: str) -> None:
    assert context["conf_dir"].name == name


@then(parsers.parse('the conf dir path is "{value}"'))
def _conf_dir_path(context: dict[str, Path], value: str) -> None:
    assert context["conf_dir"] == Path(value)


@then(parsers.parse('the global config file is named "{name}"'))
def _global_named(context: dict[str, Path], name: str) -> None:
    assert context["global"].name == name


@then(parsers.parse('the global config path is "{value}"'))
def _global_path(context: dict[str, Path], value: str) -> None:
    assert context["global"] == Path(value)


@then(parsers.parse('the download tool config file is named "{name}"'))
def _download_named(context: dict[str, Path], name: str) -> None:
    assert context["download"].name == name
