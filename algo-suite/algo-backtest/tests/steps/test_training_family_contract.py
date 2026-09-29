"""BDD for training CLI selection guards using real strategy configuration parsing."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import Mock

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/training_family_contract.feature")

_SCRIPTS = Path(__file__).parents[2] / "scripts"


@pytest.fixture
def family_cli(tmp_path: Path) -> dict[str, Any]:
    """Keep all candidate YAML and potential artifacts in the scenario directory."""
    return {"root": tmp_path / "strategies", "out": tmp_path / "model.json", "stubs": {}}


def _shape(extends: str, families: list[str]) -> dict[str, Any]:
    """A minimal valid strategy shape isolating the script's own contract: `none` is a
    self-contained one-filter chain without F7 (so it names F1 as its terminal filter),
    anything else extends a bundled base."""
    meta_learner = {"families": families}
    if extends == "none":
        return {
            "schema_version": 2, "filters": ["f1_trend"], "terminal_filter": "f1_trend",
            "meta_learner": meta_learner,
        }
    return {"extends": extends, "meta_learner": meta_learner}


@given(
    parsers.parse(
        "the {trainer} training CLI selects an external strategy extending {extends} with "
        "families {families}"
    )
)
def external_selection(
    family_cli: dict[str, Any], trainer: str, extends: str, families: str
) -> None:
    """Persist small real YAML inputs rather than mocking the configuration loader."""
    family_cli.update(trainer=trainer, strategy="candidate")
    directory = family_cli["root"] / "candidate"
    directory.mkdir(parents=True)
    body = _shape(extends, yaml.safe_load(families))
    (directory / "config.yaml").write_text(yaml.safe_dump(body))


def _load_trainer(path: Path) -> ModuleType:
    """Import a `scripts/train_*_meta_learner.py` by path, as the CLI would run it."""
    spec = importlib.util.spec_from_file_location(f"family_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@given("the market data and model persistence behind the training CLI are stubbed")
def stub_training_pipeline(family_cli: dict[str, Any]) -> None:
    """Replace every step past config validation so the families reaching the fit and
    the saved provenance can be observed without Parquet or a LightGBM fit."""
    family_cli["stubs"] = {
        "load_m1_bars": Mock(return_value=[]),
        "load_event_intensity": Mock(return_value={}),
        "build_training_rows": Mock(return_value=[]),
        "walk_forward_split": Mock(return_value=Mock(train=[], validation=[], test=[])),
        "train_meta_learner": Mock(return_value=object()),
        "save_model": Mock(),
    }


def _argv(path: Path, family_cli: dict[str, Any]) -> list[str]:
    """The CLI arguments every scenario invokes the trainer with."""
    return [
        str(path),
        "--strategy", family_cli["strategy"],
        "--strategies-dir", str(family_cli["root"]),
        "--from", "2015-02-02",
        "--train-end", "2015-06-30",
        "--validation-end", "2015-07-31",
        "--test-end", "2015-08-07",
        "--out", str(family_cli["out"]),
    ]


@when("the selected training CLI is invoked")
def invoke_cli(
    family_cli: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Parse actual CLI arguments and stop at the first expensive market-data boundary
    (or run through the stubbed pipeline when a scenario installed one)."""
    path = _SCRIPTS / f"train_{family_cli['trainer']}_meta_learner.py"
    module = _load_trainer(path)
    price = Mock(side_effect=RuntimeError("price data boundary reached"))
    events = Mock(side_effect=RuntimeError("event data boundary reached"))
    monkeypatch.setattr(module, "load_m1_bars", price)
    if hasattr(module, "load_event_intensity"):
        monkeypatch.setattr(module, "load_event_intensity", events)
    for name, stub in family_cli.get("stubs", {}).items():
        monkeypatch.setattr(module, name, stub)
    monkeypatch.setenv("ALGO_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setattr(sys, "argv", _argv(path, family_cli))
    family_cli.update(price=price, events=events)
    try:
        module.main()
    except (ValueError, RuntimeError) as error:
        family_cli["error"] = error


@then(parsers.parse('training rejects the selection mentioning "{reason}" with remediation'))
def rejected_selection(family_cli: dict[str, Any], reason: str) -> None:
    """Require a strategy contract error, not an unrelated market-file failure."""
    error = family_cli["error"]
    assert isinstance(error, ValueError), error
    assert reason in str(error), str(error)
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
    assert isinstance(family_cli["error"], RuntimeError), family_cli.get("error")
    assert str(family_cli["error"]) == "price data boundary reached"
    family_cli["price"].assert_called_once()
    family_cli["events"].assert_not_called()


@then(parsers.parse("the meta-learner is trained on the families {families}"))
def trained_families(family_cli: dict[str, Any], families: str) -> None:
    """The fit receives exactly the declared families, in the declared order."""
    assert "error" not in family_cli, family_cli.get("error")
    fit = family_cli["stubs"]["train_meta_learner"]
    fit.assert_called_once()
    assert [f.value for f in fit.call_args.kwargs["families"]] == yaml.safe_load(families)


@then(parsers.parse("the persisted model provenance records the families {families}"))
def recorded_families(family_cli: dict[str, Any], families: str) -> None:
    """What the model document says it was trained on is what the run-time check reads."""
    save = family_cli["stubs"]["save_model"]
    save.assert_called_once()
    _model, out, provenance = save.call_args.args
    assert out == family_cli["out"]
    assert provenance["families"] == yaml.safe_load(families)
    assert provenance["strategy"] == "candidate"


@when("each current Heikin-Ashi H4 candidate is passed to its matching training CLI")
def current_candidates(
    family_cli: dict[str, Any], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exercise every shipped experiment strategy through its actual trainer entry point."""
    root = Path(__file__).parents[3] / "experiments/heikin-ashi-signals/strategies"
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
        invoke_cli(candidate, monkeypatch, tmp_path)
        reaches_market(candidate)
        accepted.append(path.parent.name)
    family_cli["accepted"] = accepted


@then("all eight candidates reach the price data boundary")
def accepted_candidates(family_cli: dict[str, Any]) -> None:
    """Preserve the pending experiment matrix without starting training or writing models."""
    assert len(family_cli["accepted"]) == 8
    assert not family_cli["out"].exists()
