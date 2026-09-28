"""BDD for training CLI selection guards using real strategy configuration parsing."""

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/training_family_contract.feature")


@pytest.fixture
def family_cli(tmp_path: Path) -> dict[str, Any]:
    """Keep all candidate YAML and potential artifacts in the scenario directory."""
    return {"root": tmp_path / "strategies", "out": tmp_path / "model.json"}


def _shape(name: str) -> dict[str, Any]:
    """Build minimal valid strategy shapes that isolate the script's own contract."""
    if name == "no-f7":
        return {"schema_version": 2, "filters": ["f1_trend"]}
    base = "hybrid" if name.startswith("hybrid") else "baseline"
    families = ["trend", "indicator", "pattern"] + (["news"] if base == "hybrid" else [])
    if name.endswith("-subset"):
        families.remove("pattern")
    if name.endswith("-reversed"):
        families.reverse()
    if name == "baseline-news-gate":
        base = "hybrid"
    if name == "hybrid-without-news-gate":
        base = "baseline"
    return {"extends": base, "meta_learner": {"families": families}}


@given(parsers.parse("the {trainer} training CLI selects an external {shape} strategy"))
def external_selection(family_cli: dict[str, Any], trainer: str, shape: str) -> None:
    """Persist small real YAML inputs rather than mocking the configuration loader."""
    family_cli.update(trainer=trainer, strategy="candidate")
    directory = family_cli["root"] / "candidate"
    directory.mkdir(parents=True)
    (directory / "config.yaml").write_text(yaml.safe_dump(_shape(shape)))


@when("the selected training CLI is invoked")
def invoke_cli(family_cli: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Parse actual CLI arguments and stop at the first expensive market-data boundary."""
    path = Path(__file__).parents[2] / f"scripts/train_{family_cli['trainer']}_meta_learner.py"
    spec = importlib.util.spec_from_file_location(f"family_{family_cli['trainer']}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    price = Mock(side_effect=RuntimeError("price data boundary reached"))
    events = Mock(side_effect=RuntimeError("event data boundary reached"))
    monkeypatch.setattr(module, "load_m1_bars", price)
    if hasattr(module, "load_event_intensity"):
        monkeypatch.setattr(module, "load_event_intensity", events)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(path),
            "--strategy",
            family_cli["strategy"],
            "--strategies-dir",
            str(family_cli["root"]),
            "--from",
            "2015-02-02",
            "--train-end",
            "2015-06-30",
            "--validation-end",
            "2015-07-31",
            "--test-end",
            "2015-08-07",
            "--out",
            str(family_cli["out"]),
        ],
    )
    family_cli.update(price=price, events=events)
    try:
        module.main()
    except (ValueError, RuntimeError) as error:
        family_cli["error"] = error


@then(parsers.parse('training rejects the selection mentioning "{reason}" with remediation'))
def rejected_selection(family_cli: dict[str, Any], reason: str) -> None:
    """Require a strategy contract error, not an unrelated market-file failure."""
    error = family_cli["error"]
    assert isinstance(error, ValueError)
    assert reason in str(error)
    assert "candidate" in str(error)
    assert "use" in str(error) or "enable" in str(error)


@then("neither price nor event data was read and no model was written")
def no_market_reads(family_cli: dict[str, Any]) -> None:
    """A rejected strategy cannot trigger costly IO or emit an incompatible artifact."""
    family_cli["price"].assert_not_called()
    family_cli["events"].assert_not_called()
    assert not family_cli["out"].exists()


@then("the selection reaches the price data boundary")
def reaches_market(family_cli: dict[str, Any]) -> None:
    """Correct family sets are accepted even when their YAML ordering differs."""
    assert isinstance(family_cli["error"], RuntimeError)
    assert str(family_cli["error"]) == "price data boundary reached"
    family_cli["price"].assert_called_once()
    family_cli["events"].assert_not_called()


@when("each current Dragon08 candidate is passed to its matching training CLI")
def current_candidates(family_cli: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise every shipped experiment strategy through its actual trainer entry point."""
    root = Path(__file__).parents[3] / "experiments/spockfx-signals/strategies"
    paths = sorted(root.glob("*/config.yaml"))
    assert len(paths) == 8
    accepted = []
    for path in paths:
        raw = yaml.safe_load(path.read_text())
        trainer = "hybrid" if "news" in raw["meta_learner"]["families"] else "baseline"
        candidate = {
            "root": root,
            "out": family_cli["out"],
            "strategy": path.parent.name,
            "trainer": trainer,
        }
        invoke_cli(candidate, monkeypatch)
        reaches_market(candidate)
        accepted.append(path.parent.name)
    family_cli["accepted"] = accepted


@then("all eight candidates reach the price data boundary")
def accepted_candidates(family_cli: dict[str, Any]) -> None:
    """Preserve the pending experiment matrix without starting training or writing models."""
    assert len(family_cli["accepted"]) == 8
    assert not family_cli["out"].exists()
