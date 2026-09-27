"""Exercise the executable QA contract against controlled on-disk run artifacts."""

import hashlib
import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("../features/ablation_provenance.feature")


@pytest.fixture
def ablation_qa():
    """Load the same standalone QA implementation used for committed evidence."""
    path = Path(__file__).parents[1] / "qa" / "run_double_smoothed_heikin_ashi_qa.py"
    spec = importlib.util.spec_from_file_location("dsha_ablation_qa", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@given("a completed baseline run with a recorded model hash")
def _completed_run(ctx, tmp_path):
    """Supply every other required artifact so a missing sidecar is the sole fault."""
    ctx["root"] = tmp_path
    ctx["run"] = tmp_path / "runs" / "baseline" / "sample"
    ctx["run"].mkdir(parents=True)
    manifest = {
        "success": True, "strategy": "baseline", "closed_trades": 0,
        "symbol": "EURUSD", "start": "2015-08-03", "end": "2015-08-07", "params": {},
    }
    for name, value in (("run.json", manifest), ("metrics.json", {}), ("trades.json", [])):
        (ctx["run"] / name).write_text(json.dumps(value))
    (ctx["run"] / "log.txt").write_text("MODEL_SHA256=" + "a" * 64)
    pq.write_table(pa.table({"timestamp": []}), ctx["run"] / "decisions.parquet")


@given("the run includes its resolved engine config")
def _engine_config(ctx):
    """Preserve intentionally noncanonical whitespace to check byte provenance."""
    ctx["config_bytes"] = b'{"perception_source": "ema", "filters": []}\n'
    (ctx["run"] / "strategy-config.json").write_bytes(ctx["config_bytes"])


@when("the ablation QA inspects the run")
def _inspect(ctx, ablation_qa):
    """Capture the QA contract's explicit assertion failures."""
    try:
        ctx["evidence"] = ablation_qa.inspect_run(
            ctx["root"], "baseline/sample", "baseline", ctx["root"] / "evidence")
    except AssertionError as error:
        ctx["error"] = str(error)


@then("the run is rejected for missing its engine-written config")
def _missing_config(ctx):
    """QA must never synthesize a present-day config for an older run."""
    assert "missing engine-written strategy-config.json" in ctx["error"]
    assert "evidence" not in ctx


@then("evidence records and copies the original engine config")
def _config_provenance(ctx):
    """The content, digest and origin all refer to the actual engine bytes."""
    evidence = ctx["evidence"]
    assert evidence["config"] == json.loads(ctx["config_bytes"])
    assert evidence["config_origin"] == "engine-written strategy-config.json"
    assert evidence["artifact_sha256"]["strategy-config.json"] == hashlib.sha256(
        ctx["config_bytes"]).hexdigest()
    assert (ctx["root"] / "evidence/baseline/strategy-config.json").read_bytes() == (
        ctx["config_bytes"])


def _decision(minute, candidate):
    """Keep strengths equal while realistic F1 direction results differ."""
    direction = -1 if candidate else 1
    return {
        "timestamp": datetime(2015, 8, 3, tzinfo=UTC) + timedelta(minutes=minute),
        "features_hash": f"{'dsha' if candidate else 'ema'}-{minute}",
        "filter_results": [{
            "filter_name": "F1_trend", "reason": (
                f"trend_direction={direction}.0 higher_tf_trend_direction={direction}.0 "
                "trend_strength=0.5"),
        }],
    }


@given("paired decision artifacts with a later and shorter candidate history")
def _paired_decisions(ctx, tmp_path):
    """Use a small representative audit trail, including actual Parquet decoding."""
    ctx["root"] = tmp_path
    ctx["baseline"] = [_decision(minute, False) for minute in range(1, 5)]
    ctx["candidate"] = [_decision(minute, True) for minute in (3, 4)]


@given("a candidate decision is introduced at the first baseline timestamp")
def _premature_decision(ctx):
    """A candidate with three rows is still shorter, but starts prematurely."""
    ctx["candidate"].insert(0, _decision(1, True))


@given("extra late candidate decisions erase the row-count difference")
def _extra_decisions(ctx):
    """Keep the later start so the row-count guard is independently necessary."""
    ctx["candidate"].extend(_decision(minute, True) for minute in (5, 6))


@when("the ablation QA compares their decisions")
def _compare(ctx, ablation_qa):
    """Drive comparison through its real artifact reader."""
    for strategy in ("baseline", "candidate"):
        path = ctx["root"] / "runs" / strategy / "decisions.parquet"
        path.parent.mkdir(parents=True)
        pq.write_table(pa.Table.from_pylist(ctx[strategy]), path)
    try:
        ctx["comparison"] = ablation_qa.compare_decisions(ctx["root"], ["baseline", "candidate"])
    except AssertionError as error:
        ctx["error"] = str(error)


@then("evidence records the observed warm-up asymmetry")
def _warmup_evidence(ctx):
    """Report observed timestamps and counts from the supplied decision history."""
    result = ctx["comparison"]
    assert result["baseline_rows"] == 4
    assert result["candidate_rows"] == result["shared_timestamps"] == 2
    assert result["first_baseline_timestamp"] == str(ctx["baseline"][0]["timestamp"])
    assert result["first_candidate_timestamp"] == str(ctx["candidate"][0]["timestamp"])
    assert result["changed_f1_results"] == result["equal_strength_observations"] == 2


@then("the comparison rejects the premature candidate start")
def _reject_early(ctx):
    """The candidate must start strictly after the baseline."""
    assert ctx["error"] == "candidate warm-up no longer starts later"
    assert "comparison" not in ctx


@then("the comparison rejects the missing warm-up row asymmetry")
def _reject_count(ctx):
    """Candidate history must retain the missing early observations."""
    assert ctx["error"] == "candidate warm-up no longer omits early decisions"
    assert "comparison" not in ctx
