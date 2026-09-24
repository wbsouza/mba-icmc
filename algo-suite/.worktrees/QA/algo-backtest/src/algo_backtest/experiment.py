"""Backtest experiment: the reproducible Chapter-4 experiment contract (Stage F1).

An *experiment* is a named set of *runs*, each pinning a strategy, symbol, window and
parameters. `run_experiment` executes every run on the proven run path, writing one
deterministic directory per run plus a flat, row-oriented `experiment.json` manifest
(one metrics row per run) — the seed for the Chapter-4 comparison table (Stage F2).

Locked contract (F1):
  * Schema is closed: each run needs id/strategy/symbol/from/to; params live in an explicit
    nested block, strategy-specific (baseline-ma: fast/slow/size; baseline-meanrev:
    window/band/size) and pinned explicitly — no hidden defaults. Unknown top-level keys are
    rejected; the per-strategy validator (run.STRATEGIES) enforces the param key set.
  * Output is deterministic: runs/experiments/<experiment>/<run_id>/, with the
    experiment-level manifest/error artifact at the experiment root. Re-running **replaces
    the whole experiment tree** up front, so the tree always reflects exactly the current
    spec — a shrunk spec leaves no stale run dirs. Replace-only (no resume); not
    concurrency-safe (one experiment process at a time).
  * Failure is fail-fast: the first failed run aborts the experiment and writes an
    `experiment-error.json` (failed + completed run ids) at the experiment root instead of
    a manifest, so a broken run is still traceable. Exactly one of experiment.json /
    experiment-error.json ever exists.

Not a strategy/optimization framework — no CPCV, parameter sweeps, or parallelism.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Protocol

import structlog
import yaml
from algo_core.atomicio import write_text_atomic
from algo_core.instrument import Instrument, build_instrument

from algo_backtest.artifacts import RunManifest, write_run_artifacts
from algo_backtest.metrics import Metrics, metrics_from_results
from algo_backtest.results import RunResult
from algo_backtest.run import lean_data_covers, run_strategy, validate_run_inputs

EXPERIMENT_KEYS = frozenset({"experiment", "runs"})
RUN_KEYS = frozenset({"id", "strategy", "symbol", "from", "to", "params"})


@dataclass(frozen=True)
class Run:
    """One pinned, reproducible backtest within an experiment.

    `params` are strategy-specific (e.g. baseline-ma: fast/slow/size; baseline-meanrev:
    window/band/size) and validated by the strategy at run time — the spec must pin them
    explicitly (no hidden defaults).
    """

    run_id: str
    strategy: str
    symbol: str
    start: date
    end: date
    params: dict[str, str]


@dataclass(frozen=True)
class Experiment:
    """A named set of runs — the experiment contract loaded from a spec."""

    name: str
    runs: tuple[Run, ...]


@dataclass(frozen=True)
class RunOutcome:
    """The result of executing one run: its metrics + where they live."""

    run: Run
    success: bool
    closed_trades: int
    metrics: Metrics
    run_dir: Path


@dataclass(frozen=True)
class ExperimentResult:
    """A finished experiment: the manifest path + every run's outcome."""

    manifest_path: Path
    outcomes: tuple[RunOutcome, ...]


class StrategyRunner(Protocol):
    """The run-path callable `run_experiment` depends on (default: `run_strategy`).

    Declared as a Protocol so the experiment orchestration can be unit-tested with a fake
    runner — the injection seam is at this boundary only, not deeper in the stack.
    """

    def __call__(
        self,
        strategy: str,
        *,
        data_root: Path,
        instrument: Instrument,
        start: date,
        end: date,
        params: Mapping[str, str],
        results_dir: Path,
        timeout: int,
    ) -> RunResult: ...


def load_experiment(spec_path: Path) -> Experiment:
    """Load + structurally validate an experiment spec (fail fast on a malformed contract).

    Raises:
        ValueError: not a mapping, unknown top-level keys, no runs, a malformed run, or
            duplicate run ids.
    """
    raw = yaml.safe_load(spec_path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(
            f"{spec_path} is not an experiment mapping (needs 'experiment' + 'runs')"
        )
    unknown = set(raw) - EXPERIMENT_KEYS
    if unknown:
        raise ValueError(
            f"{spec_path}: unknown top-level key(s) {sorted(unknown)}; "
            f"allowed: {sorted(EXPERIMENT_KEYS)}"
        )
    if "experiment" not in raw:
        raise ValueError(f"{spec_path}: missing the required 'experiment' name")
    rows = raw.get("runs")
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{spec_path}: the experiment has no runs")
    runs = tuple(_run_from_spec(row, spec_path) for row in rows)
    ids = [r.run_id for r in runs]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(
            f"{spec_path}: duplicate run id(s) {duplicates}; ids must be unique"
        )
    return Experiment(name=str(raw["experiment"]), runs=runs)


def _run_from_spec(row: Any, spec_path: Path) -> Run:
    """Build one Run from a spec row, rejecting unknown/missing fields."""
    if not isinstance(row, dict):
        raise ValueError(f"{spec_path}: each run must be a mapping, got {row!r}")
    unknown = set(row) - RUN_KEYS
    if unknown:
        raise ValueError(
            f"{spec_path}: run {row.get('id', '?')!r} has unknown field(s) {sorted(unknown)}"
        )
    params = _params_from_spec(row.get("params", {}), spec_path, str(row.get("id", "?")))
    try:
        return Run(
            run_id=str(row["id"]),
            strategy=str(row["strategy"]),
            symbol=str(row["symbol"]),
            start=date.fromisoformat(str(row["from"])),
            end=date.fromisoformat(str(row["to"])),
            params=params,
        )
    except (KeyError, ValueError) as exc:
        raise ValueError(
            f"{spec_path}: run {row.get('id', '?')!r} is invalid ({exc}); "
            "needs id, strategy, symbol, from, to"
        ) from exc


def _params_from_spec(raw: Any, spec_path: Path, run_id: str) -> dict[str, str]:
    """Read the strategy-specific params block as a string map (the strategy validates it).

    Kept generic — which keys are valid depends on the strategy, so the per-strategy
    validator (run.STRATEGIES) enforces the closed key set and value ranges at run time.
    """
    if not isinstance(raw, dict):
        raise ValueError(f"{spec_path}: run {run_id!r} params must be a mapping")
    return {str(key): str(value) for key, value in raw.items()}


def run_experiment(
    experiment: Experiment,
    *,
    data_root: Path,
    timeout: int,
    runner: StrategyRunner = run_strategy,
) -> ExperimentResult:
    """Run every run in order; write the manifest, or abort + error on first failure.

    The whole experiment tree is **replaced** up front (`runs/experiments/<experiment>/`),
    so a re-run with a shrunk spec leaves no stale run directories behind — the tree always
    reflects exactly this spec. On the first failed run, writes `experiment-error.json` and
    re-raises — no manifest. Replace-only: there is no resume, so a failure late in a long
    experiment re-runs the earlier runs (acceptable at thesis scale; a sweep with resume is
    later work). Not concurrency-safe — one experiment process at a time (the up-front
    rmtree would race a concurrent run).

    Raises:
        ValueError: a run is invalid or its window has no materialized data.
        RuntimeError: the engine run for a run failed.
    """
    log = structlog.get_logger("backtest")
    _reset_experiment_tree(data_root, experiment.name)
    total = len(experiment.runs)
    outcomes: list[RunOutcome] = []
    for index, run in enumerate(experiment.runs, start=1):
        log.info(
            "run_start", experiment=experiment.name, run=run.run_id, index=index, total=total
        )
        try:
            outcomes.append(_execute_run(run, experiment.name, data_root, timeout, runner))
        except (ValueError, RuntimeError) as exc:
            _write_experiment_error(experiment, run, outcomes, data_root, exc)
            raise
    manifest_path = _write_experiment_manifest(experiment, outcomes, data_root)
    return ExperimentResult(manifest_path=manifest_path, outcomes=tuple(outcomes))


def _execute_run(
    run: Run,
    experiment_name: str,
    data_root: Path,
    timeout: int,
    runner: StrategyRunner,
) -> RunOutcome:
    """Validate, execute, and persist one run's artifacts; return its outcome."""
    instrument = build_instrument(run.symbol)
    validate_run_inputs(run.strategy, run.params, run.start, run.end)
    if not lean_data_covers(data_root, instrument, run.start, run.end):
        raise ValueError(
            f"run {run.run_id!r}: no lean-data for {run.symbol} covering "
            f"{run.start}..{run.end}; run "
            f"`algo-backtest materialize --symbol {run.symbol} ...` for that window first"
        )
    results_dir = _run_dir(data_root, experiment_name, run.run_id)
    result = runner(
        run.strategy, data_root=data_root, instrument=instrument,
        start=run.start, end=run.end, params=run.params,
        results_dir=results_dir, timeout=timeout,
    )
    if not result.success:
        raise RuntimeError(f"run {run.run_id!r}: the engine run failed; see {results_dir}")
    results_doc = json.loads(result.raw_results_path.read_text())
    metrics = metrics_from_results(results_doc, source=result.raw_results_path)
    manifest = RunManifest(
        strategy=run.strategy, symbol=run.symbol,
        start=run.start.isoformat(), end=run.end.isoformat(),
        params=dict(run.params),
        success=result.success, closed_trades=result.closed_trades,
    )
    closed_trades = results_doc["totalPerformance"]["closedTrades"]
    write_run_artifacts(results_dir, manifest, closed_trades, metrics)
    return RunOutcome(
        run=run, success=result.success,
        closed_trades=result.closed_trades, metrics=metrics, run_dir=results_dir,
    )


def _reset_experiment_tree(data_root: Path, experiment_name: str) -> None:
    """Replace the experiment tree so it reflects exactly this spec (no stale runs)."""
    directory = data_root / "runs" / "experiments" / experiment_name
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)


def _run_dir(data_root: Path, experiment_name: str, run_id: str) -> Path:
    """The deterministic per-run dir under the (freshly reset) experiment tree."""
    directory = data_root / "runs" / "experiments" / experiment_name / run_id
    directory.mkdir(parents=True)
    return directory


def _run_row(experiment_name: str, outcome: RunOutcome, data_root: Path) -> dict[str, Any]:
    """One flat manifest row (the F2-consumable schema) for a run outcome."""
    run, metrics = outcome.run, outcome.metrics
    return {
        "experiment": experiment_name,
        "run_id": run.run_id,
        "strategy": run.strategy,
        "symbol": run.symbol,
        "from": run.start.isoformat(),
        "to": run.end.isoformat(),
        "success": outcome.success,
        "closed_trades": outcome.closed_trades,
        "total_return": metrics.total_return,
        "sharpe": metrics.sharpe,
        "max_drawdown": metrics.max_drawdown,
        "hit_rate": metrics.hit_rate,
        "run_dir": outcome.run_dir.relative_to(data_root).as_posix(),
    }


def _experiment_dir(data_root: Path, experiment_name: str) -> Path:
    """The experiment-level dir holding the manifest/error artifact + run subdirs."""
    directory = data_root / "runs" / "experiments" / experiment_name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _write_experiment_manifest(
    experiment: Experiment, outcomes: list[RunOutcome], data_root: Path
) -> Path:
    """Write the row-oriented experiment manifest (the tree was reset up front, so only one
    of experiment.json / experiment-error.json is ever written per run)."""
    directory = _experiment_dir(data_root, experiment.name)
    manifest = {
        "experiment": experiment.name,
        "generated_at": datetime.now(UTC).isoformat(),
        "runs": [_run_row(experiment.name, o, data_root) for o in outcomes],
    }
    path = directory / "experiment.json"
    write_text_atomic(path, json.dumps(manifest, indent=2))
    return path


def _write_experiment_error(
    experiment: Experiment,
    failed: Run,
    completed: list[RunOutcome],
    data_root: Path,
    error: Exception,
) -> None:
    """Record an experiment-level failure artifact (failed + completed run ids) for traceability."""
    directory = _experiment_dir(data_root, experiment.name)
    payload = {
        "experiment": experiment.name,
        "generated_at": datetime.now(UTC).isoformat(),
        "failed_run": failed.run_id,
        "completed_runs": [o.run.run_id for o in completed],
        "error": str(error),
    }
    write_text_atomic(directory / "experiment-error.json", json.dumps(payload, indent=2))
