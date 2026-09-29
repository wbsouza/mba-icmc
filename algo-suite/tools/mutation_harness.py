"""Mutation-testing harness (Hardener gate).

Why not just `mutmut run`: mutmut is still the default Hardener tool here (see
`[tool.mutmut]` in each tool's pyproject.toml) and works for algo-suite's plain
src-layout packages — this harness is NOT a claim that mutmut is broken for
every project. It exists as a fallback for the specific failure classes mutmut
does not defend against on its own:

  - mutmut copies the covered package into a `mutants/` scratch dir and shadows
    sys.path/import machinery to redirect imports there for the duration of a
    run. That composes cleanly with a plain `import algo_download...`, but
    breaks silently (every mutant reported "caught" with none of the mutated
    code ever executed) for any import path that resolves outside a plain
    sys.path scan — e.g. a workspace member imported through its own installed
    location rather than through the mutated copy. algo-core is depended on by
    every other tool via `[tool.uv.sources] algo-core = { workspace = true }`;
    mutating algo-core while a *different* tool's test suite exercises it would
    hit exactly this class of silent false-negative. Mutating a tool's own
    src/ while running that tool's own tests (today's usage) does not, but the
    risk moves with the workspace, not with today's usage pattern.
  - A process killed mid-mutation (task timeout, operator SIGTERM/SIGINT) can
    leave a mutated file on disk with nothing to revert it — this harness
    mutates the real source file in place (not a `mutants/` copy) and needs
    its own signal/atexit revert net to be safe to run unattended.
  - `if max_mutants:` treats `--max 0` as falsy (run everything, not nothing).

Usage:
    uv run python tools/mutation_harness.py TOOL [--paths p1,p2] [--max N]

TOOL is one of the uv workspace members (algo-core, algo-download,
algo-transform, algo-score, algo-backtest, algo-analyze). Scope defaults to
that tool's whole `src/<package>/` tree, excluding `__init__.py`, `spikes/`,
`algos/`, and `mutants/` (same exclusions as the workspace's ruff/mypy config)
— business logic only, same domain/service_layer vs. adapters/entrypoints
split as mutmut's own `[tool.mutmut] only_mutate` scoping.
"""

from __future__ import annotations

import argparse
import ast
import atexit
import contextlib
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

# A mutated test suite is untrusted: a broken loop-termination mutant (e.g. an
# arith flip in a date-range rollover) can turn a bounded loop unbounded and
# drive the pytest child's RSS toward all of host RAM. Uncapped, that reaches
# the kernel OOM-killer -- and on this host each tmux pane is its own systemd
# --scope unit, so an OOM kill of the pytest child (not the shell) still gets
# the *whole scope* torn down ~90s later on "Stopping timed out. Killing.",
# SIGKILLing the pane's shell as collateral and silently closing the tmux
# window mid-run (observed 3x: 2026-09-24 dmesg/journalctl show oom-kill of
# `pytest` in `tmux-spawn-*.scope`, followed by a scope-stop-timeout SIGKILL
# of the pane's zsh). Override via MUTATION_HARNESS_CHILD_MEM_MB if a tool's
# suite legitimately needs more.
_CHILD_MEM_CAP_MB = int(os.environ.get("MUTATION_HARNESS_CHILD_MEM_MB", "4096"))

# Tracks the file/content currently mutated on disk, so a killed process (SIGTERM from
# an operator, a task-manager timeout, anything short of SIGKILL) still restores the
# real source instead of leaving a mutant applied in the working tree.
_PENDING_REVERT: tuple[Path, str] | None = None

# Tracks the pgid of a live `uv run pytest` subprocess group, so a harness
# process killed mid-test (operator SIGTERM/SIGINT, tmux window closed) still
# reaps the whole tree instead of leaving an orphaned, full-CPU pytest running
# — the same failure mode the timeout branch in run_tool_tests guards against.
_PENDING_PROC_GROUP: int | None = None


def _revert_pending() -> None:
    global _PENDING_REVERT
    if _PENDING_REVERT is not None:
        path, original = _PENDING_REVERT
        path.write_text(original)
        _PENDING_REVERT = None


def _kill_pending_proc_group() -> None:
    global _PENDING_PROC_GROUP
    if _PENDING_PROC_GROUP is not None:
        with contextlib.suppress(ProcessLookupError):  # already exited between check and kill
            os.killpg(_PENDING_PROC_GROUP, signal.SIGKILL)
        _PENDING_PROC_GROUP = None


def _handle_termination(signum, frame):  # noqa: ANN001 - signal handler signature
    _kill_pending_proc_group()
    _revert_pending()
    sys.exit(128 + signum)


atexit.register(_revert_pending)
atexit.register(_kill_pending_proc_group)
signal.signal(signal.SIGTERM, _handle_termination)
signal.signal(signal.SIGINT, _handle_termination)

REPO_ROOT = Path(__file__).resolve().parents[1]

_EXCLUDED_DIR_NAMES = {"spikes", "algos", "mutants"}

_CMP_FLIPS = {
    ast.Lt: ast.GtE,
    ast.LtE: ast.Gt,
    ast.Gt: ast.LtE,
    ast.GtE: ast.Lt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
}
_BOOL_FLIPS = {ast.And: ast.Or, ast.Or: ast.And}
_ARITH_FLIPS = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}


@dataclass
class Mutant:
    file: Path
    lineno: int
    description: str
    apply: object  # callable(ast.Module) -> None, mutates the tree in place
    verdict: str = "pending"
    detail: str = ""


@dataclass
class MutationReport:
    tool: str
    mutants: list = field(default_factory=list)

    def summary(self) -> dict:
        killed = sum(1 for m in self.mutants if m.verdict == "killed")
        survived = sum(1 for m in self.mutants if m.verdict == "survived")
        errored = sum(1 for m in self.mutants if m.verdict == "error")
        total = len(self.mutants)
        denom = total - errored
        score = (killed / denom * 100.0) if denom else 100.0
        return {
            "tool": self.tool,
            "total": total,
            "killed": killed,
            "survived": survived,
            "errored": errored,
            "score_pct": round(score, 1),
        }


class _SingleNodeMutator(ast.NodeTransformer):
    """Mutates only the Nth matching node (by visit order); leaves everything else untouched."""

    def __init__(self, target_index, predicate, mutate):
        self.target_index = target_index
        self.predicate = predicate
        self.mutate = mutate
        self._count = -1
        self.applied = False

    def generic_visit(self, node):
        if self.predicate(node):
            self._count += 1
            if self._count == self.target_index and not self.applied:
                self.applied = True
                mutated = self.mutate(node)
                node = mutated if mutated is not None else node
        return super().generic_visit(node)


def _is_compare(node):
    return isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMP_FLIPS


def _is_boolop(node):
    return isinstance(node, ast.BoolOp) and type(node.op) in _BOOL_FLIPS


def _is_not(node):
    return isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not)


def _is_binop(node):
    return isinstance(node, ast.BinOp) and type(node.op) in _ARITH_FLIPS


def _dfs_preorder(node):
    """Pre-order DFS matching ast.NodeTransformer.generic_visit's own traversal order
    (node itself, then each field in declaration order, recursing into lists/nodes).

    ast.walk() is BFS and does NOT match this order for nested nodes at different
    depths — using it here to assign each mutant's index/lineno while
    _SingleNodeMutator applies mutations via NodeTransformer (DFS) meant the Nth
    mutant reported could be a DIFFERENT node than the Nth one actually mutated
    whenever a file had matching nodes at unequal nesting depths. Both counting and
    applying must walk the tree the same way.
    """
    yield node
    for _field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield from _dfs_preorder(item)
        elif isinstance(value, ast.AST):
            yield from _dfs_preorder(value)


def _count_matching(tree, predicate) -> int:
    return sum(1 for node in _dfs_preorder(tree) if predicate(node))


def _find_nth(tree, predicate, index):
    count = -1
    for node in _dfs_preorder(tree):
        if predicate(node):
            count += 1
            if count == index:
                return node
    raise IndexError(index)


def _make_apply(predicate, index, mutate):
    def _apply(tree):
        _SingleNodeMutator(index, predicate, mutate).visit(tree)

    return _apply


def _flip_compare(node):
    node.ops = [_CMP_FLIPS[type(node.ops[0])]()]
    return node


def _flip_boolop(node):
    node.op = _BOOL_FLIPS[type(node.op)]()
    return node


def _strip_not(node):
    return node.operand


def _flip_binop(node):
    node.op = _ARITH_FLIPS[type(node.op)]()
    return node


def generate_mutants(path: Path) -> list[Mutant]:
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    mutants: list[Mutant] = []

    def add(predicate, describe, mutate, kind):
        n = _count_matching(tree, predicate)
        for i in range(n):
            node = _find_nth(tree, predicate, i)
            mutants.append(
                Mutant(
                    file=path,
                    lineno=getattr(node, "lineno", 0),
                    description=f"{kind}@L{getattr(node, 'lineno', 0)}: {describe(node)}",
                    apply=_make_apply(predicate, i, mutate),
                )
            )

    add(_is_compare, lambda n: f"{type(n.ops[0]).__name__} flip", _flip_compare, "compare")
    add(_is_boolop, lambda n: f"{type(n.op).__name__} flip", _flip_boolop, "boolop")
    add(_is_not, lambda n: "remove not", _strip_not, "not")
    add(_is_binop, lambda n: f"{type(n.op).__name__} flip", _flip_binop, "arith")

    return mutants


def _package_name(tool: str) -> str:
    return tool.replace("-", "_")


def iter_target_files(tool: str, extra_paths: list[str] | None = None) -> list[Path]:
    tool_dir = REPO_ROOT / tool
    if extra_paths:
        files: list[Path] = []
        for p in extra_paths:
            fp = tool_dir / p
            if fp.is_dir():
                files.extend(sorted(fp.rglob("*.py")))
            elif fp.is_file():
                files.append(fp)
        return files
    src_dir = tool_dir / "src" / _package_name(tool)
    if not src_dir.is_dir():
        return []
    return [
        f
        for f in sorted(src_dir.rglob("*.py"))
        if f.name != "__init__.py" and not _EXCLUDED_DIR_NAMES & set(f.relative_to(tool_dir).parts)
    ]


def _memory_capped_preexec() -> None:
    """Apply the RLIMIT_AS fallback memory cap in the child before exec (no systemd-run)."""
    resource.setrlimit(
        resource.RLIMIT_AS, (_CHILD_MEM_CAP_MB * 1024 * 1024, resource.RLIM_INFINITY)
    )


def cap_memory(cmd: list[str]) -> tuple[list[str], Callable[[], None] | None]:
    """Wraps cmd to enforce _CHILD_MEM_CAP_MB, isolated in its own cgroup scope when possible.

    Prefers `systemd-run --scope -p MemoryMax=...`: a mutant that runs away in memory
    then gets OOM-killed inside its OWN transient scope, not the caller's (e.g. the tmux
    pane's) scope -- avoiding the collateral scope-stop-timeout kill described above.
    Falls back to an RLIMIT_AS preexec_fn (same host cap, no scope isolation) when
    systemd-run isn't on PATH.
    """
    if shutil.which("systemd-run"):
        wrapped = [
            "systemd-run",
            "--user",
            "--scope",
            "--collect",
            "--quiet",
            "-p",
            f"MemoryMax={_CHILD_MEM_CAP_MB}M",
            "--",
            *cmd,
        ]
        return wrapped, None
    return cmd, _memory_capped_preexec


def run_tool_tests(tool: str, timeout: int = 900) -> tuple[bool, str]:
    """True = suite passed (mutant survived); False = suite failed (mutant killed)."""
    tool_dir = REPO_ROOT / tool
    confcutdir = tool_dir / "tests"
    cmd = [
        "uv",
        "run",
        "pytest",
        "tests",
        "-q",
        "-p",
        "no:cacheprovider",
        "--color=no",
        f"--confcutdir={confcutdir}",
    ]
    cmd, preexec_fn = cap_memory(cmd)
    global _PENDING_PROC_GROUP
    proc_handle = subprocess.Popen(
        cmd,
        cwd=str(tool_dir),
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
        preexec_fn=preexec_fn,
    )
    # `uv run pytest` forks pytest as a real child (not an exec-replace), so
    # killing proc_handle alone leaves pytest (and anything it spawned) orphaned
    # and running at full CPU indefinitely — the actual cause of prior host
    # freezes. start_new_session=True puts the whole tree in its own process
    # group; killpg reaches all of it. _PENDING_PROC_GROUP lets a harness kill
    # (SIGTERM/SIGINT/atexit) reap it too, not just the timeout path below.
    _PENDING_PROC_GROUP = proc_handle.pid
    try:
        out, _ = proc_handle.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):  # already exited between timeout and kill
            os.killpg(proc_handle.pid, signal.SIGKILL)
        proc_handle.communicate()
        return True, "TIMEOUT (treated as survived — inconclusive, needs manual replay)"
    finally:
        _PENDING_PROC_GROUP = None
    passed = proc_handle.returncode == 0
    tail = "\n".join(out.splitlines()[-25:])
    return passed, tail


def mutate_file(path: Path, apply) -> str:
    original = path.read_text()
    tree = ast.parse(original, filename=str(path))
    apply(tree)
    mutated_src = ast.unparse(ast.fix_missing_locations(tree))
    path.write_text(mutated_src)
    return original


def run_campaign(tool: str, extra_paths, max_mutants, timeout: int) -> MutationReport:
    files = iter_target_files(tool, extra_paths)
    report = MutationReport(tool=tool)
    all_mutants: list[Mutant] = []
    for f in files:
        try:
            all_mutants.extend(generate_mutants(f))
        except SyntaxError as e:
            print(f"SKIP {f}: {e}", file=sys.stderr)
    if max_mutants is not None:
        all_mutants = all_mutants[:max_mutants]

    print(f"[{tool}] {len(all_mutants)} mutants across {len(files)} files", flush=True)
    global _PENDING_REVERT
    tool_dir = REPO_ROOT / tool
    for i, m in enumerate(all_mutants, 1):
        original = mutate_file(m.file, m.apply)
        _PENDING_REVERT = (m.file, original)
        try:
            passed, tail = run_tool_tests(tool, timeout=timeout)
            m.verdict = "survived" if passed else "killed"
            m.detail = tail if passed else ""
        except Exception as e:  # noqa: BLE001 - harness must never crash the campaign
            m.verdict = "error"
            m.detail = str(e)
        finally:
            m.file.write_text(original)
            _PENDING_REVERT = None
        report.mutants.append(m)
        rel_file = m.file.relative_to(tool_dir)
        print(
            f"  [{i}/{len(all_mutants)}] {rel_file} :: "
            f"{m.description} -> {m.verdict}",
            flush=True,
        )

    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tool", help="uv workspace member, e.g. algo-download")
    ap.add_argument(
        "--paths",
        help="comma-separated paths (relative to the tool dir) to scope mutation to",
    )
    ap.add_argument("--max", type=int, default=None, help="cap number of mutants (debugging)")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--report", default=None, help="write JSON report to this path")
    args = ap.parse_args()

    extra_paths = args.paths.split(",") if args.paths else None
    report = run_campaign(args.tool, extra_paths, args.max, args.timeout)
    summary = report.summary()
    print(json.dumps(summary, indent=2))

    if args.report:
        tool_dir = REPO_ROOT / args.tool
        out = {
            "summary": summary,
            "mutants": [
                {
                    "file": str(m.file.relative_to(tool_dir)),
                    "line": m.lineno,
                    "description": m.description,
                    "verdict": m.verdict,
                }
                for m in report.mutants
            ],
        }
        Path(args.report).write_text(json.dumps(out, indent=2))

    survivors = [m for m in report.mutants if m.verdict == "survived"]
    if survivors:
        tool_dir = REPO_ROOT / args.tool
        print(f"\n{len(survivors)} SURVIVORS:")
        for m in survivors:
            print(f"  {m.file.relative_to(tool_dir)}:{m.lineno} {m.description}")


if __name__ == "__main__":
    main()
