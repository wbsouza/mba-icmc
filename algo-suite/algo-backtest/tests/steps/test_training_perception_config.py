"""BDD for the config-selecting offline training CLI's output contract."""

import importlib.util
from pathlib import Path

import pytest
from pytest_bdd import scenarios, then, when

scenarios("../features/training_perception_config.feature")


def _arguments(monkeypatch, extra):
    """Load the real training script and parse its public CLI arguments."""
    path = Path(__file__).parents[2] / "scripts/train_baseline_meta_learner.py"
    spec = importlib.util.spec_from_file_location("dsha_training_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr("sys.argv", [
        str(path), "--from", "2015-02-02", "--train-end", "2015-06-30",
        "--validation-end", "2015-07-31", "--test-end", "2015-08-07", *extra,
    ])
    return module._parse_args()


@when("baseline training arguments are parsed without a strategy override")
def _baseline(ctx, monkeypatch):
    """Preserve existing callers of the baseline training entry point."""
    ctx["args"] = _arguments(monkeypatch, [])


@then("training selects baseline and its bundled model output")
def _baseline_output(ctx):
    """The default training behavior and model destination remain unchanged."""
    args = ctx["args"]
    assert args.strategy == "baseline"
    assert args.out.parts[-3:] == ("algos", "baseline", "f7_meta_learner.json")


@when("baseline-dsha training arguments omit the output path")
def _missing_output(ctx, monkeypatch, capsys):
    """Reject ambiguous output before loading data or training any model."""
    with pytest.raises(SystemExit) as error:
        _arguments(monkeypatch, ["--strategy", "baseline-dsha"])
    ctx["exit"] = error.value.code
    ctx["stderr"] = capsys.readouterr().err


@then("training fails with an explicit output-path instruction")
def _output_error(ctx):
    """Name both the selected strategy and the required remediation."""
    assert ctx["exit"] == 2
    assert "--strategy baseline-dsha requires --out" in ctx["stderr"]


@when("baseline-dsha training arguments specify a separate model output")
def _separate_output(ctx, monkeypatch, tmp_path):
    """Request a DSHA-trained artifact independently of the frozen model."""
    ctx["out"] = tmp_path / "dsha.json"
    ctx["args"] = _arguments(monkeypatch, [
        "--strategy", "baseline-dsha", "--out", str(ctx["out"]),
    ])


@then("training selects baseline-dsha and the requested output")
def _candidate_output(ctx):
    """The CLI forwards the selected config identity and exact output destination."""
    assert ctx["args"].strategy == "baseline-dsha"
    assert ctx["args"].out == ctx["out"]
