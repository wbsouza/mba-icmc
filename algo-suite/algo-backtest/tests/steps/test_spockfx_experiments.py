"""BDD for experiment preparation and bounded execution, without training or LEAN."""

import importlib.util
import json
import subprocess
import sys
import threading
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from algo_backtest.strategies import load_strategy_chain_config
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/spockfx_experiments.feature")
SETUP = Path(__file__).resolve().parents[3] / "experiments/spockfx-signals"


@pytest.fixture
def experiment(monkeypatch, tmp_path):
    """Load the runner with an isolated code tree so concurrent checkout edits cannot race it."""
    spec = importlib.util.spec_from_file_location("spockfx_experiment_runner", SETUP / "runner.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fingerprint_root = tmp_path / "fingerprint-code"
    fingerprint_root.mkdir()
    source = fingerprint_root / "source.py"
    source.write_text("VALUE = 1\n")

    def isolated_code_hashes():
        """Hash real fixture bytes while keeping production snapshot verification intact."""
        return {str(path): module.digest(path) for path in sorted(fingerprint_root.glob("*.py"))}

    monkeypatch.setattr(module, "code_hashes", isolated_code_hashes)
    return {"runner": module, "calls": [], "fingerprint_source": source}


@pytest.fixture(autouse=True)
def forbid_jobs(monkeypatch):
    """Any unmocked subprocess launch fails this offline test suite immediately."""

    def forbidden(*args, **kwargs):
        """Require each execution scenario to install its explicit child harness."""
        pytest.fail("Unexpected subprocess: experiment tests must not launch jobs")

    monkeypatch.setattr(subprocess, "run", forbidden)


@given("the tracked SpockFX experiment setup")
def tracked(experiment):
    """Read the explicit, versionable four-run plan."""
    experiment["plan"] = yaml.safe_load((SETUP / "plan.yaml").read_text())


@when("all four H4 strategy variants are resolved")
def variants(experiment):
    """Use the production configuration loader, not a duplicate parser."""
    experiment["configs"] = [
        load_strategy_chain_config(name, root=SETUP / "strategies")
        for name in experiment["plan"]["variants"]
    ]


@when("baseline and hybrid counterparts are resolved")
def counterpart_configs(experiment):
    """Resolve each declared family through the same production loader."""
    experiment["pairs"] = [
        (
            load_strategy_chain_config(base, root=SETUP / "strategies"),
            load_strategy_chain_config(hybrid, root=SETUP / "strategies"),
        )
        for base, hybrid in zip(
            experiment["plan"]["variants"], experiment["plan"]["hybrid_variants"], strict=True
        )
    ]


@then("each hybrid differs only by F4 news context and the F7 news family")
def comparable_pairs(experiment):
    """Detect accidental changes to timing, trading costs, risk or signal ablations."""
    assert len(experiment["pairs"]) == 4
    for baseline, hybrid in experiment["pairs"]:
        raw = json.loads(json.dumps(dict(hybrid.raw)))
        assert raw.pop("news_context") == {
            "event_intensity_veto_threshold": -0.5,
            "sentiment_direction_threshold": 0.15,
        }
        assert "f4_news_context" in raw["filters"]
        raw["filters"].remove("f4_news_context")
        assert raw["meta_learner"]["families"] == ["trend", "indicator", "pattern", "news"]
        raw["meta_learner"]["families"].remove("news")
        assert raw == dict(baseline.raw)


def month_range(cell: str) -> list[tuple[int, int]]:
    """Translate a table cell such as 2015-02..2015-09 into inclusive (year, month) pairs."""
    first, last = cell.split("..")
    year, month = (int(part) for part in first.split("-"))
    stop = tuple(int(part) for part in last.split("-"))
    months = []
    while (year, month) <= stop:
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def evaluation_weekdays(plan) -> list[date]:
    """List the Monday–Friday dates LEAN needs from the plan's evaluation window."""
    start, end = (date.fromisoformat(plan[key]) for key in ("test_start", "test_end"))
    days = (start + timedelta(offset) for offset in range((end - start).days + 1))
    return [day for day in days if day.weekday() < 5]


def write_fixture(path: Path, content: str) -> None:
    """Create one small stand-in partition, never a real market file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode())


def materialize(experiment, m1_months, gdelt_months=(), sentiment_months=()):
    """Create the named synthetic partitions plus every evaluation weekday's LEAN zip."""
    root, runner = experiment["input"], experiment["runner"]
    for year, month in m1_months:
        write_fixture(
            root / f"parquet/forex/EURUSD/m1/year={year}/month={month:02d}/data.parquet",
            f"fixture-month-{year}-{month}",
        )
    lean = root / "lean-data/forex/oanda/minute/eurusd"
    for day in evaluation_weekdays(experiment["plan"]):
        write_fixture(lean / f"{day:%Y%m%d}_quote.zip", "fixture-minute-data")
    for year, month in gdelt_months:
        path = runner.event_feature_path(root, "gdelt", year, month)
        write_fixture(path, f"news-fixture-{year}-{month}")
    for year, month in sentiment_months:
        write_fixture(runner.symbol_path(root, "lm", year, month), f"lm-{year}-{month}")
    experiment["input_hashes"] = {str(p): runner.digest(p) for p in root.rglob("*") if p.is_file()}


def write_xml_sources(experiment, sources: Path) -> None:
    """Stand in for the three SpockFX XML files the runner copies and hashes."""
    for name in experiment["runner"].XML_SOURCES:
        path = sources / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<beans><!-- source fixture only --></beans>")


@given("all required hybrid news sources")
def news_sources(experiment):
    """Supply file fixtures through October's final September decision boundary."""
    materialize(experiment, [], gdelt_months=month_range("2015-02..2015-10"))


@when("a fresh hybrid experiment output directory is prepared")
def prepare_hybrid(experiment):
    """Opt in to four hybrid arms without adding the baseline family to execution."""
    experiment["runner"].prepare(
        experiment["input"], experiment["output"], experiment["source"], mode="hybrid"
    )


@then("exactly four hybrid runs use the hybrid trainer and exhaustive source archives")
def hybrid_archives(experiment):
    """Every selected arm is independently auditable before the first child exists."""
    runner, root = experiment["runner"], experiment["output"]
    manifest = runner.read_json(root / "manifest.json")
    assert manifest["plan"]["mode"] == "hybrid"
    assert len(manifest["plan"]["variants"]) == 4
    assert manifest["news_sources"]["enabled"] is True
    assert len([p for p in manifest["inputs"] if "/events/" in p]) == 9
    assert manifest["news_sources"]["sentiment_files"] == []
    assert not any((root / name).exists() for name in experiment["plan"]["variants"])
    for name in manifest["plan"]["variants"]:
        run = root / name
        command = runner.read_json(run / "commands.json")["training"]
        assert Path(command[1]).name == "train_hybrid_meta_learner.py"
        assert command[command.index("--strategy") + 1] == name
        assert "news_context.event_intensity_veto_threshold" in (run / "parameters.md").read_text()
        assert (run / "source-mapping.md").is_file()
        assert (run / "source-configs" / name / "config.yaml").is_file()
        assert (run / "source-configs/hybrid/config.yaml").is_file()
        for source in runner.XML_SOURCES:
            assert (run / "source-xml" / source).read_bytes() == (
                experiment["source"] / source
            ).read_bytes()
    assert runner.verify_prepared(root)["plan"]["mode"] == "hybrid"


@when("hybrid preparation is requested without news sources")
def missing_news(experiment):
    """A hybrid mode never silently falls back to a price-only trainer or data stream."""
    with pytest.raises(ValueError, match="Missing hybrid GDELT") as error:
        prepare_hybrid(experiment)
    experiment["error"] = str(error.value)
    assert not experiment["output"].exists()


@when("combined experiment mode is requested")
def combined_mode(experiment):
    """Mode selection cannot expand into a combined eight- or sixteen-run sweep."""
    with pytest.raises(ValueError, match="mode must be baseline or hybrid") as error:
        experiment["runner"].select_plan("all")
    experiment["error"] = str(error.value)


@then("the variants form the disabled or talib by absent or present volume matrix")
def matrix(experiment):
    """Only detector and optional volume gate differ across the four arms."""
    configs = experiment["configs"]
    assert len(configs) == 4
    assert {(c.pattern.detector, c.volume_strength is not None) for c in configs} == {
        ("disabled", False),
        ("disabled", True),
        ("talib", False),
        ("talib", True),
    }
    normalized = []
    for config in configs:
        raw = json.loads(json.dumps(dict(config.raw)))
        raw["pattern"].pop("detector")
        volume = raw.pop("volume_strength", None)
        if volume:
            assert volume == {"lookback": 20, "min_relative_activity": 1.0}
        raw["filters"] = [name for name in raw["filters"] if name != "volume_strength"]
        normalized.append(raw)
    assert all(raw == normalized[0] for raw in normalized)


@then("each variant preserves the Dragon08 risk and exit mapping")
def mapping(experiment):
    """Check source values as risk fractions and original-position close fractions."""
    for config in experiment["configs"]:
        assert config.price_features.bar_minutes == 240
        assert config.risk_guard.portfolio_at_risk_cap == 0.18
        assert config.capital_mgmt.risk_per_trade == 0.03
        assert config.capital_mgmt.stop_loss_shrink == 0.5
        assert [(t.at_level_ratio, t.close_fraction) for t in config.capital_mgmt.targets] == [
            (4.0, 0.5),
            (6.0, 0.5),
        ]
        assert [(t.at_level_ratio, t.to_level_ratio) for t in config.capital_mgmt.trail_stops] == [
            (2.0, 0.1)
        ]


@then("every variant declares the research assumptions and exploratory windows")
def assumptions(experiment):
    """Keep research choices distinct from unsupported original detector semantics."""
    plan = experiment["plan"]
    assert plan["classification"] == "exploratory"
    assert [
        plan[k]
        for k in (
            "train_start",
            "train_end",
            "calibration_start",
            "calibration_end",
            "test_start",
            "test_end",
        )
    ] == ["2015-02-02", "2015-06-30", "2015-07-01", "2015-07-31", "2015-09-01", "2015-09-30"]
    for config in experiment["configs"]:
        assert config.capital_mgmt.stop_distance_source == "swing"
        assert config.f7.label_horizon_minutes == 240
        assert (config.f7.theta_high, config.f7.theta_low, config.f7.regime_gate) == (
            0.55,
            0.45,
            False,
        )
        assert config.execution.close_on_veto is False
    readme = (SETUP / "README.md").read_text()
    assert all(word in readme for word in ("offsetRisk", "SetupNow", "Dragon03", "proprietary"))


@given("explicit temporary input and SpockFX source directories")
def inputs(experiment, tmp_path):
    """Small fixture files exercise paths and hashes without touching real market inputs."""
    root, sources = tmp_path / "inputs", tmp_path / "xml"
    experiment.update(input=root, source=sources, output=tmp_path / "output")
    materialize(experiment, month_range("2015-02..2015-09"))
    write_xml_sources(experiment, sources)


@when("a fresh experiment output directory is prepared")
def prepare(experiment):
    """Preparation writes only the new explicit output tree."""
    experiment["runner"].prepare(experiment["input"], experiment["output"], experiment["source"])


@given("a prepared temporary SpockFX experiment")
def prepared(experiment, tmp_path):
    """Prepare the real archive using tiny market-source fixtures."""
    tracked(experiment)
    inputs(experiment, tmp_path)
    prepare(experiment)


@then("each run already has resolved settings provenance hashes parameters and pending status")
def archives(experiment):
    """No model hash is invented before training exists."""
    for name in experiment["plan"]["variants"]:
        run = experiment["output"] / name
        for filename in (
            "strategy-config.yaml",
            "strategy-config.json",
            "strategy-provenance.json",
            "provenance.json",
            "parameters.md",
            "commands.json",
        ):
            assert (run / filename).is_file()
        assert json.loads((run / "status.json").read_text())["state"] == "prepared"
        hashes = json.loads((run / "hashes.json").read_text())
        assert hashes["model_sha256"] is None
        assert hashes["code"]


@then("the archived commands use explicit strategy directory model output and September dates")
def explicit_commands(experiment):
    """The CLI trainer receives the declared variant and a private model destination."""
    for name in experiment["plan"]["variants"]:
        run = experiment["output"] / name
        command = json.loads((run / "commands.json").read_text())["training"]
        assert command[command.index("--strategy") + 1] == name
        assert command[command.index("--out") + 1] == str(run / "model.json")
        assert command[command.index("--strategies-dir") + 1] == str(run.parent / "strategies")
        plan = json.loads((run / "provenance.json").read_text())["plan"]
        assert (plan["test_start"], plan["test_end"]) == ("2015-09-01", "2015-09-30")


@then("no training or backtest process was launched")
def no_children(experiment):
    """Preparation does not call the execution path."""
    assert experiment["calls"] == []
    assert not (experiment["output"] / "execution-started.json").exists()


@then("the input files are unchanged")
def untouched(experiment):
    """Both contents and file inventory of the input root stay identical."""
    assert {
        str(p): experiment["runner"].digest(p)
        for p in experiment["input"].rglob("*")
        if p.is_file()
    } == experiment["input_hashes"]


@when(parsers.parse("preparation is requested with {problem}"))
def bad_prepare(experiment, problem):
    """Exercise refusal before any child can run."""
    if problem == "an existing output":
        experiment["output"].mkdir()
    elif problem == "output inside inputs":
        experiment["output"] = experiment["input"] / "output"
    elif problem == "inputs inside output":
        experiment["input"] = experiment["output"] / "nested-input"
    elif problem == "missing market inputs":
        experiment["input"] = experiment["input"] / "missing"
    elif problem == "a dangling output link":
        experiment["output"].symlink_to(experiment["output"].parent / "missing-output")
    else:
        experiment["source"] = experiment["source"] / "missing"
    with pytest.raises(ValueError) as error:
        prepare(experiment)
    experiment["error"] = str(error.value)


@then("preparation fails before launching a process")
def refused(experiment):
    """Unsafe input/output choices fail with an actionable explanation."""
    assert experiment["error"]
    assert experiment["calls"] == []


def harness(
    experiment,
    monkeypatch,
    failure=None,
    timeout=False,
    spawn_error=False,
    no_model=False,
    mutate=None,
    mutated_exit=0,
):
    """Stub only child processes; execute the actual runner state and archive logic."""

    def child(command, **kwargs):
        """Assert audit readiness at launch and emulate a trainer or engine exit."""
        stage = "training" if "--strategy" in command else "backtest"
        run = (
            Path(command[command.index("--out") + 1]).parent
            if stage == "training"
            else Path(command[command.index("--run-dir") + 1])
        )
        assert (run / "parameters.md").is_file()
        assert kwargs["env"]["ALGO_DATA_ROOT"] == str(experiment["input"])
        assert kwargs["env"]["LEAN_MAX_CONCURRENT"] == "6"
        assert kwargs["env"]["LEAN_CONTAINER_CPUS"] == "4"
        assert kwargs["env"]["LEAN_CONTAINER_MEM_LIMIT"] == "8g"
        experiment["calls"].append((stage, run))
        if timeout:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        if spawn_error:
            raise OSError("fixture executable unavailable")
        if stage == failure:
            return SimpleNamespace(returncode=17)
        if stage == "training" and not no_model:
            (run / "model.json").write_text('{"fixture_model": true}')
        elif stage == "backtest":
            assert json.loads((run / "hashes.json").read_text())["model_sha256"] == (
                experiment["runner"].digest(run / "model.json")
            )
            if mutate:
                targets = {
                    "input": Path(next(iter(experiment["input_hashes"]))),
                    "source": experiment["source"] / "deploy.xml",
                    "model": run / "model.json",
                }
                target = targets[mutate]
                experiment["changed_file"] = target
                experiment["original_hash"] = experiment["runner"].digest(target)
                target.write_bytes(target.read_bytes() + b"changed during child")
                return SimpleNamespace(returncode=mutated_exit)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(experiment["runner"].subprocess, "run", child)
    experiment["exit"] = experiment["runner"].execute(experiment["output"])


@when("all training and backtest children succeed in the runner harness")
def successful(experiment, monkeypatch):
    """Successful fake children prove the serial orchestration contract."""
    harness(experiment, monkeypatch)


@then("exactly four training and four backtest children ran sequentially")
def child_order(experiment):
    """No optional H1 family or parallel child is silently launched."""
    assert [stage for stage, _ in experiment["calls"]] == ["training", "backtest"] * 4
    assert experiment["exit"] == 0


@then("every run records success and the exact model hash")
def successful_archives(experiment):
    """Every child exit and model byte identity remains inspectable."""
    for name in experiment["plan"]["variants"]:
        run = experiment["output"] / name
        status = json.loads((run / "status.json").read_text())
        assert status == {"state": "succeeded", "exit_code": 0, "training": 0, "backtest": 0}
        assert json.loads((run / "hashes.json").read_text())["model_sha256"] == (
            experiment["runner"].digest(run / "model.json")
        )


@then("the final immutable check passes with archived source and input hashes")
def final_check_passed(experiment):
    """Success and child failure both leave an atomic byte-identity audit."""
    runner = experiment["runner"]
    report = runner.read_json(experiment["output"] / "final-input-check.json")
    manifest = runner.read_json(experiment["output"] / "manifest.json")
    assert report["ok"] is True
    assert report["mismatches"] == report["errors"] == []
    for group in ("code", "inputs", "source_xml"):
        assert set(report["groups"][group]) == set(manifest[group])
        for name, entry in report["groups"][group].items():
            assert entry["actual_sha256"] == entry["expected_sha256"] == manifest[group][name]


@when(parsers.parse("the first backtest child changes {target} and exits with code {code:d}"))
def child_mutates_input(experiment, monkeypatch, target, code):
    """Model a misbehaving child changing real fixture bytes before returning."""
    harness(experiment, monkeypatch, mutate=target, mutated_exit=code)


@then("the final immutable check names the changed file and both hashes")
def mutation_audit(experiment):
    """A successful child cannot hide changed source/input/model bytes."""
    runner = experiment["runner"]
    report = runner.read_json(experiment["output"] / "final-input-check.json")
    path = experiment["changed_file"]
    assert report["ok"] is False
    assert str(path) in report["mismatches"]
    entries = {name: item for group in report["groups"].values() for name, item in group.items()}
    assert entries[str(path)]["expected_sha256"] == experiment["original_hash"]
    assert entries[str(path)]["actual_sha256"] == runner.digest(path)
    assert entries[str(path)]["matches"] is False
    assert runner.read_json(experiment["output"] / "exit-status.json")["exit_code"] == 1
    assert not (experiment["output"] / "batch-02-before-input-check.json").exists()


@when(parsers.parse("the first {stage} child exits with code 17 in the runner harness"))
def failing(experiment, monkeypatch, stage):
    """A nonzero training or backtest exit stops the matrix."""
    harness(experiment, monkeypatch, failure=stage)


@when("the first training child times out in the runner harness")
def timed_out(experiment, monkeypatch):
    """Timeout is never interpreted as successful completion."""
    harness(experiment, monkeypatch, timeout=True)


@when("the first training child cannot start in the runner harness")
def spawn_failure(experiment, monkeypatch):
    """An unavailable executable records a useful failure code."""
    harness(experiment, monkeypatch, spawn_error=True)


@when("the trainer exits successfully without a model in the runner harness")
def missing_model(experiment, monkeypatch):
    """Exit zero alone cannot authorize backtesting an absent or bundled model."""
    harness(experiment, monkeypatch, no_model=True)


@when(parsers.parse("the backtest worker receives engine success {success} in the runner harness"))
def worker(experiment, monkeypatch, success):
    """Exercise the real worker using a fake engine, never a Docker container."""
    import algo_backtest.run as production

    run = experiment["output"] / experiment["plan"]["variants"][0]
    (run / "model.json").write_text('{"fixture_model":true}')
    runner = experiment["runner"]
    hashes = runner.read_json(run / "hashes.json")
    hashes["model_sha256"] = runner.digest(run / "model.json")
    runner.write_json(run / "hashes.json", hashes)

    def fake_engine(name, **kwargs):
        """Capture the production API's input/output contract."""
        experiment["engine_args"] = kwargs
        return SimpleNamespace(
            success=json.loads(success),
            error="fixture failure",
            raw_results_path=run / "results/raw.json",
            closed_trades=0,
        )

    def save_results(*args):
        """Record successful result reporting without fabricating LEAN artifacts."""
        experiment["saved_results"] = True

    monkeypatch.setattr(production, "validate_run_inputs", lambda *args, **kwargs: None)
    monkeypatch.setattr(production, "run_strategy", fake_engine)
    monkeypatch.setattr(runner, "archive_results", save_results)
    experiment["worker_exit"] = runner.backtest(run)


@then("the worker passes the explicit inputs and isolated results to the production API")
def worker_roots(experiment):
    """Read-only data sharing does not require a data-root symlink overlay."""
    kwargs = experiment["engine_args"]
    assert kwargs["data_root"] == experiment["input"]
    assert kwargs["results_dir"].is_relative_to(experiment["output"])
    assert kwargs["start"] == date(2015, 9, 1)
    assert kwargs["end"] == date(2015, 9, 30)
    assert kwargs["broker_adapter"] == "oanda"
    assert kwargs["params"] == {"cash": "10000"}


@then(parsers.parse("the worker reports engine success {success}"))
def worker_status(experiment, success):
    """Failed engines never emit a successful experiment report."""
    assert experiment["worker_exit"] == (0 if json.loads(success) else 1)
    assert experiment.get("saved_results", False) is json.loads(success)


@then(parsers.parse("the experiment exits with code {code:d} and launches no later run"))
def failure_exit(experiment, code):
    """The caller receives the failing child's exit code rather than a bare-wait success."""
    assert experiment["exit"] == code
    assert {run.name for _, run in experiment["calls"]} == {experiment["plan"]["variants"][0]}


@then("the failed run retains its settings and failure status")
def failure_archive(experiment):
    """Even failed work has prelaunch parameter provenance and an explicit exit code."""
    run = experiment["calls"][-1][1]
    status = json.loads((run / "status.json").read_text())
    assert status["state"] == "failed"
    assert status["exit_code"] == experiment["exit"]
    assert (run / "strategy-config.yaml").is_file()
    assert (run / "parameters.md").is_file()


@when("an archived strategy is changed before execution")
def drift(experiment):
    """Model a change to the snapshot the trainer would consume."""
    name = experiment["plan"]["variants"][0]
    (experiment["output"] / "strategies" / name / "config.yaml").write_text("changed: true\n")


@when("a fingerprinted fixture source changes before execution")
def fixture_source_drift(experiment):
    """Change one protected code byte without touching the shared checkout."""
    experiment["fingerprint_source"].write_text("VALUE = 2\n")


@when("an unrelated fixture document changes after preparation")
def unrelated_edit(experiment, tmp_path):
    """Represent another agent's documentation work outside the protected fixture tree."""
    (tmp_path / "parent-progress.md").write_text("Parent provenance work continues.\n")


@then("the prepared fingerprint still verifies")
def verify_isolated(experiment):
    """Run the real verifier; only code-file discovery is isolated in the fixture."""
    manifest = experiment["runner"].verify_prepared(experiment["output"])
    assert list(manifest["code"]) == [str(experiment["fingerprint_source"])]
    assert experiment["calls"] == []


@then("execution refuses the changed snapshot before launching a process")
def drift_refusal(experiment):
    """Hash verification happens before claiming or launching the experiment."""
    with pytest.raises(ValueError, match="snapshot changed"):
        experiment["runner"].execute(experiment["output"])
    assert experiment["calls"] == []


@when("execution is requested again")
def duplicate_execute(experiment):
    """Preserve successful outputs by refusing reuse."""
    experiment["previous_calls"] = len(experiment["calls"])
    with pytest.raises(ValueError, match="already executed"):
        experiment["runner"].execute(experiment["output"])


@then("the second execution is rejected before launching a process")
def no_repeat(experiment):
    """No additional trainer or engine is invoked against an existing run."""
    assert len(experiment["calls"]) == experiment["previous_calls"]


@then("the archived environment declares six LEAN slots with four CPUs and eight gigabytes each")
def archived_budget(experiment):
    """Plan and actual child environment record the same explicit provisional budget."""
    manifest = experiment["runner"].read_json(experiment["output"] / "manifest.json")
    assert manifest["plan"]["resources"]["workers"] == 1
    assert manifest["environment"]["LEAN_MAX_CONCURRENT"] == "6"
    assert manifest["environment"]["LEAN_CONTAINER_CPUS"] == "4"
    assert manifest["environment"]["LEAN_CONTAINER_MEM_LIMIT"] == "8g"


@then("training stays on the existing CPU backend with four numeric threads")
def training_budget(experiment):
    """Increasing resources does not enable GPU fitting or change model families."""
    manifest = experiment["runner"].read_json(experiment["output"] / "manifest.json")
    assert manifest["plan"]["resources"]["training_device"] == "cpu"
    for variable in (
        "OMP_NUM_THREADS",
        "OMP_THREAD_LIMIT",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
    ):
        assert manifest["environment"][variable] == "4"


@given("a temporary SpockFX experiment prepared for two workers")
def prepare_two_workers(experiment, tmp_path):
    """Freeze the concurrency choice before any execution archive is created."""
    tracked(experiment)
    inputs(experiment, tmp_path)
    experiment["runner"].prepare(
        experiment["input"], experiment["output"], experiment["source"], workers=2
    )


def parallel_harness(experiment, monkeypatch, fail=False):
    """Use a barrier to observe overlap deterministically without subprocesses or sleeps."""
    barrier, lock = threading.Barrier(2), threading.Lock()
    experiment.update(active=0, peak=0, finished=[], checkpoint_writers=[])
    write_json = experiment["runner"].write_json

    def record_write(path, value):
        """Observe checkpoint ownership without changing the atomic writer."""
        if path.name.endswith("input-check.json"):
            experiment["checkpoint_writers"].append(
                (path.name, threading.get_ident(), experiment["active"])
            )
        write_json(path, value)

    monkeypatch.setattr(experiment["runner"], "write_json", record_write)

    def cell(run_dir, manifest):
        """Each independent cell owns its audit files and rendezvous with its paired worker."""
        with lock:
            experiment["active"] += 1
            experiment["peak"] = max(experiment["peak"], experiment["active"])
        barrier.wait(timeout=5)
        code = 17 if fail and run_dir.name == manifest["plan"]["variants"][0] else 0
        experiment["runner"].write_json(
            run_dir / "status.json", {"state": "failed" if code else "succeeded", "exit_code": code}
        )
        with lock:
            experiment["active"] -= 1
            experiment["finished"].append(run_dir.name)
        return code

    monkeypatch.setattr(experiment["runner"], "execute_run", cell)
    experiment["exit"] = experiment["runner"].execute(experiment["output"], workers=2)


@when("two-worker execution is observed with controlled independent cells")
def run_two_workers(experiment, monkeypatch):
    """Exercise the real bounded scheduler with two pairs of independent cells."""
    parallel_harness(experiment, monkeypatch)


@then("no more than two cells overlap and all four are individually recorded")
def bounded_workers(experiment):
    """Concurrency reaches two without exceeding the archived budget."""
    assert experiment["peak"] == 2
    assert experiment["active"] == 0
    assert set(experiment["finished"]) == set(experiment["plan"]["variants"])
    assert experiment["exit"] == 0
    for name in experiment["finished"]:
        status = experiment["runner"].read_json(experiment["output"] / name / "status.json")
        assert status["state"] == "succeeded"


@then("each pair has parent-owned before and after immutable checks")
def parent_checkpoints(experiment):
    """Cells never write shared parent checkpoints, and verification waits for both exits."""
    assert experiment["checkpoint_writers"] == [
        (name, threading.get_ident(), 0)
        for name in (
            "batch-01-before-input-check.json",
            "batch-01-after-input-check.json",
            "batch-02-before-input-check.json",
            "batch-02-after-input-check.json",
            "final-input-check.json",
        )
    ]


@when("one cell in the first pair fails with code 17")
def failing_pair(experiment, monkeypatch):
    """Finish already-started work but never submit the next pair after a failure."""
    parallel_harness(experiment, monkeypatch, fail=True)


@then("both started cells finish and no second pair starts")
def drained_failure(experiment):
    """A peer's completion cannot mask another cell's failing return code."""
    assert experiment["exit"] == 17
    assert experiment["active"] == 0
    assert set(experiment["finished"]) == set(experiment["plan"]["variants"][:2])
    result = experiment["runner"].read_json(experiment["output"] / "exit-status.json")
    assert sorted(result["batch_outcomes"].values()) == [0, 17]
    for name in experiment["plan"]["variants"][2:]:
        assert (
            experiment["runner"].read_json(experiment["output"] / name / "status.json")["state"]
            == "prepared"
        )


@when("execution requests two workers against the one-worker plan")
def override_workers(experiment):
    """Execution cannot rewrite the resource provenance of a prepared experiment."""
    with pytest.raises(ValueError, match="Worker budget differs") as error:
        experiment["runner"].execute(experiment["output"], workers=2)
    experiment["error"] = str(error.value)


@then("execution rejects the changed worker budget before launching a process")
def frozen_workers(experiment):
    """A rejected execution override leaves the plan unclaimed."""
    assert experiment["error"]
    assert not (experiment["output"] / "execution-started.json").exists()


@when(parsers.parse("preparation requests worker count {workers}"))
def invalid_workers(experiment, workers):
    """Reject booleans, zero and unsupported extra workers before writing output."""
    with pytest.raises(ValueError) as error:
        experiment["runner"].prepare(
            experiment["input"],
            experiment["output"],
            experiment["source"],
            workers=json.loads(workers),
        )
    experiment["error"] = str(error.value)
    assert not experiment["output"].exists()


@given(parsers.parse("the registered plan {plan}"))
def registered_plan(experiment, tmp_path, plan):
    """Read one of the two tracked plans and lay out fresh disjoint roots for it."""
    experiment["plan_path"] = SETUP / plan
    experiment["plan"] = yaml.safe_load(experiment["plan_path"].read_text())
    experiment.update(input=tmp_path / "inputs", source=tmp_path / "xml", output=tmp_path / "out")
    write_xml_sources(experiment, experiment["source"])


@given(
    parsers.parse(
        "synthetic inputs for M1 months {m1}, the plan's evaluation weekdays, "
        "GDELT months {gdelt} and sentiment months {sentiment}"
    )
)
def span_inputs(experiment, m1, gdelt, sentiment):
    """Create exactly the partitions the outline names, so nothing else can be required."""
    materialize(experiment, month_range(m1), month_range(gdelt), month_range(sentiment))


@when("the plan's hybrid input files are derived")
def derive_inputs(experiment):
    """Use the production derivation in hybrid mode so news partitions are included."""
    runner = experiment["runner"]
    plan = runner.select_plan("hybrid", experiment["plan_path"])
    experiment["derived"] = runner.input_files(experiment["input"], plan)


@then("the derived input files are exactly the synthetic inputs")
def derived_matches(experiment):
    """Neither a missing nor an unrequested partition is tolerated."""
    assert {str(p) for p in experiment["derived"]} == set(experiment["input_hashes"])


@then(parsers.parse("exactly {zips:d} LEAN weekday zips are required"))
def zip_count(experiment, zips):
    """The glob of same-span zips adds nothing beyond the required weekdays."""
    assert sum(p.suffix == ".zip" for p in experiment["derived"]) == zips


@given(parsers.parse("a plan copied from plan.yaml with {change}"))
def copied_plan(experiment, tmp_path, change):
    """Write a variant plan: '<key> removed' drops the key, "<key> 'value'" replaces it."""
    plan = yaml.safe_load((SETUP / "plan.yaml").read_text())
    key, value = change.split(" ", 1)
    if value == "removed":
        del plan[key]
    else:
        plan[key] = value.strip("'")
    experiment["plan_path"] = tmp_path / "plan-copy.yaml"
    experiment["plan_path"].write_text(yaml.safe_dump(plan))


@when("a fresh experiment output directory is prepared from the copied plan")
def prepare_copied(experiment):
    """Prepare through the explicit plan path instead of the bundled pilot."""
    experiment["runner"].prepare(
        experiment["input"],
        experiment["output"],
        experiment["source"],
        plan_path=experiment["plan_path"],
    )


@when("preparation is requested from the copied plan")
def refuse_copied(experiment):
    """A malformed plan is refused before any output directory exists."""
    with pytest.raises(ValueError) as error:
        prepare_copied(experiment)
    experiment["error"] = str(error.value)
    assert not experiment["output"].exists()


@then(parsers.parse('preparation fails before launching a process with "{expected}"'))
def refused_with(experiment, expected):
    """The refusal text names the key or the offending pair and the fix."""
    assert experiment["error"] == expected
    assert experiment["calls"] == []


@then(
    parsers.parse(
        "every archived training command passes --test-end {heldout} "
        "while LEAN keeps {start} to {end}"
    )
)
def heldout_commands(experiment, heldout, start, end):
    """The trainer's held-out partition ends at the registered span, not the LEAN window."""
    manifest = experiment["runner"].read_json(experiment["output"] / "manifest.json")
    plan = manifest["plan"]
    assert (plan["heldout_end"], plan["test_start"], plan["test_end"]) == (heldout, start, end)
    for name in plan["variants"]:
        run = experiment["output"] / name
        command = json.loads((run / "commands.json").read_text())["training"]
        assert command[command.index("--test-end") + 1] == heldout
        assert command[command.index("--validation-end") + 1] == plan["calibration_end"]
        provenance = json.loads((run / "provenance.json").read_text())["plan"]
        assert (provenance["test_start"], provenance["test_end"]) == (start, end)


@when(parsers.parse("the runner command line prepares with --plan {plan}"))
def cli_prepare(experiment, monkeypatch, plan):
    """Drive the real argument parser; only the plan option departs from the pilot command."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "runner.py",
            "prepare",
            "--input-root",
            str(experiment["input"]),
            "--output-root",
            str(experiment["output"]),
            "--spockfx-conf",
            str(experiment["source"]),
            "--plan",
            str(SETUP / plan),
        ],
    )
    assert experiment["runner"].main() == 0


@then("the manifest archives the plan path and its SHA-256 beside the XML sources")
def plan_archived(experiment):
    """The chosen plan is hashed like the XML sources, copied, and re-verified at execution."""
    runner, root = experiment["runner"], experiment["output"]
    manifest = runner.read_json(root / "manifest.json")
    path = experiment["plan_path"]
    assert manifest["plan_source"] == {str(path): runner.digest(path)}
    xml = {str(experiment["source"] / name) for name in runner.XML_SOURCES}
    assert set(manifest["source_xml"]) == xml
    assert (root / "plan.yaml").read_bytes() == path.read_bytes()
    assert runner.verify_prepared(root)["plan_source"] == manifest["plan_source"]
    parameters = root / manifest["plan"]["variants"][0] / "parameters.md"
    assert "2015-2016 window" in parameters.read_text()
