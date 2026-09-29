"""Behavioral coverage for the reproducible perception gauntlet."""

import json

import mutation_harness
import perception_quality
from pytest_bdd import given, scenarios, then, when

scenarios("../features/perception_quality.feature")


@given("host perception coverage and native traced lines")
def coverage_inputs(context, tmp_path, monkeypatch):
    package = tmp_path / "perception"
    package.mkdir()
    (package / "lean_indicator.py").write_text("value = 1\n")
    monkeypatch.setattr(perception_quality, "PACKAGE", package)
    context["host"] = tmp_path / "host.json"
    context["native"] = tmp_path / "native"
    context["native"].mkdir()
    context["output"] = tmp_path / "merged.json"
    context["host"].write_text(json.dumps({"meta": {"branch_coverage": True}, "files": {
        "src/algo_backtest/perception/lean_indicator.py": {
            "executed_lines": [1], "missing_lines": [2, 3], "summary": {},
        },
    }}))
    (context["native"] / "perception-native-lines.json").write_text(json.dumps({
        "/Lean/algo_backtest/perception/lean_indicator.py": [2, 99],
    }))


@given("the native adapter trace is absent")
def remove_adapter(context):
    (context["native"] / "perception-native-lines.json").write_text("{}")


@when("the perception coverage is merged")
def merge(context):
    try:
        perception_quality.merge_native_coverage(
            context["host"], context["native"], context["output"]
        )
    except ValueError as error:
        context["error"] = str(error)


@then("native statements count as covered without counting nonexecutable trace lines")
def merged_values(context):
    report = json.loads(context["output"].read_text())
    data = report["files"]["src/algo_backtest/perception/lean_indicator.py"]
    assert data == {"executed_lines": [1, 2], "missing_lines": [3]}
    assert report["meta"]["branch_coverage"] is False


@then("merging fails because native adapter evidence is missing")
def missing_evidence(context):
    assert context["error"] == "lean_indicator.py: missing or ambiguous native trace"
    assert not context["output"].exists()


@given("a pure perception module importing QuantConnect")
def bad_dependency(context, tmp_path, monkeypatch):
    (tmp_path / "heikin_ashi.py").write_text("import QuantConnect\n")
    monkeypatch.setattr(perception_quality, "PACKAGE", tmp_path)


@when("the perception architecture gate runs")
def architecture_gate(context, capsys):
    context["status"] = perception_quality.check_architecture()
    context["log"] = capsys.readouterr().out


@then("the dependency gate fails")
def rejected_dependency(context):
    assert context["status"] == 1
    assert "heikin_ashi.py: forbidden dependency QuantConnect" in context["log"]


@given("systemd-run is available")
def systemd_available(monkeypatch):
    monkeypatch.setattr(mutation_harness.shutil, "which", lambda _: "/usr/bin/systemd-run")


@when("the mutation command is memory capped")
def memory_cap(context):
    context["command"], context["preexec"] = mutation_harness.cap_memory(["python", "probe.py"])


@then("its child scope has a memory limit and preserves the command")
def capped_command(context):
    assert context["command"][0:4] == ["systemd-run", "--user", "--scope", "--collect"]
    assert any(arg.startswith("MemoryMax=") for arg in context["command"])
    assert context["command"][-3:] == ["--", "python", "probe.py"]
    assert context["preexec"] is None
