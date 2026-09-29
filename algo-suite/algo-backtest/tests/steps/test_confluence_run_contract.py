"""Steps for confluence_run_contract.feature — the bounded launch harness (story 21, T17).

`experiments/confluence-chain/run_cells.py` is a standalone script outside the
`algo_backtest` package, loaded here by file path (same pattern as T8/T9/T10's steps).
Every scenario injects a fake runner (never a real LEAN run) and a permissive no-op
population-preflight stub by default, so no scenario touches real data or a real child
process; only the "population preflight that always fails" rule overrides the stub.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
import yaml
from algo_core import layout
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_run_contract.feature")

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "experiments" / "confluence-chain" / "run_cells.py"
)

# Independently written (not derived from run_cells.ALLOWED_CELL_IDS) so this scenario
# would fail if the harness's registered set ever drifted from README.md's table.
_EXPECTED_FOURTEEN = frozenset(
    {
        "a-h1",
        "a-h4",
        "b-h1",
        "b-h4",
        "a-plan-h1",
        "a-plan-h4",
        "t-only-h1",
        "t-only-h4",
        "m-only-h1",
        "m-only-h4",
        "always-short-h1",
        "always-short-h4",
        "always-long-h1",
        "always-long-h4",
    }
)


def _load_script(path: Path) -> ModuleType:
    """Load a standalone script file as an importable module, by file path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rc = _load_script(_SCRIPT_PATH)


def _permissive_gate(cells: Sequence[Any], data_root: Path) -> None:
    """The default preflight stub for every scenario: always passes."""


@dataclass
class _RunContractCtx:
    """Per-scenario context: the job directory, the last launch's outcome, and its calls."""

    job_dir: Path
    data_root: Path
    population_gate_fn: Any = _permissive_gate
    calls: list[list[str]] = field(default_factory=list)
    statuses: list[dict[str, Any]] = field(default_factory=list)
    error: Exception | None = None
    calls_full: list[tuple[list[str], Path, int]] = field(default_factory=list)
    snapshot: tuple[str, bool] | None = None
    peak: int = 0
    gate_seen: list[tuple[list[str], Path]] = field(default_factory=list)
    cli_code: int = -1
    data_root_dir_made: bool = False


@pytest.fixture
def run_contract_ctx(tmp_path: Path) -> _RunContractCtx:
    """A fresh per-scenario context with its own job and data directories."""
    return _RunContractCtx(job_dir=tmp_path / "job", data_root=tmp_path / "data")


def _launch(
    ctx: _RunContractCtx,
    cell_ids: Sequence[str] | None,
    *,
    exit_code: int | None = None,
    rerun: Sequence[str] = (),
    output: str = "boom\n",
    runner: Callable[[Sequence[str], Path, int], Any] | None = None,
    use_default_data_root: bool = False,
    **launch_kwargs: Any,
) -> None:
    """Launch `cell_ids` through a fake runner (or `runner`), recording calls onto `ctx`."""
    calls: list[list[str]] = []

    def fake_runner(command: Sequence[str], cwd: Path, timeout: int) -> Any:
        calls.append(list(command))
        ctx.calls_full.append((list(command), cwd, timeout))
        return rc.ChildResult(0 if exit_code is None else exit_code, output)

    if not use_default_data_root:
        launch_kwargs["data_root"] = ctx.data_root
    try:
        ctx.statuses = rc.launch_job(
            ctx.job_dir,
            cell_ids=None if cell_ids is None else list(cell_ids),
            rerun=list(rerun),
            runner=runner or fake_runner,
            population_gate_fn=ctx.population_gate_fn,
            **launch_kwargs,
        )
        ctx.error = None
    except ValueError as exc:
        ctx.error, ctx.statuses = exc, []
    ctx.calls = calls


def _status(ctx: _RunContractCtx, cell_id: str) -> dict[str, Any]:
    return rc._read_json(ctx.job_dir / cell_id / "status.json")


# --- Given ---


@given("a fresh job directory")
def _fresh_job_dir(run_contract_ctx: _RunContractCtx) -> None:
    assert not run_contract_ctx.job_dir.exists()


@given("a population preflight that always fails")
def _failing_preflight(run_contract_ctx: _RunContractCtx) -> None:
    def always_fails(cells: Sequence[Any], data_root: Path) -> None:
        raise ValueError("preflight: forced failure for this scenario")

    run_contract_ctx.population_gate_fn = always_fails


@given(
    parsers.parse(
        'the harness has already launched cell id "{cell_id}" with a fake runner '
        "that always succeeds"
    )
)
def _already_launched_success(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    _launch(run_contract_ctx, [cell_id])
    assert run_contract_ctx.error is None, run_contract_ctx.error


@given(
    parsers.parse(
        'the harness has already launched cell id "{cell_id}" with a fake runner '
        "that always exits 1"
    )
)
def _already_launched_failure(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    _launch(run_contract_ctx, [cell_id], exit_code=1)
    assert run_contract_ctx.error is None, run_contract_ctx.error


# --- When ---


@when(
    parsers.parse(
        'the harness is launched for cell id "{cell_id}" with a fake runner that always succeeds'
    )
)
def _launch_one_success(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    _launch(run_contract_ctx, [cell_id])


@when(
    parsers.parse(
        'the harness is launched for cell id "{cell_id}" with a fake runner that always exits 1'
    )
)
def _launch_one_failure(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    _launch(run_contract_ctx, [cell_id], exit_code=1)


@when(
    parsers.parse(
        'the harness is launched for cells "{first}" and "{second}" with a fake runner '
        "that always succeeds"
    )
)
def _launch_two_success(run_contract_ctx: _RunContractCtx, first: str, second: str) -> None:
    _launch(run_contract_ctx, [first, second])


@when(
    parsers.parse(
        'the harness is launched again for cell id "{cell_id}" with a fake runner '
        "that always exits 1"
    )
)
def _launch_again_failure(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    _launch(run_contract_ctx, [cell_id], exit_code=1)


@when(
    parsers.parse('the harness reruns cell id "{cell_id}" with a fake runner that always succeeds')
)
def _rerun_success(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    _launch(run_contract_ctx, [cell_id], rerun=[cell_id])


# --- Then ---


@then("the harness's registered cell ids are exactly the fourteen from the README")
def _check_registered_ids() -> None:
    assert rc.ALLOWED_CELL_IDS == _EXPECTED_FOURTEEN
    assert len(rc.ALLOWED_CELL_IDS) == 14


@then(parsers.parse('the launch is refused naming the unregistered id "{cell_id}"'))
def _check_refused(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    assert run_contract_ctx.error is not None
    assert cell_id in str(run_contract_ctx.error)


@then("no attempt file exists for any cell")
def _check_no_attempts(run_contract_ctx: _RunContractCtx) -> None:
    assert list(run_contract_ctx.job_dir.glob("*/status.json")) == []


@then(
    parsers.parse(
        '"{first}" and "{second}" each have their own status.json under the job directory'
    )
)
def _check_distinct_status_files(
    run_contract_ctx: _RunContractCtx, first: str, second: str
) -> None:
    assert (run_contract_ctx.job_dir / first / "status.json").is_file()
    assert (run_contract_ctx.job_dir / second / "status.json").is_file()


@then(parsers.parse('"{first}"\'s status.json path differs from "{second}"\'s status.json path'))
def _check_status_paths_differ(run_contract_ctx: _RunContractCtx, first: str, second: str) -> None:
    first_path = run_contract_ctx.job_dir / first / "status.json"
    second_path = run_contract_ctx.job_dir / second / "status.json"
    assert first_path != second_path


@then(parsers.parse('the recorded command for "{cell_id}" does not contain "{flag}"'))
def _check_command_excludes(run_contract_ctx: _RunContractCtx, cell_id: str, flag: str) -> None:
    command_doc = rc._read_json(run_contract_ctx.job_dir / cell_id / "command.json")
    assert flag not in command_doc["command"]


@then("the launch raises a preflight error")
def _check_preflight_error(run_contract_ctx: _RunContractCtx) -> None:
    assert isinstance(run_contract_ctx.error, ValueError)


@then("the fake runner was never called")
def _check_never_called(run_contract_ctx: _RunContractCtx) -> None:
    assert run_contract_ctx.calls == []


@then(parsers.parse('the fake runner was never called for "{cell_id}"'))
def _check_never_called_for(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    assert not any(cell_id in call for call in run_contract_ctx.calls)


@then(parsers.parse('"{cell_id}"\'s status is "{state}"'))
@then(parsers.parse('"{cell_id}"\'s status is still "{state}"'))
def _check_status_state(run_contract_ctx: _RunContractCtx, cell_id: str, state: str) -> None:
    assert _status(run_contract_ctx, cell_id)["state"] == state


@then("the launch does not raise")
def _check_no_error(run_contract_ctx: _RunContractCtx) -> None:
    assert run_contract_ctx.error is None, run_contract_ctx.error


@then(parsers.parse('"{cell_id}"\'s recorded exit code is {code:d}'))
def _check_exit_code(run_contract_ctx: _RunContractCtx, cell_id: str, code: int) -> None:
    assert _status(run_contract_ctx, cell_id)["exit_code"] == code


@then(parsers.parse('"{cell_id}"\'s recorded config hash matches its generated manifest row'))
def _check_config_hash(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    manifest = json.loads((run_contract_ctx.job_dir / "manifest.json").read_text())
    row = next(r for r in manifest if r["cell_id"] == cell_id)
    assert _status(run_contract_ctx, cell_id)["config_hash"] == row["config_hash"]


@then(parsers.parse('"{cell_id}"\'s command record names a source revision or explicit None'))
def _check_source_revision(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    command_doc = rc._read_json(run_contract_ctx.job_dir / cell_id / "command.json")
    assert "source_revision" in command_doc


# ======================================================================================
# Phase 3 hardening steps (mutation pass over run_cells.py and the registration README)
# ======================================================================================

_SUITE_DIR = Path(__file__).resolve().parents[3]
_README = _SCRIPT_PATH.parent / "README.md"
_STUDY_MONTHS = [
    "2016-03",
    "2016-04",
    "2016-05",
    "2016-06",
    "2016-07",
    "2016-08",
    "2016-09",
    "2016-10",
    "2016-11",
    "2016-12",
    "2017-01",
    "2017-02",
]
_NEWS_FREE = ["m-only-h1", "m-only-h4", "always-long-h1", "always-long-h4"]


def _text(raw: str) -> str:
    """Decode the literal backslash-n a Gherkin cell may carry into a real newline."""
    return raw.replace("\\n", "\n")


def _all_fourteen(ctx: _RunContractCtx) -> None:
    """Launch every registered cell (no selection) through the always-succeeding runner."""
    _launch(ctx, None)
    assert ctx.error is None, ctx.error


def _readme_cell_rows() -> list[tuple[str, str, str]]:
    """(cell id, arm, clock label) from the README's numbered cell table."""
    pattern = re.compile(r"^\| \d+ \| `([a-z0-9-]+)` \| ([^|]+?) \| (H[14]) \|", re.MULTILINE)
    return pattern.findall(_README.read_text())


def _readme_launch_table() -> tuple[set[str], set[str]]:
    """(launch-ready ids, blocked ids) from the README's two-column availability table."""
    lines = [line.strip() for line in _README.read_text().splitlines()]
    header = next(i for i, line in enumerate(lines) if line.startswith("| Launch-ready today"))
    ready: set[str] = set()
    blocked: set[str] = set()
    for line in lines[header + 2 :]:
        if not line.startswith("|"):
            break
        columns = line.strip().strip("|").split("|")
        ready.update(re.findall(r"`([a-z0-9-]+)`", columns[0]))
        blocked.update(re.findall(r"`([a-z0-9-]+)`", columns[1]))
    return ready, blocked


# --- Given (hardening) ---


@given("a recording population preflight")
def _recording_preflight(run_contract_ctx: _RunContractCtx) -> None:
    def record(cells: Sequence[Any], data_root: Path) -> None:
        run_contract_ctx.gate_seen.append(([c.cell_id for c in cells], data_root))

    run_contract_ctx.population_gate_fn = record


@given("the real population preflight")
def _real_preflight(run_contract_ctx: _RunContractCtx) -> None:
    run_contract_ctx.population_gate_fn = rc.population_gate


@given(parsers.parse('the backtest config names data root "{root}"'))
def _config_data_root(monkeypatch: pytest.MonkeyPatch, root: str) -> None:
    import algo_backtest.config as backtest_config

    monkeypatch.setattr(
        backtest_config, "load_backtest_config", lambda: SimpleNamespace(data_root=Path(root))
    )


@given(parsers.parse('a generator that also emits a cell "{cell_id}"'))
def _generator_extra(monkeypatch: pytest.MonkeyPatch, cell_id: str) -> None:
    original = rc.mc.generate_manifest

    def with_extra(job_dir: Path) -> list[Any]:
        cells = original(job_dir)
        return [*cells, replace(cells[0], cell_id=cell_id)]

    monkeypatch.setattr(rc.mc, "generate_manifest", with_extra)


@given(parsers.parse('a generator that omits the cell "{cell_id}"'))
def _generator_omits(monkeypatch: pytest.MonkeyPatch, cell_id: str) -> None:
    original = rc.mc.generate_manifest

    def without(job_dir: Path) -> list[Any]:
        return [cell for cell in original(job_dir) if cell.cell_id != cell_id]

    monkeypatch.setattr(rc.mc, "generate_manifest", without)


@given(parsers.parse('the status file for "{cell_id}" holds a JSON list'))
def _status_is_list(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    (run_contract_ctx.job_dir / cell_id / "status.json").write_text("[]")


def _write_partitions(ctx: _RunContractCtx, skip_month: str) -> None:
    """Create every study month's M1 price partition, except `skip_month`, under the data root."""
    for month in _STUDY_MONTHS:
        if month == skip_month:
            continue
        year, month_number = month.split("-")
        path = layout.price_path(
            ctx.data_root, "forex", "EURUSD", "m1", int(year), int(month_number)
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")


@given(parsers.parse('a data root holding every M1 monthly partition except "{month}"'))
def _partitions_except(run_contract_ctx: _RunContractCtx, month: str) -> None:
    _write_partitions(run_contract_ctx, month)


# --- When (hardening) ---


@when(
    "the harness is launched for all fourteen registered cells with a fake runner "
    "that always succeeds"
)
def _launch_all(run_contract_ctx: _RunContractCtx) -> None:
    _launch(run_contract_ctx, None)


@when("the harness is launched for no cells with a fake runner that always succeeds")
def _launch_none(run_contract_ctx: _RunContractCtx) -> None:
    _launch(run_contract_ctx, [])


@when(parsers.parse('the harness is launched for cell id "{cell_id}" with rerun of "{rerun}"'))
def _launch_with_rerun(run_contract_ctx: _RunContractCtx, cell_id: str, rerun: str) -> None:
    _launch(run_contract_ctx, [cell_id], rerun=[rerun])


@when(
    parsers.parse(
        'the harness is launched for cell id "{cell_id}" with a concurrency cap of {cap:d}'
    )
)
def _launch_with_cap(run_contract_ctx: _RunContractCtx, cell_id: str, cap: int) -> None:
    _launch(run_contract_ctx, [cell_id], max_concurrent=cap)


@when(
    parsers.parse(
        'the harness is launched for cell id "{cell_id}" with a timeout of {secs:d} seconds'
    )
)
def _launch_with_timeout(run_contract_ctx: _RunContractCtx, cell_id: str, secs: int) -> None:
    _launch(run_contract_ctx, [cell_id], timeout=secs)


@when(parsers.parse('the harness is launched for cell id "{cell_id}" with the default data root'))
def _launch_default_root(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    _launch(run_contract_ctx, [cell_id], use_default_data_root=True)


@when(
    parsers.parse(
        'the harness is launched for cell id "{cell_id}" with a fake runner exiting {code:d}'
    )
)
def _launch_exiting(run_contract_ctx: _RunContractCtx, cell_id: str, code: int) -> None:
    _launch(run_contract_ctx, [cell_id], exit_code=code)


@when(
    parsers.parse(
        'the harness is launched for cell id "{cell_id}" with a fake runner printing "{output}"'
    )
)
def _launch_printing(run_contract_ctx: _RunContractCtx, cell_id: str, output: str) -> None:
    _launch(run_contract_ctx, [cell_id], output=_text(output))


@when(
    parsers.parse(
        'the harness is launched for cell id "{cell_id}" with a fake runner that raises "{message}"'
    )
)
def _launch_raising(run_contract_ctx: _RunContractCtx, cell_id: str, message: str) -> None:
    def raising(command: Sequence[str], cwd: Path, timeout: int) -> Any:
        raise RuntimeError(message)

    _launch(run_contract_ctx, [cell_id], runner=raising)


@when(
    parsers.parse(
        'the harness is launched for cell id "{cell_id}" with a fake runner that '
        "inspects its own record"
    )
)
def _launch_inspecting(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    def inspecting(command: Sequence[str], cwd: Path, timeout: int) -> Any:
        cell_dir = run_contract_ctx.job_dir / cell_id
        state = json.loads((cell_dir / "status.json").read_text())["state"]
        run_contract_ctx.snapshot = (state, (cell_dir / "command.json").is_file())
        return rc.ChildResult(0, "ok\n")

    _launch(run_contract_ctx, [cell_id], runner=inspecting)


@when(
    "the harness is launched for four news-free cells with a concurrency cap of 2 and a slow runner"
)
def _launch_slow(run_contract_ctx: _RunContractCtx) -> None:
    lock = threading.Lock()
    running = 0

    def slow(command: Sequence[str], cwd: Path, timeout: int) -> Any:
        nonlocal running
        with lock:
            running += 1
            run_contract_ctx.peak = max(run_contract_ctx.peak, running)
        time.sleep(0.3)
        with lock:
            running -= 1
        return rc.ChildResult(0, "ok\n")

    _launch(run_contract_ctx, _NEWS_FREE, runner=slow, max_concurrent=2)


# --- Then (hardening) ---


@then("the harness defaults to 1800 seconds per cell and 3 concurrent cells")
def _check_default_caps() -> None:
    assert rc.DEFAULT_TIMEOUT_SECONDS == 1800
    assert rc.DEFAULT_MAX_CONCURRENT == 3


@then("the README states a cap of 3 concurrent containers and a 30-minute timeout per cell")
def _check_readme_caps() -> None:
    text = _README.read_text()
    assert "cap of 3 concurrent LEAN containers" in text
    assert "30-minute timeout per cell" in text


@then("the README's cell table names exactly the registered cell ids with their arm and clock")
def _check_readme_table(run_contract_ctx: _RunContractCtx) -> None:
    rows = _readme_cell_rows()
    assert len(rows) == 14
    assert {cell_id for cell_id, _, _ in rows} == _EXPECTED_FOURTEEN
    manifest = json.loads((run_contract_ctx.job_dir / "manifest.json").read_text())
    by_id = {row["cell_id"]: row for row in manifest}
    for cell_id, arm, clock in rows:
        assert by_id[cell_id]["arm"] == arm
        assert by_id[cell_id]["clock_minutes"] == {"H1": 60, "H4": 240}[clock]


@then(parsers.parse('every cell the README calls launch-ready is "{state}"'))
def _check_ready_cells(run_contract_ctx: _RunContractCtx, state: str) -> None:
    ready, _ = _readme_launch_table()
    assert len(ready) == 6
    assert all(_status(run_contract_ctx, cell_id)["state"] == state for cell_id in ready)


@then(parsers.parse('every cell the README calls blocked is "{state}"'))
def _check_blocked_cells(run_contract_ctx: _RunContractCtx, state: str) -> None:
    ready, blocked = _readme_launch_table()
    assert len(blocked) == 8
    assert ready | blocked == _EXPECTED_FOURTEEN
    assert all(_status(run_contract_ctx, cell_id)["state"] == state for cell_id in blocked)


@then(
    parsers.parse(
        'every cell config has pair "{pair}", window "{start}" to "{end}" and close_on_veto false'
    )
)
def _check_cell_configs(run_contract_ctx: _RunContractCtx, pair: str, start: str, end: str) -> None:
    for cell_id in _EXPECTED_FOURTEEN:
        config = yaml.safe_load((run_contract_ctx.job_dir / cell_id / "config.yaml").read_text())
        assert config["pair"] == pair
        assert (config["window"]["start"], config["window"]["end"]) == (start, end)
        assert config["execution"]["close_on_veto"] is False


@then(parsers.parse('the README states pair "{pair}", window "{window}" and close_on_veto false'))
def _check_readme_config_claims(pair: str, window: str) -> None:
    text = _README.read_text()
    assert f"Every cell: {pair}" in text
    assert f"window {window} inclusive" in text
    assert "`close_on_veto: false` on all 14 cells" in text


@then("the job directory's README is a byte-for-byte copy of the registration README")
def _check_readme_copy(run_contract_ctx: _RunContractCtx) -> None:
    copied = run_contract_ctx.job_dir / "README.md"
    assert copied.read_bytes() == _README.read_bytes()
    assert len(_README.read_bytes()) > 0


@then("the launch returned fourteen statuses in sorted cell id order")
def _check_fourteen_sorted(run_contract_ctx: _RunContractCtx) -> None:
    ids = [status["cell_id"] for status in run_contract_ctx.statuses]
    assert ids == sorted(_EXPECTED_FOURTEEN)


@then(parsers.parse('{ok:d} cells are "{ok_state}" and {blocked:d} cells are "{blocked_state}"'))
def _check_state_counts(
    run_contract_ctx: _RunContractCtx, ok: int, ok_state: str, blocked: int, blocked_state: str
) -> None:
    states = [status["state"] for status in run_contract_ctx.statuses]
    assert states.count(ok_state) == ok
    assert states.count(blocked_state) == blocked


@then("the launch returned no statuses")
def _check_no_statuses(run_contract_ctx: _RunContractCtx) -> None:
    assert run_contract_ctx.error is None, run_contract_ctx.error
    assert run_contract_ctx.statuses == []


@then(parsers.parse('the launch returned statuses for "{first}" then "{second}"'))
def _check_status_order(run_contract_ctx: _RunContractCtx, first: str, second: str) -> None:
    assert [status["cell_id"] for status in run_contract_ctx.statuses] == [first, second]


@then(parsers.parse('the launch is refused with "{fragment}"'))
def _check_refused_with(run_contract_ctx: _RunContractCtx, fragment: str) -> None:
    assert run_contract_ctx.error is not None
    assert fragment in str(run_contract_ctx.error)


@then("the job directory was not created")
def _check_no_job_dir(run_contract_ctx: _RunContractCtx) -> None:
    assert not run_contract_ctx.job_dir.exists()


@then(parsers.parse('loading the sibling script "{name}" is refused'))
def _check_unloadable_script(tmp_path: Path, name: str) -> None:
    (tmp_path / name).write_text("x = 1\n")
    with pytest.raises(ValueError, match="cannot load sibling script"):
        rc._load_script(tmp_path / name)


@then("at most 2 cells ran at the same time and 2 ran together")
def _check_peak(run_contract_ctx: _RunContractCtx) -> None:
    assert run_contract_ctx.error is None, run_contract_ctx.error
    assert len(run_contract_ctx.statuses) == 4
    assert run_contract_ctx.peak == 2


@then(parsers.parse('the preflight was given data root "{root}"'))
def _check_gate_root(run_contract_ctx: _RunContractCtx, root: str) -> None:
    assert run_contract_ctx.gate_seen == [(["m-only-h1"], Path(root))]


@then("the preflight was given the explicit data root")
def _check_gate_explicit_root(run_contract_ctx: _RunContractCtx) -> None:
    assert run_contract_ctx.gate_seen == [(["m-only-h1"], run_contract_ctx.data_root)]


def _cells(
    clocks: Sequence[int],
    *,
    pair: str = "EURUSD",
    start: str = "2016-03-01",
    end: str = "2017-02-28",
) -> list[Any]:
    """Hand-built LaunchCells, one per clock, for calling the real gate directly."""
    return [
        rc.LaunchCell(
            cell_id=f"x-{clock}",
            arm="M-only",
            clock_minutes=clock,
            config_hash="0" * 64,
            pair=pair,
            window_start=start,
            window_end=end,
        )
        for clock in clocks
    ]


@then("the real population gate passes over no cells")
def _check_gate_no_cells(tmp_path: Path) -> None:
    rc.population_gate([], tmp_path)


@then(
    parsers.parse(
        'the real population gate over both clocks fails naming clock {clock:d} and month "{month}"'
    )
)
def _check_gate_fails(run_contract_ctx: _RunContractCtx, clock: int, month: str) -> None:
    with pytest.raises(ValueError, match=f"clock {clock} month {month}"):
        rc.population_gate(_cells((60, 240)), run_contract_ctx.data_root)


@then("the real population gate over both clocks passes")
def _check_gate_passes(run_contract_ctx: _RunContractCtx) -> None:
    rc.population_gate(_cells((60, 240)), run_contract_ctx.data_root)


@then("the real population gate over the H4 clock alone passes")
def _check_gate_h4_only(run_contract_ctx: _RunContractCtx) -> None:
    rc.population_gate(_cells((240,)), run_contract_ctx.data_root)


@then(
    parsers.parse(
        "the real population gate over the H4 clock alone fails naming clock {clock:d} "
        'and month "{month}"'
    )
)
def _check_gate_h4_fails(run_contract_ctx: _RunContractCtx, clock: int, month: str) -> None:
    with pytest.raises(ValueError, match=f"clock {clock} month {month}"):
        rc.population_gate(_cells((240,)), run_contract_ctx.data_root)


@then(
    parsers.parse(
        'the partition expected for pair "{pair}", clock {clock:d} and month "{month}" is the '
        "layout's forex m1 price path"
    )
)
def _check_partition_layout(tmp_path: Path, pair: str, clock: int, month: str) -> None:
    year, month_number = month.split("-")
    expected = layout.price_path(tmp_path, "forex", pair, "m1", int(year), int(month_number))
    assert tmp_path / rc.pf.partition_path(pair, clock, month) == expected


@then(parsers.parse("the real population gate refuses cells that differ in {difference}"))
def _check_gate_disagreement(tmp_path: Path, difference: str) -> None:
    first = _cells((60,))[0]
    other = {
        "pair": replace(first, cell_id="y", pair="GBPUSD"),
        "window start": replace(first, cell_id="y", window_start="2016-04-01"),
        "window end": replace(first, cell_id="y", window_end="2017-01-31"),
    }[difference]
    with pytest.raises(ValueError, match="disagree on pair/window"):
        rc.population_gate([first, other], tmp_path)


@then(parsers.parse('the months between "{start}" and "{end}" are "{months}"'))
def _check_months(start: str, end: str, months: str) -> None:
    actual = rc.months_between(date.fromisoformat(start), date.fromisoformat(end))
    assert ",".join(":".join(row) for row in actual) == months


@then(
    parsers.parse(
        'the recorded command for "{cell_id}" is exactly the algo-backtest run contract '
        "with timeout {secs:d}"
    )
)
def _check_exact_command(run_contract_ctx: _RunContractCtx, cell_id: str, secs: int) -> None:
    recorded = rc._read_json(run_contract_ctx.job_dir / cell_id / "command.json")["command"]
    assert recorded == [
        "uv",
        "run",
        "algo-backtest",
        "run",
        "--strategy",
        cell_id,
        "--symbol",
        "EURUSD",
        "--from",
        "2016-03-01",
        "--to",
        "2017-02-28",
        "--strategies-dir",
        str(run_contract_ctx.job_dir),
        "--timeout",
        str(secs),
    ]
    assert [call[0] for call in run_contract_ctx.calls_full] == [recorded]


@then(parsers.parse("the fake runner was called from the suite directory with timeout {secs:d}"))
def _check_runner_args(run_contract_ctx: _RunContractCtx, secs: int) -> None:
    ((_, cwd, timeout),) = run_contract_ctx.calls_full
    assert cwd == _SUITE_DIR
    assert timeout == secs


@then("the runner saw a running status and a command record while the child was running")
def _check_snapshot(run_contract_ctx: _RunContractCtx) -> None:
    assert run_contract_ctx.snapshot == ("running", True)


def _suite_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=_SUITE_DIR, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


@then(parsers.parse("\"{cell_id}\"'s command and status both record the suite's git revision"))
def _check_revision(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    revision = _suite_revision()
    assert len(revision) == 40
    command_doc = rc._read_json(run_contract_ctx.job_dir / cell_id / "command.json")
    assert command_doc["source_revision"] == revision
    assert _status(run_contract_ctx, cell_id)["source_revision"] == revision


@then(
    parsers.parse(
        '"{cell_id}"\'s command record holds the SHA-256 of the harness, generator and '
        "preflight sources"
    )
)
def _check_code_hashes(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    hashes = rc._read_json(run_contract_ctx.job_dir / cell_id / "command.json")["code_hashes"]
    by_name = {Path(path).name: digest for path, digest in hashes.items()}
    assert set(by_name) == {"run_cells.py", "make_cells.py", "preflight.py"}
    for name, digest in by_name.items():
        assert digest == hashlib.sha256((_SCRIPT_PATH.parent / name).read_bytes()).hexdigest()


@then(parsers.parse('"{cell_id}"\'s status has a start time and a later-or-equal finish time'))
def _check_times(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    status = _status(run_contract_ctx, cell_id)
    started = datetime.fromisoformat(status["started_at"])
    finished = datetime.fromisoformat(status["finished_at"])
    assert started.utcoffset() is not None
    assert finished >= started


@then(parsers.parse('"{cell_id}"\'s run log holds exactly "{text}"'))
def _check_run_log(run_contract_ctx: _RunContractCtx, cell_id: str, text: str) -> None:
    assert (run_contract_ctx.job_dir / cell_id / "run.log").read_text() == _text(text)


@then(parsers.parse('"{cell_id}"\'s run log mentions "{fragment}"'))
def _check_run_log_mentions(run_contract_ctx: _RunContractCtx, cell_id: str, fragment: str) -> None:
    assert fragment in (run_contract_ctx.job_dir / cell_id / "run.log").read_text()


@then(parsers.parse('"{cell_id}"\'s recorded reason is {reason}'))
def _check_reason(run_contract_ctx: _RunContractCtx, cell_id: str, reason: str) -> None:
    expected = None if reason == "null" else reason
    assert _status(run_contract_ctx, cell_id)["reason"] == expected


@then(parsers.parse('"{cell_id}"\'s recorded results directory is {results}'))
def _check_results_dir(run_contract_ctx: _RunContractCtx, cell_id: str, results: str) -> None:
    expected = None if results == "null" else results
    assert _status(run_contract_ctx, cell_id)["results_dir"] == expected


@then(parsers.parse('"{cell_id}" has no start time, no finish time and no source revision'))
def _check_unavailable_blank(run_contract_ctx: _RunContractCtx, cell_id: str) -> None:
    status = _status(run_contract_ctx, cell_id)
    assert status["started_at"] is None
    assert status["finished_at"] is None
    assert status["source_revision"] is None
    assert status["exit_code"] is None
    assert status["results_dir"] is None


def _real_runner_case(behaviour: str, cwd: Path) -> tuple[list[str], int]:
    """(argv, timeout) for one named real-child behaviour."""
    python = sys.executable
    return {
        "prints both": (
            [python, "-c", "import sys;print('out-line');print('err-line',file=sys.stderr)"],
            30,
        ),
        "exits 3": ([python, "-c", "raise SystemExit(3)"], 30),
        "missing exe": (["/nonexistent/definitely-not-here"], 30),
        "overruns": ([python, "-c", "import time;time.sleep(1.5)"], 1),
        "shows cwd": ([python, "-c", "import os;print(os.getcwd())"], 30),
    }[behaviour]


@then(
    parsers.parse(
        'the real runner running "{behaviour}" reports exit code {code:d} '
        'and output containing "{text}"'
    )
)
def _check_real_runner(tmp_path: Path, behaviour: str, code: int, text: str) -> None:
    command, timeout = _real_runner_case(behaviour, tmp_path)
    result = rc._real_runner(command, tmp_path, timeout)
    assert result.exit_code == code
    if behaviour == "shows cwd":
        assert result.output.strip() == str(tmp_path.resolve())
    elif text != "none":
        assert text in result.output


@then(parsers.parse("the git revision for {situation} is None"))
def _check_git_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, situation: str) -> None:
    if situation == "a machine without git":

        def no_git(*args: Any, **kwargs: Any) -> Any:
            raise FileNotFoundError("git")

        monkeypatch.setattr(rc.subprocess, "run", no_git)
    assert rc._git_sha(tmp_path) is None


def _record_launcher(
    monkeypatch: pytest.MonkeyPatch, outcome: str = "reports every cell success"
) -> dict[str, Any]:
    """Replace `launch_job` with a recorder returning/raising per `outcome`."""
    seen: dict[str, Any] = {}

    def fake_launch(job_dir: Path, **kwargs: Any) -> list[dict[str, Any]]:
        seen["job_dir"], seen["kwargs"] = job_dir, kwargs
        if outcome == "refuses the launch":
            raise ValueError("kaput")
        statuses = [{"cell_id": "m-only-h1", "state": "succeeded", "exit_code": 0}]
        if outcome == "reports one cell failed":
            statuses.append({"cell_id": "always-long-h1", "state": "failed", "exit_code": 1})
        return statuses

    monkeypatch.setattr(rc, "launch_job", fake_launch)
    return seen


@then(parsers.parse('running the CLI with "{arguments}" forwards the defaults'))
def _check_cli_defaults(monkeypatch: pytest.MonkeyPatch, arguments: str) -> None:
    seen = _record_launcher(monkeypatch)
    assert rc.main(arguments.split()) == 0
    assert seen["job_dir"] == Path("some/job")
    assert seen["kwargs"] == {
        "cell_ids": None,
        "rerun": (),
        "timeout": 1800,
        "max_concurrent": 3,
        "data_root": None,
    }


@then("running the CLI with every explicit argument forwards each one")
def _check_cli_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _record_launcher(monkeypatch)
    argv = "--job-dir j --cells m-only-h1 m-only-h4 --rerun m-only-h1 --timeout 99"
    argv += " --max-concurrent 2 --data-root some/data"
    assert rc.main(argv.split()) == 0
    assert seen["job_dir"] == Path("j")
    assert seen["kwargs"] == {
        "cell_ids": ["m-only-h1", "m-only-h4"],
        "rerun": ["m-only-h1"],
        "timeout": 99,
        "max_concurrent": 2,
        "data_root": Path("some/data"),
    }


@then(parsers.parse('the CLI against a launcher that {outcome} exits {code:d} and prints "{line}"'))
def _check_cli_outcome(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
    code: int,
    line: str,
) -> None:
    _record_launcher(monkeypatch, outcome)
    assert rc.main(["--job-dir", "j"]) == code
    captured = capsys.readouterr()
    stream = captured.err if code == 2 else captured.out
    assert line in stream.splitlines()
    if code == 2:
        assert captured.out == ""


@then("every time-exit cell config registers min_hold_bars 4 and the A-plan config registers 0")
def _check_min_hold(run_contract_ctx: _RunContractCtx) -> None:
    for cell_id in _EXPECTED_FOURTEEN:
        config = yaml.safe_load((run_contract_ctx.job_dir / cell_id / "config.yaml").read_text())
        expected = 0 if cell_id.startswith("a-plan-") else 4
        assert config["execution"]["min_hold_bars"] == expected


@then("the README states a horizon of N=4 and min_hold_bars 4")
def _check_readme_horizon() -> None:
    text = _README.read_text()
    assert "`N=4`" in text
    assert "`min_hold_bars: 4` on time-exit arms" in text


@then("the README's constant-direction rows and execution costs match every generated config")
def _check_readme_directions_and_costs(run_contract_ctx: _RunContractCtx) -> None:
    text = _README.read_text()
    rows = re.findall(r"\| `(always-(?:short|long)-h[14])` \|[^\n]*constant (SELL|BUY) \|", text)
    assert len(rows) == 4
    for cell_id, direction in rows:
        config = yaml.safe_load((run_contract_ctx.job_dir / cell_id / "config.yaml").read_text())
        assert config["constant_direction"]["direction"] == direction
    assert "spread 1.0 pip, 0 commission per lot" in text
    for cell_id in _EXPECTED_FOURTEEN:
        config = yaml.safe_load((run_contract_ctx.job_dir / cell_id / "config.yaml").read_text())
        assert config["execution"]["spread_pips"] == 1.0
        assert config["execution"]["commission_per_lot"] == 0.0
