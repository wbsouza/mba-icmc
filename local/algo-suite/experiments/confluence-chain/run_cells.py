"""Bounded fourteen-cell launch harness (story 21, T17).

An explicit-run-ID launch harness for the registered fourteen-cell confluence-chain
protocol (`README.md`; spec CC-23, CC-24, CC-32). It enforces three gates before any
cell backtest starts: **registration** (only the fourteen IDs `make_cells.py` (T10)
generates are ever accepted — an unregistered ID is refused before anything is
written), **data** (the price-population partition gate below, reusing
`preflight.py` (T9)) and **integration** (the disclosed GDELT-availability gap:
`preflight.compute_arm_ledger` with no sidecar marks every news-dependent arm
``"unavailable"`` — never silently launched, never a fabricated estimate).

One invocation, one caller-supplied ``--job-dir`` (the explicit run ID). Each
invocation regenerates the full fourteen-cell registration under that directory
(T10's generator is deterministic — regenerating is a no-op on unchanged inputs, never
a second family) and launches only the cells the caller selected via ``--cells``
(default: all fourteen) that are both data-ready and not already attempted. A cell
already attempted (any terminal ``status.json``: ``succeeded``, ``failed`` or
``unavailable``) is never relaunched on resume; the *only* sanctioned way to attempt
a specific cell again is to name it in ``--rerun``, a separately authorized action,
never an automatic retry loop (the registered "one initial attempt" policy in
``README.md``).

Each cell gets its own output root, ``<job_dir>/<cell_id>/`` — the same directory
`make_cells.py` already writes that cell's ``config.yaml`` into — holding
``command.json`` (the exact argv, the config hash and the source revision recorded
*before* launch), ``run.log`` (the child's captured stdout+stderr) and ``status.json``
(the terminal record). No cell's directory is shared with another cell's.

The child backtest is invoked through the current CLI contract,
``algo-backtest run --strategy <cell_id> --symbol <pair> --from <start> --to <end>
--strategies-dir <job_dir> --timeout <seconds>`` (`cli.py`'s ``run`` command) — never
an old latest-run-directory glob, and never with ``--model``: no cell in this study
depends on an F7 model (README, "No model dependency"), so the harness never fits or
loads one. The child process is reached through an injectable ``runner`` callable
(default: a real, timed ``subprocess.run``); this file's own tests substitute a fake
runner and never invoke a real LEAN run (see `confluence_run_contract.feature`).

The price-population gate implemented here (`population_gate`) checks only that each
required month's source Parquet partition exists (`preflight.partition_path`) —
a real, cheap, file-existence check, not a fake one. It does **not** perform T9's
fuller row-level reconciliation (`preflight.compute_population_ledger`'s
``warmup_bars``/``missing_bars`` — those require reading each month's actual bar
timestamps), which needs real data access this harness does not perform on its own;
that deeper reconciliation is a caller responsibility before any separately
authorized T19 run, not silently assumed here. A missing partition is still a hard
failure (CC-24) that aborts the whole invocation before any cell launches.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from calendar import monthrange
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from algo_backtest.run import lean_data_covers
from algo_core.atomicio import write_text_atomic
from algo_core.instrument import build_instrument

HERE = Path(__file__).resolve().parent
SUITE = HERE.parents[1]

DEFAULT_TIMEOUT_SECONDS = 1800  # coordinator-communicated cap, README "Resource cap"
DEFAULT_MAX_CONCURRENT = 3  # coordinator-communicated cap, README "Resource cap"

# preflight.py's arm registries omit "A-plan" (README, "Known constraints", finding 3):
# calling compute_arm_ledger("A-plan", ...) raises ValueError("unknown arm"). A-plan
# shares A's required voters and news dependency, so its arm-ledger gate here reuses A's
# result under its own cell id — a disclosed, documented substitution, not a silent one.
_ARM_LEDGER_ALIAS: dict[str, str] = {"A-plan": "A"}

STATE_UNAVAILABLE = "unavailable"
STATE_RUNNING = "running"
STATE_SUCCEEDED = "succeeded"
STATE_FAILED = "failed"


def _load_script(path: Path) -> ModuleType:
    """Load a standalone sibling script file as an importable module, by file path.

    Same pattern the T9/T10 Gherkin steps already use for these scripts: none of
    `make_cells.py`, `preflight.py` or this file sit inside an installed package, so a
    plain ``import`` would depend on the caller's ``sys.path`` (fragile whether this
    file is run directly, imported, or loaded dynamically by a test); loading by exact
    file path is correct regardless of how *this* file itself was loaded.
    """
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"run_cells: cannot load sibling script {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mc = _load_script(HERE / "make_cells.py")
pf = _load_script(HERE / "preflight.py")

ALLOWED_CELL_IDS: frozenset[str] = frozenset(
    f"{arm.lower()}-{'h1' if clock == 60 else 'h4'}"
    for arm in mc.ARMS
    for clock in mc.CLOCK_LOOKBACK
)


def _generate_manifest(job_dir: Path) -> list[LaunchCell]:
    """Call T10's generator and translate its rows into this file's own typed cells."""
    cells = mc.generate_manifest(job_dir)
    generated = {
        str(cell.cell_id): LaunchCell(
            cell_id=str(cell.cell_id),
            arm=str(cell.arm),
            clock_minutes=int(cell.clock_minutes),
            config_hash=str(cell.config_hash),
            pair=str(cell.config["pair"]),
            window_start=str(cell.config["window"]["start"]),
            window_end=str(cell.config["window"]["end"]),
        )
        for cell in cells
    }
    unexpected = set(generated) - ALLOWED_CELL_IDS
    if unexpected:
        raise ValueError(
            f"run_cells: make_cells.py generated unregistered cell id(s) {sorted(unexpected)} "
            f"— expected exactly {sorted(ALLOWED_CELL_IDS)}"
        )
    missing = ALLOWED_CELL_IDS - set(generated)
    if missing:
        raise ValueError(
            f"run_cells: make_cells.py did not generate registered cell id(s) {sorted(missing)}"
        )
    return [generated[cell_id] for cell_id in sorted(generated)]


def _arm_ledger_status(cell: LaunchCell) -> tuple[str, str | None]:
    """OK or unavailable for one cell (CC-13, CC-32, D9), never a fabricated estimate."""
    arm = _ARM_LEDGER_ALIAS.get(cell.arm, cell.arm)
    window_start, window_end = _date_window(cell.window_start, cell.window_end)
    ledger = pf.compute_arm_ledger(
        arm, clock_minutes=cell.clock_minutes, window_start=window_start, window_end=window_end
    )
    return str(ledger.status), (None if ledger.reason is None else str(ledger.reason))


def _date_window(start: str, end: str) -> tuple[datetime, datetime]:
    window_start, window_end = pf.date_window(start, end)
    return window_start, window_end


def _check_population_month(
    *, pair: str, clock_minutes: int, month_start: str, month_end: str, partition_exists: bool
) -> None:
    """One T9 population-ledger call for one (pair, clock, month); raises on a hard failure."""
    window_start, window_end = _date_window(month_start, month_end)
    pf.compute_population_ledger(
        pair=pair,
        clock_minutes=clock_minutes,
        window_start=window_start,
        window_end=window_end,
        partition_exists=partition_exists,
    )


@dataclass(frozen=True)
class LaunchCell:
    """One registered cell's identity, as this harness needs it (T10's row, retyped)."""

    cell_id: str
    arm: str
    clock_minutes: int
    config_hash: str
    pair: str
    window_start: str
    window_end: str


@dataclass(frozen=True)
class ChildResult:
    """One child backtest attempt's outcome."""

    exit_code: int
    output: str


Runner = Callable[[Sequence[str], Path, int], ChildResult]
PopulationGate = Callable[[Sequence[LaunchCell], Path], None]


def _real_runner(command: Sequence[str], cwd: Path, timeout: int) -> ChildResult:
    """Launch the actual `algo-backtest run` child, bounded by `timeout` (README, D-neutral).

    Never raises: a spawn failure or a timeout is itself a recorded outcome, matching
    the existing `heikin-ashi-signals/runner.py` convention (exit 127 / 124 respectively).
    """
    try:
        result = subprocess.run(
            list(command), cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return ChildResult(result.returncode, result.stdout + result.stderr)
    except subprocess.TimeoutExpired as exc:
        return ChildResult(124, f"run_cells: child exceeded {timeout}s: {exc}")
    except OSError as exc:
        return ChildResult(127, f"run_cells: cannot start child: {exc}")


def months_between(start: date, end: date) -> list[tuple[str, str, str]]:
    """(month label, first day, last day) for every calendar month touching [start, end]."""
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        last_day = monthrange(year, month)[1]
        label = f"{year:04d}-{month:02d}"
        months.append((label, f"{label}-01", f"{label}-{last_day:02d}"))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


def population_gate(cells: Sequence[LaunchCell], data_root: Path) -> None:
    """The real materialized-data-coverage price-population gate (CC-24); see module docstring.

    Raises:
        ValueError: any required month has no materialized lean-data for any requested
            clock, or the requested cells disagree on pair/window (a registration bug).
    """
    if not cells:
        return
    pairs = {cell.pair for cell in cells}
    windows = {(cell.window_start, cell.window_end) for cell in cells}
    if len(pairs) != 1 or len(windows) != 1:
        raise ValueError(
            f"run_cells: requested cells disagree on pair/window (pairs={sorted(pairs)}, "
            f"windows={sorted(windows)}) — this is a registration bug, not a data gap"
        )
    (pair,) = pairs
    ((study_start, study_end),) = windows
    instrument = build_instrument(pair)
    for clock_minutes in sorted({cell.clock_minutes for cell in cells}):
        # Reuse the same real coverage check `algo-backtest run` itself gates on
        # (algo_backtest.run.lean_data_covers) — H1 and H4 both aggregate from the same
        # materialized minute quotes, so this is clock-independent (the month label
        # below is used only for `_check_population_month`'s own window bounds).
        for _label, month_start, month_end in months_between(
            date.fromisoformat(study_start), date.fromisoformat(study_end)
        ):
            partition_exists = lean_data_covers(
                data_root,
                instrument,
                date.fromisoformat(month_start),
                date.fromisoformat(month_end),
            )
            _check_population_month(
                pair=pair,
                clock_minutes=clock_minutes,
                month_start=month_start,
                month_end=month_end,
                partition_exists=partition_exists,
            )


def _write_json(path: Path, value: object) -> None:
    write_text_atomic(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def _read_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text())
    if not isinstance(document, dict):
        raise ValueError(f"run_cells: expected an object in {path}")
    return document


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _source_hashes() -> dict[str, str]:
    """Fingerprint this harness's own code and its two direct T9/T10 dependencies."""
    return {
        str(path): _digest(path)
        for path in (HERE / "run_cells.py", HERE / "make_cells.py", HERE / "preflight.py")
    }


def _git_sha(cwd: Path) -> str | None:
    """The source revision this attempt ran against, or None outside a git checkout."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _backtest_command(cell: LaunchCell, job_dir: Path, timeout: int) -> list[str]:
    """The exact `algo-backtest run` argv for one cell (cli.py's `run` command); no
    `--model` (see module docstring, "No model dependency")."""
    return [
        "uv",
        "run",
        "algo-backtest",
        "run",
        "--strategy",
        cell.cell_id,
        "--symbol",
        cell.pair,
        "--from",
        cell.window_start,
        "--to",
        cell.window_end,
        "--strategies-dir",
        str(job_dir),
        "--timeout",
        str(timeout),
    ]


def _extract_results_dir(output: str) -> str | None:
    """The run's own results directory, if the child reported one (`cli.py`'s `results=`)."""
    for line in output.splitlines():
        marker = "results="
        index = line.find(marker)
        if index != -1:
            return line[index + len(marker) :].split()[0]
    return None


def _cell_dir(job_dir: Path, cell_id: str) -> Path:
    return job_dir / cell_id


def _status_path(job_dir: Path, cell_id: str) -> Path:
    return _cell_dir(job_dir, cell_id) / "status.json"


def _launch_one(
    cell: LaunchCell, job_dir: Path, *, timeout: int, runner: Runner, git_sha: str | None
) -> dict[str, Any]:
    """Run exactly one attempt for `cell` and persist its terminal status.json.

    Never raises: any unexpected exception from `runner` itself is caught and recorded
    as a failure, so one cell's crash never aborts the others (mirrors
    `heikin-ashi-signals/runner.py`'s `execute_cell`).
    """
    cell_dir = _cell_dir(job_dir, cell.cell_id)
    command = _backtest_command(cell, job_dir, timeout)
    started_at = datetime.now(UTC).isoformat()
    _write_json(
        cell_dir / "command.json",
        {
            "cell_id": cell.cell_id,
            "command": command,
            "config_hash": cell.config_hash,
            "source_revision": git_sha,
            "code_hashes": _source_hashes(),
            "started_at": started_at,
        },
    )
    _write_json(
        cell_dir / "status.json",
        {
            "cell_id": cell.cell_id,
            "arm": cell.arm,
            "clock_minutes": cell.clock_minutes,
            "config_hash": cell.config_hash,
            "state": STATE_RUNNING,
            "exit_code": None,
            "reason": None,
            "started_at": started_at,
            "finished_at": None,
        },
    )
    try:
        result = runner(command, SUITE, timeout)
        exit_code, output = result.exit_code, result.output
    except Exception as exc:  # a runner that raises instead of returning is still recorded
        exit_code, output = 1, f"run_cells: runner raised {exc!r}"
    write_text_atomic(cell_dir / "run.log", output)
    status = {
        "cell_id": cell.cell_id,
        "arm": cell.arm,
        "clock_minutes": cell.clock_minutes,
        "config_hash": cell.config_hash,
        "state": STATE_SUCCEEDED if exit_code == 0 else STATE_FAILED,
        "exit_code": exit_code,
        "reason": None if exit_code == 0 else f"child exited {exit_code}",
        "source_revision": git_sha,
        "results_dir": _extract_results_dir(output),
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    _write_json(cell_dir / "status.json", status)
    return status


def _unavailable_status(cell: LaunchCell, reason: str) -> dict[str, Any]:
    return {
        "cell_id": cell.cell_id,
        "arm": cell.arm,
        "clock_minutes": cell.clock_minutes,
        "config_hash": cell.config_hash,
        "state": STATE_UNAVAILABLE,
        "exit_code": None,
        "reason": reason,
        "source_revision": None,
        "results_dir": None,
        "started_at": None,
        "finished_at": None,
    }


def _validate_selection(
    cell_ids: Sequence[str] | None, rerun: Sequence[str]
) -> tuple[set[str], set[str]]:
    """The requested and rerun id sets, or raise naming any unregistered/mismatched id."""
    requested = set(cell_ids) if cell_ids is not None else set(ALLOWED_CELL_IDS)
    unregistered = requested - ALLOWED_CELL_IDS
    if unregistered:
        raise ValueError(
            f"run_cells: unregistered cell id(s) {sorted(unregistered)} — the fourteen "
            f"registered ids are {sorted(ALLOWED_CELL_IDS)}"
        )
    rerun_set = set(rerun)
    unregistered_rerun = rerun_set - requested
    if unregistered_rerun:
        raise ValueError(
            f"run_cells: --rerun id(s) {sorted(unregistered_rerun)} are not among the "
            f"requested cells {sorted(requested)}"
        )
    return requested, rerun_set


def _gate_arm_ledger(
    to_check: Sequence[LaunchCell], job_dir: Path
) -> tuple[list[LaunchCell], dict[str, dict[str, Any]]]:
    """Split `to_check` into launchable cells and recorded-unavailable statuses (D9)."""
    to_launch: list[LaunchCell] = []
    statuses: dict[str, dict[str, Any]] = {}
    for cell in to_check:
        status_arm, reason = _arm_ledger_status(cell)
        if status_arm == pf.OK:
            to_launch.append(cell)
        else:
            status = _unavailable_status(cell, reason or "unavailable")
            _write_json(_status_path(job_dir, cell.cell_id), status)
            statuses[cell.cell_id] = status
    return to_launch, statuses


def launch_job(
    job_dir: Path,
    *,
    cell_ids: Sequence[str] | None = None,
    rerun: Sequence[str] = (),
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    data_root: Path | None = None,
    runner: Runner = _real_runner,
    population_gate_fn: PopulationGate = population_gate,
) -> list[dict[str, Any]]:
    """Enforce registration, data and integration gates, then launch the selected cells.

    Always regenerates the full fourteen-cell registration under `job_dir` (T10 is
    deterministic — a no-op on unchanged inputs) before filtering to the requested
    subset, so `job_dir` always carries the complete registration regardless of which
    cells this particular invocation launches.

    Raises:
        ValueError: an unrecognized `cell_ids`/`rerun` entry, or `population_gate_fn`
            raises (a hard data failure) — in either case, zero cells are launched.
    """
    if max_concurrent < 1:
        raise ValueError(f"run_cells: --max-concurrent must be >= 1, got {max_concurrent}")
    job_dir.mkdir(parents=True, exist_ok=True)
    readme = HERE / "README.md"
    if readme.is_file():
        write_text_atomic(job_dir / "README.md", readme.read_text())
    all_cells = {cell.cell_id: cell for cell in _generate_manifest(job_dir)}
    requested, rerun_set = _validate_selection(cell_ids, rerun)

    selected = [all_cells[cell_id] for cell_id in sorted(requested)]
    to_check = [
        cell
        for cell in selected
        if cell.cell_id in rerun_set or not _status_path(job_dir, cell.cell_id).is_file()
    ]
    resolved_data_root = data_root if data_root is not None else _default_data_root()
    population_gate_fn(to_check, resolved_data_root)  # a hard failure here launches zero cells

    git_sha = _git_sha(SUITE)
    to_launch, statuses = _gate_arm_ledger(to_check, job_dir)

    if to_launch:
        with ThreadPoolExecutor(max_workers=min(max_concurrent, len(to_launch))) as pool:
            futures = {
                cell.cell_id: pool.submit(
                    _launch_one, cell, job_dir, timeout=timeout, runner=runner, git_sha=git_sha
                )
                for cell in to_launch
            }
            for cell_id, future in futures.items():
                statuses[cell_id] = future.result()

    for cell in selected:
        if cell.cell_id not in statuses:
            statuses[cell.cell_id] = _read_json(_status_path(job_dir, cell.cell_id))
    return [statuses[cell_id] for cell_id in sorted(requested)]


def _default_data_root() -> Path:
    from algo_backtest.config import load_backtest_config

    return load_backtest_config().data_root


def main(argv: Sequence[str] | None = None) -> int:
    """Console entry point: `--job-dir` is the only required argument."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", type=Path, required=True)
    parser.add_argument("--cells", nargs="+", default=None, help="default: all fourteen")
    parser.add_argument(
        "--rerun", nargs="+", default=(), help="explicit, separately authorized re-run"
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-concurrent", type=int, default=DEFAULT_MAX_CONCURRENT)
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        statuses = launch_job(
            args.job_dir,
            cell_ids=args.cells,
            rerun=args.rerun,
            timeout=args.timeout,
            max_concurrent=args.max_concurrent,
            data_root=args.data_root,
        )
    except ValueError as exc:
        print(f"run_cells: {exc}", file=sys.stderr)
        return 2
    failed = [s for s in statuses if s["state"] == STATE_FAILED]
    for status in statuses:
        print(f"{status['cell_id']}: {status['state']} (exit_code={status['exit_code']})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
