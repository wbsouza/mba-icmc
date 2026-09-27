"""Story 04k mutation gate, using isolated imports and the real native BDD probe.

Run ``uv run python tools/perception_mutations.py [--native]`` from algo-suite.
The default covers pure config/HA; --native also covers LEAN adapters. The
existing harness supplies mutation operators and a process memory limit.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import cast

_harness = import_module("mutation_harness")
cap_memory = _harness.cap_memory
generate_mutants = _harness.generate_mutants

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "algo-backtest/src/algo_backtest"
TESTS = ROOT / "algo-backtest/tests/steps"


def run(scratch: Path, native: bool) -> tuple[int, str]:
    """Require imports from the isolated package before invoking bounded pytest."""
    expression = """
import pathlib, sys, algo_backtest
assert pathlib.Path(algo_backtest.__file__).is_relative_to(sys.argv[1])
import pytest
raise SystemExit(pytest.main(sys.argv[2:]))
"""
    command = [sys.executable, "-B", "-c", expression, str(scratch),
               str(TESTS / "test_double_smoothed_heikin_ashi.py"),
               str(TESTS / "test_perception_hardening.py"), "-q", "-m",
               "" if native else "not integration", "-p", "no:cacheprovider",
               "--basetemp", str(scratch / "pytest-results")]
    command, preexec = cap_memory(command)
    environment = dict(os.environ, PYTHONPATH=str(scratch), PYTHONDONTWRITEBYTECODE="1")
    process = subprocess.Popen(command, cwd=ROOT, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               start_new_session=True, preexec_fn=preexec)
    try:
        output, _ = process.communicate(timeout=180)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        return 124, "TIMEOUT: inconclusive"
    return process.returncode, output


def main() -> int:
    """Execute every generated mutation and preserve a reviewable JSON report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", action="store_true")
    parser.add_argument("--report", type=Path, default=ROOT / "build/perception-mutations.json")
    args = parser.parse_args()
    names = ["config.py", "heikin_ashi.py"]
    if args.native:
        names += ["lean_indicator.py", "multi_timeframe.py", "../engine/chain_algorithm.py"]
    records = []
    with tempfile.TemporaryDirectory(prefix="perception-mutations-") as directory:
        scratch = Path(directory)
        package = scratch / "algo_backtest"
        shutil.copytree(SOURCE, package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        code, output = run(scratch, args.native)
        if code or "skipped" in output:
            print(output)
            raise SystemExit("Baseline failed or skipped: mutation results would be invalid")
        for name in names:
            original = SOURCE / "perception" / name
            target = package / "perception" / name
            text = original.read_text()
            wiring_lines = {line for node in ast.walk(ast.parse(text))
                            if isinstance(node, ast.FunctionDef)
                            and node.name in {"_subscribe_indicators", "_indicators_ready"}
                            for line in range(node.lineno, (node.end_lineno or node.lineno) + 1)}
            for mutant in generate_mutants(original):
                if name.startswith("../") and mutant.lineno not in wiring_lines:
                    continue
                tree = ast.parse(text)
                cast(Callable[[ast.AST], None], mutant.apply)(tree)
                target.write_text(ast.unparse(ast.fix_missing_locations(tree)))
                try:
                    code, output = run(scratch, name not in {"config.py", "heikin_ashi.py"})
                finally:
                    target.write_text(text)
                verdict = "killed" if code == 1 else "survived" if code == 0 else "error"
                record = {"file": name, "line": mutant.lineno,
                          "mutation": mutant.description, "verdict": verdict}
                if verdict != "killed":
                    record["output"] = output[-3000:]
                records.append(record)
                print(f"{name} {mutant.description}: {verdict}", flush=True)
    summary = {name: sum(row["verdict"] == name for row in records)
               for name in ("killed", "survived", "error")}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"summary": summary, "mutants": records}, indent=2))
    print(summary)
    return int(bool(summary["survived"] or summary["error"]))


if __name__ == "__main__":
    raise SystemExit(main())
