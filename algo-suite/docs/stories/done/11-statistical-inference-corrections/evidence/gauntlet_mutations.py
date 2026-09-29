"""Reproduce all Story 11 repository-harness mutants in isolated source snapshots.

Use --reuse REPORT to retain killed outcomes only for byte-identical source files;
all survivors and every changed file's mutants are executed again. No mutant cap.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / "tools/mutation_harness.py").exists())
PACKAGE = ROOT / "algo-analyze"
OUTPUT = Path(__file__).resolve().parent
FILES = ("deflated.py", "significance.py", "portfolio.py", "reports.py")


def harness() -> Any:
    """Use the repository's existing AST operators without redefining or sampling them."""
    spec = importlib.util.spec_from_file_location(
        "mutation_harness", ROOT / "tools/mutation_harness.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def summary(output: str) -> str:
    """Retain decisive assertion/test-count lines without repeated full tracebacks."""
    lines = output.splitlines()
    decisive = [line for line in lines if line.startswith(("FAILED ", "ERROR "))]
    return "\n".join([*decisive, *lines[-2:]])[-2000:]


def check(folder: Path) -> tuple[int, str]:
    """Run the actual suite against the copied package, with bytecode caching disabled."""
    command = [str(ROOT / ".venv/bin/python"), "-m", "pytest", str(folder / "tests"),
               "-q", "-x", "-p", "no:cacheprovider", "-c", str(ROOT / "pyproject.toml"),
               "--confcutdir=" + str(folder / "tests")]
    process = subprocess.run(command, cwd=folder,
                             env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                             capture_output=True, text=True, timeout=120)
    return process.returncode, summary(process.stdout + process.stderr)


def snapshot(base: Path) -> dict[str, str]:
    """Copy source and tests without carrying stale compiled mutants into a process."""
    for directory in ("src", "tests"):
        shutil.copytree(PACKAGE / directory, base / directory,
                        ignore=shutil.ignore_patterns("__pycache__"))
    return {name: (base / "src/algo_analyze" / name).read_text() for name in FILES}


def preflight(base: Path, sources: dict[str, str]) -> dict[str, Any]:
    """Require a clean baseline and a known failing change to the imported copied source."""
    baseline = check(base)
    if baseline[0]:
        raise RuntimeError(f"baseline failed: {baseline}")
    probe = base / "src/algo_analyze/deflated.py"
    probe.write_text(sources["deflated.py"].replace("return NormalDist().cdf(z)", "return -9999.0"))
    try:
        control = check(base)
    finally:
        probe.write_text(sources["deflated.py"])
    if control[0] != 1:
        raise RuntimeError(f"negative control failed to detect corruption: {control}")
    return {"baseline": baseline, "negative_control": control}


def execute(item: tuple[str, int, Any], base: Path, tool: Any) -> dict[str, Any]:
    """Execute one mutant in an isolated tree and classify timeouts as inconclusive errors."""
    name, index, mutant = item
    with tempfile.TemporaryDirectory(prefix="mutant-", dir=base) as directory:
        folder = Path(directory)
        for part in ("src", "tests"):
            shutil.copytree(base / part, folder / part)
        tool.mutate_file(folder / "src/algo_analyze" / name, mutant.apply)
        try:
            code, detail = check(folder)
            verdict = "survived" if code == 0 else "killed" if code == 1 else "error"
        except subprocess.TimeoutExpired:
            code, detail, verdict = -1, "TIMEOUT", "error"
    print(f"{name}:{index} {mutant.description}: {verdict}", flush=True)
    return {"file": name, "index": index, "line": mutant.lineno,
            "description": mutant.description, "verdict": verdict,
            "returncode": code, "detail": detail}


def reusable(previous: dict[str, Any], hashes: dict[str, str]) -> dict[tuple[str, int], Any]:
    """Retain only proven kills where the entire corresponding source file is unchanged."""
    return {(row["file"], row["index"]): row for row in previous.get("mutants", [])
            if row["verdict"] == "killed"
            and previous["source_sha256"][row["file"]] == hashes[row["file"]]}


def campaign(base: Path, previous: dict[str, Any]) -> dict[str, Any]:
    """Enumerate every eligible mutant and execute every outcome without a reusable proof."""
    tool = harness()
    sources = snapshot(base)
    report = preflight(base, sources)
    hashes = {name: hashlib.sha256(value.encode()).hexdigest() for name, value in sources.items()}
    retained = reusable(previous, hashes)
    mutants = [(name, index, mutant) for name in FILES for index, mutant in enumerate(
        tool.generate_mutants(base / "src/algo_analyze" / name))]
    pending = [item for item in mutants if (item[0], item[1]) not in retained]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fresh = list(pool.map(lambda item: execute(item, base, tool), pending))
    results = {**retained, **{(row["file"], row["index"]): row for row in fresh}}
    report.update(source_sha256=hashes, executed_in_this_run=len(fresh), reused_kills=len(retained),
                  operators="repository harness: simple comparisons, and/or, not, + - * /; no cap",
                  mutants=[results[(name, index)] for name, index, _ in mutants])
    if any((PACKAGE / "src/algo_analyze" / name).read_text() != text
           for name, text in sources.items()):
        raise RuntimeError("source changed while campaign executed; results require replay")
    return report


def main() -> None:
    """Archive complete outcomes and fail the gate on every unexplained surviving mutant."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT / "gauntlet-mutations-final.json")
    args = parser.parse_args()
    previous = json.loads(args.reuse.read_text()) if args.reuse else {}
    with tempfile.TemporaryDirectory(prefix="story11-hardener-") as directory:
        report = campaign(Path(directory), previous)
    report["reused_from"] = str(args.reuse) if args.reuse else None
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    counts = {verdict: sum(row["verdict"] == verdict for row in report["mutants"])
              for verdict in ("killed", "survived", "error")}
    print(json.dumps(counts), flush=True)
    if counts["survived"] or counts["error"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
