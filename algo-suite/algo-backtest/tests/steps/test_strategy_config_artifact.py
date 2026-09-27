"""BDD contract for the engine-written strategy config snapshot."""

import json
from dataclasses import replace

import pytest
from algo_backtest.artifacts import write_strategy_config
from algo_backtest.strategies import load_strategy_chain_config
from algo_core import atomicio
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/strategy_config_artifact.feature")


@given("a resolved baseline-dsha config and an existing config sidecar")
def _setup(ctx, tmp_path, monkeypatch):
    """Observe the actual atomic replacement rather than mocking the writer."""
    ctx["config"] = load_strategy_chain_config("baseline-dsha")
    ctx["directory"] = tmp_path
    ctx["path"] = tmp_path / "strategy-config.json"
    ctx["prior"] = '{"old": true}\n'
    ctx["path"].write_text(ctx["prior"])
    original = atomicio.os.replace
    ctx["replacements"] = []

    def observe(source, destination):
        """Require a complete temporary JSON before publishing the new version."""
        assert destination == ctx["path"]
        assert source.parent == destination.parent
        assert destination.read_text() == ctx["prior"]
        ctx["replacements"].append(json.loads(source.read_text()))
        original(source, destination)

    monkeypatch.setattr(atomicio.os, "replace", observe)


@given(parsers.parse("its raw config contains {invalid} data"))
def _invalid(ctx, invalid):
    """Supply values JSON must reject without lossy default conversion."""
    value = object() if invalid == "non-JSON" else float("nan")
    ctx["config"] = replace(ctx["config"], raw={"unsupported": value})


@given("the filesystem rejects the sidecar replacement")
def _filesystem_failure(monkeypatch):
    """Simulate a failure at the atomic publication boundary."""
    def reject(source, destination):
        """Raise the original filesystem error; no fallback write is permitted."""
        raise OSError("read-only filesystem")
    monkeypatch.setattr(atomicio.os, "replace", reject)


@when("the resolved config sidecar is written")
def _write(ctx):
    """Use the production helper called from ChainAlgorithm.initialize."""
    write_strategy_config(ctx["directory"], ctx["config"])


@when("writing the config sidecar fails")
def _failure(ctx):
    """Capture explicit serialization or filesystem failures."""
    with pytest.raises((ValueError, OSError)) as error:
        write_strategy_config(ctx["directory"], ctx["config"])
    ctx["error"] = str(error.value)


@then("the replacement publishes the full resolved config atomically")
def _published(ctx):
    """Exactly one atomic replacement publishes the unmodified resolved mapping."""
    assert ctx["replacements"] == [dict(ctx["config"].raw)]
    assert json.loads(ctx["path"].read_text()) == ctx["config"].raw


@then("the prior config sidecar is unchanged")
def _unchanged(ctx):
    """Never replace a good artifact with a partial or invalid document."""
    assert ctx["path"].read_text() == ctx["prior"]
    assert ctx["replacements"] == []


@then("the error explains how to fix the strategy config")
def _remediation(ctx):
    """Serialization errors identify the offending configuration and remediation."""
    assert "baseline-dsha" in ctx["error"]
    assert "JSON-safe" in ctx["error"]
    assert "config.yaml" in ctx["error"]


@then("no temporary config file remains")
def _cleaned(ctx):
    """The shared atomic writer cleans temporary files on publication failure."""
    assert list(ctx["directory"].iterdir()) == [ctx["path"]]
