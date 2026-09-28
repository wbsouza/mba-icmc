"""Prepare an auditable H4 matrix; execute it only through an explicit subcommand."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from algo_backtest.strategies import (
    explain_lines,
    load_strategy_chain_config,
    resolved_yaml,
    strategies_root,
)
from algo_core.atomicio import write_text_atomic
from algo_core.instrument import build_instrument
from algo_core.layout import lean_data_dir_for, price_path_for
from algo_score.events.paths import feature_path as event_feature_path
from algo_score.paths import symbol_path

HERE = Path(__file__).resolve().parent
SUITE = HERE.parents[1]
XML_SOURCES = ("deploy.xml", "strategies/dragon.xml", "strategies/setupnow.xml")
DEFAULT_PLAN = HERE / "plan.yaml"
DATE_KEYS = (
    "train_start",
    "train_end",
    "calibration_start",
    "calibration_end",
    "heldout_end",
    "test_start",
    "test_end",
)
# Each triple is checked in order; the first violated pair names the refusal. The held-out
# span may end before the evaluation window (broad plan) or overlap it (pilot plan).
DATE_ORDER = (
    ("train_start", "<", "train_end"),
    ("train_end", "<", "calibration_start"),
    ("calibration_start", "<=", "calibration_end"),
    ("calibration_end", "<", "heldout_end"),
    ("calibration_end", "<", "test_start"),
    ("heldout_end", "<=", "test_end"),
    ("test_start", "<=", "test_end"),
)
MISSING_HELDOUT = (
    "Plan is missing required key heldout_end; add heldout_end: 'YYYY-MM-DD' "
    "(the trainer's held-out partition end) to the plan and prepare again."
)


def digest(path: Path) -> str:
    """Hash exact bytes without loading a whole market partition into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value: object) -> None:
    """Replace one local audit document atomically."""
    write_text_atomic(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    """Read an audit object, refusing malformed documents."""
    document = json.loads(path.read_text())
    if not isinstance(document, dict):
        raise ValueError(f"Expected an object in {path}; prepare a fresh experiment.")
    return document


def code_hashes() -> dict[str, str]:
    """Fingerprint current code, including uncommitted and untracked source files."""
    roots = [SUITE / member for member in ("algo-core", "algo-score", "algo-backtest")]
    files = {SUITE / "pyproject.toml", SUITE / "uv.lock"}
    for root in [*roots, HERE]:
        files.update(
            p
            for p in root.rglob("*")
            if p.is_file()
            and p.suffix in {".py", ".yaml", ".toml", ".md"}
            and not {".venv", "__pycache__", "mutants", "build"}.intersection(p.parts)
        )
    return {str(p): digest(p) for p in sorted(files)}


def plan_dates(plan: dict[str, Any]) -> dict[str, date]:
    """Parse every registered window boundary; a missing held-out end is refused by name."""
    if "heldout_end" not in plan:
        raise ValueError(MISSING_HELDOUT)
    return {key: date.fromisoformat(str(plan[key])) for key in DATE_KEYS}


def validate_dates(dates: dict[str, date]) -> None:
    """Refuse misordered windows, naming the first offending pair and its required order."""
    for first, operator, second in DATE_ORDER:
        earlier, later = dates[first], dates[second]
        if not (earlier < later if operator == "<" else earlier <= later):
            word = "before" if operator == "<" else "on or before"
            raise ValueError(
                f"Plan dates out of order: {first} {earlier} must be {word} "
                f"{second} {later}; fix the plan."
            )


def load_plan(path: Path) -> dict[str, Any]:
    """Read one registered plan document and validate its window boundaries."""
    document = yaml.safe_load(path.read_text())
    if not isinstance(document, dict):
        raise ValueError(f"Expected a mapping in {path}; register a complete plan.")
    plan: dict[str, Any] = document
    validate_dates(plan_dates(plan))
    return plan


def select_plan(mode: str, plan_path: Path = DEFAULT_PLAN) -> dict[str, Any]:
    """Select exactly one four-cell family; combined/timeframe sweeps are unsupported."""
    if mode not in ("baseline", "hybrid"):
        raise ValueError(
            "mode must be baseline or hybrid; prepare each four-run family separately."
        )
    plan = load_plan(plan_path)
    hybrids = plan.pop("hybrid_variants")
    if mode == "hybrid":
        plan["variants"] = hybrids
    plan["mode"] = mode
    return plan


def resource_budget(plan: dict[str, Any], workers: int | None = None) -> dict[str, Any]:
    """Validate explicit limits; GPU and backend changes require a separate parity review."""
    budget: dict[str, Any] = dict(plan["resources"])
    if workers is not None:
        budget["workers"] = workers
    for key in (
        "workers",
        "lean_max_concurrent",
        "lean_container_cpus",
        "lean_container_mem_gib",
        "training_numeric_threads",
    ):
        if type(budget[key]) is not int or budget[key] < 1:
            raise ValueError(f"resources.{key} must be a positive integer; fix the plan.")
    if budget["workers"] not in (1, 2) or budget["workers"] > budget["lean_max_concurrent"]:
        raise ValueError(
            "workers must be 1 or 2 and fit the LEAN slot budget; prepare a fresh plan."
        )
    if budget["training_device"] != "cpu":
        raise ValueError(
            "training_device must remain cpu until GPU model/backend parity is reviewed."
        )
    return budget


def months_between(start: date, end: date) -> list[tuple[int, int]]:
    """List (year, month) partitions from the month of ``start`` through the month of ``end``."""
    months: list[tuple[int, int]] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def following_month(day: date) -> date:
    """First day of the next month: where the last evaluation bar's decision minute lands."""
    return date(day.year + (day.month == 12), day.month % 12 + 1, 1)


def weekdays_between(start: date, end: date) -> list[date]:
    """List every Monday–Friday from ``start`` through ``end`` inclusive."""
    days = (start + timedelta(offset) for offset in range((end - start).days + 1))
    return [day for day in days if day.weekday() < 5]


def hybrid_input_files(root: Path, plan: dict[str, Any]) -> list[Path]:
    """Require GDELT features through the month after the last bar; hash optional sentiment."""
    dates = plan_dates(plan)
    boundary = following_month(dates["test_end"])
    events = [
        event_feature_path(root, "gdelt", year, month)
        for year, month in months_between(dates["train_start"], boundary)
    ]
    missing = [str(p) for p in events if not p.is_file()]
    if missing:
        raise ValueError(
            f"Missing hybrid GDELT sources: {missing}; build event features separately."
        )
    sentiment = [
        symbol_path(root, "lm", year, month)
        for year, month in months_between(dates["test_start"], boundary)
    ]
    return events + [p for p in sentiment if p.is_file()]


def input_files(root: Path, plan: dict[str, Any]) -> list[Path]:
    """Require the plan's M1 months and every evaluation weekday zip; add same-span extras."""
    dates = plan_dates(plan)
    instrument = build_instrument(plan["symbol"])
    paths = [
        price_path_for(root, instrument, "m1", year, month)
        for year, month in months_between(dates["train_start"], dates["test_end"])
    ]
    lean = lean_data_dir_for(root, instrument, "minute")
    evaluation = (dates["test_start"], dates["test_end"])
    paths += [lean / f"{day:%Y%m%d}_quote.zip" for day in weekdays_between(*evaluation)]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"Missing explicit market inputs: {missing}; materialize separately.")
    extras = [
        path
        for year, month in months_between(*evaluation)
        for path in lean.glob(f"{year:04d}{month:02d}*_quote.zip")
    ]
    news = hybrid_input_files(root, plan) if plan["mode"] == "hybrid" else []
    return sorted(set(paths + extras + news))


def validate_roots(
    input_root: Path, output_root: Path, source_conf: Path, plan: dict[str, Any]
) -> list[Path]:
    """Refuse overlap, reuse, absent XML, and absent inputs before creating output."""
    if output_root.exists() or output_root.is_symlink():
        raise ValueError("Output already exists; choose a fresh experiment output directory.")
    if output_root.is_relative_to(input_root) or input_root.is_relative_to(output_root):
        raise ValueError("Input and output roots overlap; choose disjoint directories.")
    if output_root.is_relative_to(source_conf) or source_conf.is_relative_to(output_root):
        raise ValueError("XML source and output roots overlap; choose disjoint directories.")
    for name in XML_SOURCES:
        if not (source_conf / name).is_file():
            raise ValueError(f"Missing XML source {source_conf / name}; supply --spockfx-conf.")
    return input_files(input_root, plan)


def child_environment(input_root: Path, budget: dict[str, Any]) -> dict[str, str]:
    """Supply explicit data/resource settings without inherited trading overrides."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ALGO_", "LEAN_"))}
    env.update(
        ALGO_DATA_ROOT=str(input_root),
        LEAN_MAX_CONCURRENT=str(budget["lean_max_concurrent"]),
        LEAN_CONTAINER_MEM_LIMIT=f"{budget['lean_container_mem_gib']}g",
        LEAN_CONTAINER_CPUS=str(budget["lean_container_cpus"]),
        OMP_NUM_THREADS=str(budget["training_numeric_threads"]),
        OMP_THREAD_LIMIT=str(budget["training_numeric_threads"]),
        OPENBLAS_NUM_THREADS=str(budget["training_numeric_threads"]),
        MKL_NUM_THREADS=str(budget["training_numeric_threads"]),
        PYTHONHASHSEED="0",
        PYTHONDONTWRITEBYTECODE="1",
    )
    return env


def commands(run_dir: Path, plan: dict[str, Any]) -> dict[str, list[str]]:
    """Construct explicit argument vectors, never shell text or bundled-model output."""
    strategies = run_dir.parent / "strategies"
    train = [
        sys.executable,
        str(SUITE / f"algo-backtest/scripts/train_{plan['mode']}_meta_learner.py"),
        "--strategy",
        run_dir.name,
        "--strategies-dir",
        str(strategies),
        "--symbol",
        plan["symbol"],
        "--from",
        plan["train_start"],
        "--train-end",
        plan["train_end"],
        "--validation-end",
        plan["calibration_end"],
        "--test-end",
        plan["heldout_end"],
        "--out",
        str(run_dir / "model.json"),
    ]
    return {
        "training": train,
        "backtest": [
            sys.executable,
            str(HERE / "runner.py"),
            "_backtest",
            "--run-dir",
            str(run_dir),
        ],
    }


def archive_run(run_dir: Path, manifest: dict[str, Any]) -> None:
    """Write the full filter settings and provenance before a child can be launched."""
    run_dir.mkdir()
    archive_sources(run_dir)
    config = load_strategy_chain_config(run_dir.name, root=HERE / "strategies")
    frozen = run_dir.parent / "strategies" / run_dir.name / "config.yaml"
    write_text_atomic(frozen, resolved_yaml(config))
    write_text_atomic(run_dir / "strategy-config.yaml", resolved_yaml(config))
    write_json(run_dir / "strategy-config.json", dict(config.raw))
    write_json(run_dir / "strategy-provenance.json", dict(config.provenance))
    write_json(run_dir / "provenance.json", manifest)
    write_json(run_dir / "commands.json", commands(run_dir, manifest["plan"]))
    write_json(
        run_dir / "status.json",
        {"state": "prepared", "exit_code": None, "training": None, "backtest": None},
    )
    write_json(
        run_dir / "hashes.json",
        {"code": manifest["code"], "model_sha256": None, "model_state": "not_trained"},
    )
    parameters = "\n".join(explain_lines(config))
    write_text_atomic(
        run_dir / "parameters.md",
        f"# {run_dir.name}\n\n"
        f"Exploratory, previously inspected {window_label(manifest['plan'])} window; "
        "not confirmatory.\n\n"
        "See provenance.json for exact windows, inputs and XML source hashes.\n\n"
        "See source-mapping.md for every XML mapping and unsupported semantic; "
        "source-configs/ and source-xml/ preserve the original files.\n\n"
        f"```text\n{parameters}\n```\n\n"
        f"```json\n{json.dumps(manifest['plan'], indent=2)}\n```\n",
    )


def window_label(plan: dict[str, Any]) -> str:
    """Name the calendar years a plan spans, from training start to evaluation end."""
    dates = plan_dates(plan)
    first, last = dates["train_start"].year, dates["test_end"].year
    return str(first) if first == last else f"{first}-{last}"


def archive_sources(run_dir: Path) -> None:
    """Keep original YAML inheritance and XML/source explanations beside every run."""
    shutil.copyfile(HERE / "README.md", run_dir / "source-mapping.md")
    shutil.copytree(run_dir.parent / "source-xml", run_dir / "source-xml")
    sources = {run_dir.name: HERE / "strategies" / run_dir.name / "config.yaml"}
    for name in ("baseline", "hybrid"):
        sources[name] = strategies_root() / name / "config.yaml"
    for name, source in sources.items():
        target = run_dir / "source-configs" / name / "config.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def prepare(
    input_root: Path,
    output_root: Path,
    source_conf: Path,
    *,
    mode: str = "baseline",
    workers: int | None = None,
    plan_path: Path = DEFAULT_PLAN,
) -> Path:
    """Prepare four runs without training, launching LEAN, or mutating input trees."""
    if output_root.is_symlink():
        raise ValueError("Output is a symlink; choose a fresh experiment output directory.")
    input_root, output_root, source_conf, plan_path = (
        path.resolve() for path in (input_root, output_root, source_conf, plan_path)
    )
    plan = select_plan(mode, plan_path)
    plan["resources"] = resource_budget(plan, workers)
    paths = validate_roots(input_root, output_root, source_conf, plan)
    for name in plan["variants"]:
        load_strategy_chain_config(name, root=HERE / "strategies")
    manifest = {
        "plan": plan,
        "input_root": str(input_root),
        "code": code_hashes(),
        "inputs": {str(p): digest(p) for p in paths},
        "source_xml": {str(source_conf / n): digest(source_conf / n) for n in XML_SOURCES},
        "plan_source": {str(plan_path): digest(plan_path)},
        "prepared_at": datetime.now(UTC).isoformat(),
        "packages": {
            p: importlib.metadata.version(p)
            for p in ("algo-backtest", "TA-Lib", "lightgbm", "scikit-learn")
        },
        "environment": {
            k: v
            for k, v in child_environment(input_root, plan["resources"]).items()
            if k.startswith(("ALGO_", "LEAN_"))
            or k.endswith("NUM_THREADS")
            or k in {"PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE", "OMP_THREAD_LIMIT"}
        },
        "news_sources": {
            "enabled": mode == "hybrid",
            "sentiment_files": [str(p) for p in paths if "sentiment" in p.parts],
            "training_sentiment": "always_missing_in_current_hybrid_trainer",
        },
    }
    output_root.mkdir(parents=True, exist_ok=False)
    write_json(output_root / "manifest.json", manifest)
    shutil.copyfile(HERE / "README.md", output_root / "README.md")
    shutil.copyfile(plan_path, output_root / "plan.yaml")
    for name in XML_SOURCES:
        target = output_root / "source-xml" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_conf / name, target)
    for name in plan["variants"]:
        archive_run(output_root / name, manifest)
    snapshots = [p for p in output_root.rglob("*") if p.is_file()]
    write_json(output_root / "prepared-hashes.json", {str(p): digest(p) for p in snapshots})
    return output_root


def verify_prepared(output_root: Path) -> dict[str, Any]:
    """Fail before launch on changed code, input bytes, or prepared settings."""
    manifest = read_json(output_root / "manifest.json")
    fingerprints = {
        **manifest["code"],
        **manifest["inputs"],
        **read_json(output_root / "prepared-hashes.json"),
    }
    for name, expected in fingerprints.items():
        path = Path(name)
        if not path.is_file() or digest(path) != expected:
            raise ValueError(
                f"Prepared snapshot changed: {path}; prepare a fresh output directory."
            )
    if code_hashes() != manifest["code"]:
        raise ValueError("Code file set changed; prepare a fresh output directory.")
    current_inputs = input_files(Path(manifest["input_root"]), manifest["plan"])
    if {str(p) for p in current_inputs} != set(manifest["inputs"]):
        raise ValueError("Input file set changed; prepare a fresh output directory.")
    return manifest


def run_child(run_dir: Path, stage: str, manifest: dict[str, Any]) -> int:
    """Wait for this exact child, record its exit, and fail closed on timeout or spawn failure."""
    status = read_json(run_dir / "status.json")
    status.update(state=f"{stage}_running", exit_code=None)
    write_json(run_dir / "status.json", status)
    timeout_key = "train_timeout_seconds" if stage == "training" else "backtest_timeout_seconds"
    timeout = manifest["plan"][timeout_key] + (60 if stage == "backtest" else 0)
    with (run_dir / f"{stage}.log").open("x") as log:
        try:
            result = subprocess.run(
                read_json(run_dir / "commands.json")[stage],
                cwd=SUITE,
                env=child_environment(Path(manifest["input_root"]), manifest["plan"]["resources"]),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
            code = result.returncode
        except subprocess.TimeoutExpired:
            log.write(f"Child exceeded {timeout} seconds.\n")
            code = 124
        except OSError as exc:
            log.write(f"Cannot start child: {exc}\n")
            code = 127
    status[stage] = code
    status.update(state=f"{stage}_complete" if code == 0 else "failed", exit_code=code)
    write_json(run_dir / "status.json", status)
    return code


def execute_run(run_dir: Path, manifest: dict[str, Any]) -> int:
    """Train a separate model, archive its hash, then backtest this variant sequentially."""
    code = run_child(run_dir, "training", manifest)
    if code:
        return code
    model = run_dir / "model.json"
    if not model.is_file():
        status = read_json(run_dir / "status.json")
        status.update(state="failed", exit_code=1, error="Trainer produced no model.json")
        write_json(run_dir / "status.json", status)
        return 1
    hashes = read_json(run_dir / "hashes.json")
    hashes.update(model_sha256=digest(model), model_state="trained")
    write_json(run_dir / "hashes.json", hashes)
    code = run_child(run_dir, "backtest", manifest)
    if code == 0:
        status = read_json(run_dir / "status.json")
        status.update(state="succeeded")
        write_json(run_dir / "status.json", status)
    return code


def execute_cell(run_dir: Path, manifest: dict[str, Any]) -> int:
    """Record unexpected cell failures so every submitted worker has a durable exit."""
    try:
        return execute_run(run_dir, manifest)
    except Exception as exc:
        status = read_json(run_dir / "status.json")
        status.update(state="failed", exit_code=1, error=str(exc))
        write_json(run_dir / "status.json", status)
        return 1


def execute_batch(runs: list[Path], manifest: dict[str, Any]) -> list[tuple[str, int]]:
    """Wait for each submitted cell; never queue another pair while this pair is running."""
    with ThreadPoolExecutor(max_workers=len(runs)) as pool:
        pending = [(run.name, pool.submit(execute_cell, run, manifest)) for run in runs]
        return [(name, future.result()) for name, future in pending]


def check_hashes(expected: dict[str, str]) -> dict[str, Any]:
    """Record expected and observed bytes, including unreadable or removed files."""
    checked: dict[str, Any] = {}
    for name, sha256 in expected.items():
        try:
            actual, error = digest(Path(name)), None
        except OSError as exc:
            actual, error = None, str(exc)
        checked[name] = {
            "expected_sha256": sha256,
            "actual_sha256": actual,
            "matches": actual == sha256,
            "error": error,
        }
    return checked


def model_hashes(output_root: Path, manifest: dict[str, Any]) -> dict[str, str]:
    """Read sealed per-cell model identities only after all active cells have joined."""
    models: dict[str, str] = {}
    for name in manifest["plan"]["variants"]:
        run = output_root / name
        expected = read_json(run / "hashes.json")["model_sha256"]
        if expected is not None:
            models[str(run / "model.json")] = expected
    return models


def immutable_check(output_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Compare source/input identities with the manifest, never mutable prepared-status hashes."""
    errors = []
    groups = {
        key: check_hashes(manifest[key]) for key in ("code", "inputs", "source_xml", "plan_source")
    }
    try:
        groups["models"] = check_hashes(model_hashes(output_root, manifest))
        if code_hashes() != manifest["code"]:
            errors.append("Code file set or bytes changed since preparation.")
        current = input_files(Path(manifest["input_root"]), manifest["plan"])
        if {str(p) for p in current} != set(manifest["inputs"]):
            errors.append("Input file set changed since preparation.")
    except (OSError, ValueError, KeyError) as exc:
        errors.append(str(exc))
    mismatches = [
        name for group in groups.values() for name, item in group.items() if not item["matches"]
    ]
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "ok": not errors and not mismatches,
        "groups": groups,
        "mismatches": mismatches,
        "errors": errors,
    }


def checkpoint(output_root: Path, manifest: dict[str, Any], name: str) -> bool:
    """Write one atomic parent-owned checkpoint after every worker in a batch has joined."""
    report = immutable_check(output_root, manifest)
    write_json(output_root / name, report)
    return bool(report["ok"])


def run_batches(output_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Check immutable inputs before and after each bounded batch, stopping on any drift."""
    names, workers = manifest["plan"]["variants"], manifest["plan"]["resources"]["workers"]
    for offset in range(0, len(names), workers):
        label = f"batch-{offset // workers + 1:02d}"
        if not checkpoint(output_root, manifest, f"{label}-before-input-check.json"):
            return {
                "exit_code": 1,
                "error": "Immutable inputs changed before batch",
                "batch": label,
            }
        runs = [output_root / name for name in names[offset : offset + workers]]
        outcomes = execute_batch(runs, manifest)
        if not checkpoint(output_root, manifest, f"{label}-after-input-check.json"):
            return {
                "exit_code": 1,
                "error": "Immutable inputs changed during batch",
                "batch_outcomes": dict(outcomes),
                "batch": label,
            }
        failures = [(name, code) for name, code in outcomes if code]
        if failures:
            name, code = failures[0]
            return {"exit_code": code, "failed_run": name, "batch_outcomes": dict(outcomes)}
    return {"exit_code": 0}


def execute(output_root: Path, *, workers: int | None = None) -> int:
    """Run bounded independent cells using only the prelaunch archived resource budget."""
    output_root = output_root.resolve()
    if (output_root / "execution-started.json").exists():
        raise ValueError("Output already executed or claimed; prepare a fresh experiment.")
    manifest = verify_prepared(output_root)
    budget = resource_budget(manifest["plan"])
    if workers is not None and resource_budget(manifest["plan"], workers) != budget:
        raise ValueError(
            "Worker budget differs from the prepared plan; prepare a fresh output root."
        )
    with (output_root / "execution-started.json").open("x") as stream:
        json.dump(
            {"started_at": datetime.now(UTC).isoformat(), "pid": os.getpid(), "resources": budget},
            stream,
        )
    try:
        result = run_batches(output_root, manifest)
    except Exception as exc:
        result = {"exit_code": 1, "error": str(exc)}
    if not checkpoint(output_root, manifest, "final-input-check.json"):
        result.update(exit_code=1, error="Final immutable source/input/model verification failed")
    write_json(output_root / "exit-status.json", result)
    return int(result["exit_code"])


def backtest(run_dir: Path) -> int:
    """Use the existing API's separate results_dir so the input root stays read-only."""
    from algo_backtest.run import news_coverage_errors, run_strategy, validate_run_inputs

    manifest = read_json(run_dir / "provenance.json")
    plan = manifest["plan"]
    start, end = date.fromisoformat(plan["test_start"]), date.fromisoformat(plan["test_end"])
    model = run_dir / "model.json"
    if digest(model) != read_json(run_dir / "hashes.json")["model_sha256"]:
        raise ValueError("Model changed after training; prepare a fresh experiment.")
    strategies = run_dir.parent / "strategies"
    params = {"cash": str(plan["cash"])}
    validate_run_inputs(run_dir.name, params, start, end, model, strategies_root=strategies)
    problems = news_coverage_errors(
        run_dir.name,
        Path(manifest["input_root"]),
        plan["symbol"],
        start,
        end,
        strategies_root=strategies,
    )
    if problems:
        raise ValueError(f"Hybrid news coverage failed: {problems}; rebuild sources separately.")
    results = run_dir / "results"
    results.mkdir(exist_ok=False)
    result = run_strategy(
        run_dir.name,
        data_root=Path(manifest["input_root"]),
        instrument=build_instrument(plan["symbol"]),
        start=start,
        end=end,
        params=params,
        results_dir=results,
        timeout=plan["backtest_timeout_seconds"],
        broker_adapter=plan["broker_adapter"],
        model=model,
        strategies_root=strategies,
    )
    if not result.success:
        print(f"Backtest failed: {result.error}", file=sys.stderr)
        return 1
    archive_results(run_dir, result.raw_results_path, result.closed_trades, plan)
    return 0


def archive_results(run_dir: Path, raw: Path, closed_trades: int, plan: dict[str, Any]) -> None:
    """Produce the standard metrics, trade ledger, statement, equity, and HTML report."""
    from algo_backtest.artifacts import RunManifest, write_run_artifacts
    from algo_backtest.metrics import metrics_from_results
    from algo_backtest.statement import build_statement, load_run_artifacts, write_statement_files

    document = read_json(raw)
    result_dir = run_dir / "results"
    run_manifest = RunManifest(
        strategy=run_dir.name,
        symbol=plan["symbol"],
        start=plan["test_start"],
        end=plan["test_end"],
        params={"cash": str(plan["cash"])},
        success=True,
        closed_trades=closed_trades,
        broker_adapter=plan["broker_adapter"],
    )
    write_run_artifacts(
        result_dir,
        run_manifest,
        document["totalPerformance"]["closedTrades"],
        metrics_from_results(document, source=raw),
    )
    write_statement_files(build_statement(load_run_artifacts(result_dir)), result_dir)


def main() -> int:
    """Require an explicit prepare or execute command; never launch on import or preparation."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--mode", choices=("baseline", "hybrid"), default="baseline")
    prepare_parser.add_argument("--workers", type=int, choices=(1, 2))
    prepare_parser.add_argument(
        "--plan",
        type=Path,
        default=DEFAULT_PLAN,
        help="registered plan document; defaults to the bundled pilot plan.yaml",
    )
    for option in ("input-root", "output-root", "spockfx-conf"):
        prepare_parser.add_argument(f"--{option}", type=Path, required=True)
    execute_parser = sub.add_parser("execute")
    execute_parser.add_argument("--output-root", type=Path, required=True)
    execute_parser.add_argument("--workers", type=int, choices=(1, 2))
    sub.add_parser("_backtest").add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        print(
            prepare(
                args.input_root,
                args.output_root,
                args.spockfx_conf,
                mode=args.mode,
                workers=args.workers,
                plan_path=args.plan,
            )
        )
        return 0
    if args.action == "execute":
        return execute(args.output_root, workers=args.workers)
    return backtest(args.run_dir)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(f"Experiment failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
