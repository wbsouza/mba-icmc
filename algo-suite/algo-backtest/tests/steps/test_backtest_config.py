"""Steps for backtest_config.feature — typed, config-driven data timezone."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from algo_backtest.config import load_backtest_config
from algo_core.config.paths import ENV_CONF_DIR
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/backtest_config.feature")


@pytest.fixture
def cfg_ctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Clean ALGO_ env + empty conf dir so resolution is deterministic."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    conf = tmp_path / "conf"
    conf.mkdir()
    monkeypatch.setenv(ENV_CONF_DIR, str(conf))
    monkeypatch.setenv("ALGO_DATA_ROOT", str(tmp_path / "data"))
    return {"monkeypatch": monkeypatch}


@given("no config files and no ALGO_ overrides")
def _zero_config(cfg_ctx: dict[str, Any]) -> None:
    pass  # the fixture already cleared the env and made an empty conf dir


@given(parsers.parse('the environment sets "{env}" to "{value}"'))
def _env_sets(cfg_ctx: dict[str, Any], env: str, value: str) -> None:
    cfg_ctx["monkeypatch"].setenv(env, value)


@when("I load the algo-backtest config")
def _load(cfg_ctx: dict[str, Any]) -> None:
    cfg_ctx["cfg"] = cfg_ctx["error"] = None
    try:
        cfg_ctx["cfg"] = load_backtest_config()
    except Exception as exc:  # noqa: BLE001 — asserted in the Then steps
        cfg_ctx["error"] = exc


@then(parsers.parse('the OANDA data timezone is "{tz}"'))
def _tz_is(cfg_ctx: dict[str, Any], tz: str) -> None:
    assert str(cfg_ctx["cfg"].oanda_data_tz) == tz


@then("it is a ZoneInfo instance")
def _is_zoneinfo(cfg_ctx: dict[str, Any]) -> None:
    assert isinstance(cfg_ctx["cfg"].oanda_data_tz, ZoneInfo)


@then("the provenance trail includes the data root")
def _provenance_data_root(cfg_ctx: dict[str, Any]) -> None:
    cfg = cfg_ctx["cfg"]
    assert any("data_root" in line and str(cfg.data_root) in line for line in cfg.provenance)


@then("loading fails with a timezone error")
def _fails_tz(cfg_ctx: dict[str, Any]) -> None:
    assert isinstance(cfg_ctx["error"], ValueError)
    assert "timezone" in str(cfg_ctx["error"]).lower()


@then("loading fails naming the missing broker.adapter parameter")
def _fails_missing_broker_adapter(cfg_ctx: dict[str, Any]) -> None:
    error = str(cfg_ctx["error"])
    assert "adapter" in error and "broker" in error, error
