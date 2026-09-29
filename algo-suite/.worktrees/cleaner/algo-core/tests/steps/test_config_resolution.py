"""Step definitions for config_resolution.feature (pytest-bdd)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_core.config import ConfigError, Impact, ParameterSpec
from algo_core.config.paths import ENV_CONF_DIR
from algo_core.config.resolution import resolve
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/config_resolution.feature")

SCHEMA = (
    ParameterSpec(name="operational.log_level", impact=Impact.OPERATIONAL, default="INFO"),
    ParameterSpec(name="markets.oanda.data_tz", impact=Impact.OPERATIONAL, default="UTC"),
)
CURRENT_VERSION = 1


@pytest.fixture
def ctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A clean conf dir + a stripped ALGO_ environment for deterministic resolution."""
    conf = tmp_path / "conf"
    conf.mkdir()
    for key in [k for k in __import__("os").environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(ENV_CONF_DIR, str(conf))
    return {"conf": conf, "monkeypatch": monkeypatch}


def _set_nested(root: dict[str, Any], dotted: str, value: Any) -> None:
    """Set a dotted key into a nested dict, creating intermediate dicts."""
    node = root
    parts = dotted.split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def _write_yaml(path: Path, dotted: str, value: Any, *, schema_version: int | None) -> None:
    """Write a config file setting one dotted key, optionally with a schema_version."""
    doc: dict[str, Any] = {}
    if schema_version is not None:
        doc["schema_version"] = schema_version
    _set_nested(doc, dotted, value)
    path.write_text(yaml.safe_dump(doc))


@given("a schema with operational defaults log_level \"INFO\" and oanda data_tz \"UTC\"")
def _schema(ctx: dict[str, Any]) -> None:
    ctx["schema"] = SCHEMA


@given(parsers.parse("the current schema version is {version:d}"))
def _version(ctx: dict[str, Any], version: int) -> None:
    ctx["version"] = version


@given("no config files and no ALGO_ environment overrides")
def _zero_config(ctx: dict[str, Any]) -> None:
    pass  # the fixture already gives a clean env + empty conf dir


@given(parsers.parse('conf/algo.yaml sets "{key}" to "{value}"'))
def _global_sets(ctx: dict[str, Any], key: str, value: str) -> None:
    _write_yaml(ctx["conf"] / "algo.yaml", key, value, schema_version=CURRENT_VERSION)


@given(parsers.parse('conf/backtest.yaml sets "{key}" to "{value}"'))
def _tool_sets(ctx: dict[str, Any], key: str, value: str) -> None:
    _write_yaml(ctx["conf"] / "backtest.yaml", key, value, schema_version=CURRENT_VERSION)


@given(parsers.parse('conf/algo.yaml without a schema_version sets "{key}" to "{value}"'))
def _global_sets_no_version(ctx: dict[str, Any], key: str, value: str) -> None:
    _write_yaml(ctx["conf"] / "algo.yaml", key, value, schema_version=None)


@given(parsers.parse('the environment sets "{env}" to "{value}"'))
def _env_sets(ctx: dict[str, Any], env: str, value: str) -> None:
    ctx["monkeypatch"].setenv(env, value)


@when(parsers.parse('I resolve the "{tool}" config'))
def _resolve(ctx: dict[str, Any], tool: str) -> None:
    ctx["result"] = ctx["error"] = None
    try:
        ctx["result"] = resolve(tool, ctx["schema"], ctx["version"])
    except ConfigError as exc:
        ctx["error"] = exc


@then("it resolves successfully")
def _ok(ctx: dict[str, Any]) -> None:
    assert ctx["error"] is None, ctx["error"]
    assert ctx["result"] is not None


@then("it fails to resolve")
def _failed(ctx: dict[str, Any]) -> None:
    assert ctx["error"] is not None


@then(parsers.parse('"{key}" is "{value}"'))
def _value_is(ctx: dict[str, Any], key: str, value: str) -> None:
    assert ctx["result"].values[key] == value


@then(parsers.parse('the provenance log contains "{line}"'))
def _provenance(ctx: dict[str, Any], line: str) -> None:
    assert line in ctx["result"].provenance


@then(parsers.parse('the error mentions "{needle}"'))
def _error_mentions(ctx: dict[str, Any], needle: str) -> None:
    assert needle in str(ctx["error"])
