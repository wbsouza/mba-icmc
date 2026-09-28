"""Steps for confluence_run_contract.feature — the bounded launch harness (story 21, T17).

`experiments/confluence-chain/run_cells.py` is a standalone script outside the
`algo_backtest` package, loaded here by file path (same pattern as T8/T9/T10's steps).
Every scenario injects a fake runner (never a real LEAN run) and a permissive no-op
population-preflight stub by default, so no scenario touches real data or a real child
process; only the "population preflight that always fails" rule overrides the stub.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
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


@pytest.fixture
def run_contract_ctx(tmp_path: Path) -> _RunContractCtx:
    """A fresh per-scenario context with its own job and data directories."""
    return _RunContractCtx(job_dir=tmp_path / "job", data_root=tmp_path / "data")


def _launch(
    ctx: _RunContractCtx,
    cell_ids: Sequence[str],
    *,
    exit_code: int | None = None,
    rerun: Sequence[str] = (),
) -> None:
    """Launch `cell_ids` through a fresh fake runner, recording its calls onto `ctx`."""
    calls: list[list[str]] = []

    def fake_runner(command: Sequence[str], cwd: Path, timeout: int) -> rc.ChildResult:
        calls.append(list(command))
        return rc.ChildResult(0 if exit_code is None else exit_code, "boom\n")

    try:
        ctx.statuses = rc.launch_job(
            ctx.job_dir,
            cell_ids=list(cell_ids),
            rerun=list(rerun),
            runner=fake_runner,
            population_gate_fn=ctx.population_gate_fn,
            data_root=ctx.data_root,
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
