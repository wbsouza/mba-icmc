"""BDD contract for the engine-written strategy config snapshots (JSON + YAML)."""

import json
from dataclasses import replace

import pytest
import yaml
from algo_backtest.artifacts import write_strategy_config
from algo_backtest.strategies import load_resolved_strategy, load_strategy_chain_config
from algo_core import atomicio
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/strategy_config_artifact.feature")

_SIDECARS = ("strategy-config.json", "strategy-config.yaml")


def _parse(name, text):
    """Parse a sidecar's text by its format (both hold one mapping)."""
    return json.loads(text) if name.endswith(".json") else yaml.safe_load(text)


@given("a resolved baseline-dsha config and existing config sidecars")
def _setup(ctx, tmp_path, monkeypatch):
    """Observe the actual atomic replacement rather than mocking the writer."""
    ctx["config"] = load_strategy_chain_config("baseline-dsha")
    ctx["directory"] = tmp_path
    ctx["paths"] = {name: tmp_path / name for name in _SIDECARS}
    ctx["prior"] = {
        "strategy-config.json": '{"old": true}\n', "strategy-config.yaml": "old: true\n",
    }
    for name, path in ctx["paths"].items():
        path.write_text(ctx["prior"][name])
    original = atomicio.os.replace
    ctx["replacements"] = {name: [] for name in _SIDECARS}

    def observe(source, destination):
        """Require a complete temporary document before publishing the new version."""
        assert destination in ctx["paths"].values()
        assert source.parent == destination.parent
        assert destination.read_text() == ctx["prior"][destination.name]
        ctx["replacements"][destination.name].append(_parse(destination.name, source.read_text()))
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


@when("the resolved config sidecars are written")
def _write(ctx):
    """Use the production helper called from ChainAlgorithm.initialize."""
    write_strategy_config(ctx["directory"], ctx["config"])


@when("writing the config sidecars fails")
def _failure(ctx):
    """Capture explicit serialization or filesystem failures."""
    with pytest.raises((ValueError, OSError)) as error:
        write_strategy_config(ctx["directory"], ctx["config"])
    ctx["error"] = str(error.value)


@then(parsers.parse("the {sidecar} replacement publishes the full resolved config atomically"))
def _published(ctx, sidecar):
    """Exactly one atomic replacement publishes the unmodified resolved mapping."""
    assert ctx["replacements"][sidecar] == [dict(ctx["config"].raw)]
    assert _parse(sidecar, ctx["paths"][sidecar].read_text()) == ctx["config"].raw


@then(parsers.parse('strategy-config.yaml loads back as the resolved "{name}" strategy'))
def _yaml_reloads(ctx, name):
    """The YAML sidecar is a resolved document the strategy loader accepts as-is."""
    reloaded = load_resolved_strategy(ctx["paths"]["strategy-config.yaml"], name=name)
    assert reloaded == replace(ctx["config"], extends=None)


@then("strategy-config.json and strategy-config.yaml hold the same document")
def _same_document(ctx):
    documents = [_parse(name, path.read_text()) for name, path in ctx["paths"].items()]
    assert documents[0] == documents[1]


@then("the prior config sidecars are unchanged")
def _unchanged(ctx):
    """Never replace a good artifact with a partial or invalid document."""
    for name, path in ctx["paths"].items():
        assert path.read_text() == ctx["prior"][name], name
        assert ctx["replacements"][name] == [], name


@then("the error explains how to fix the strategy config")
def _remediation(ctx):
    """Serialization errors identify the offending configuration and remediation."""
    assert "baseline-dsha" in ctx["error"]
    assert "JSON-safe" in ctx["error"]
    assert "config.yaml" in ctx["error"]


@then("no temporary config file remains")
def _cleaned(ctx):
    """The shared atomic writer cleans temporary files on publication failure."""
    assert sorted(ctx["directory"].iterdir()) == sorted(ctx["paths"].values())
