"""Deterministic Story 11 architecture, coverage, and CRAP gate."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

from quality_common import function_scores

PACKAGE = Path(__file__).resolve().parents[1] / "algo-analyze/src/algo_analyze"
CORE = ("deflated", "significance", "portfolio", "reports")
CLI_FUNCTIONS = {"metrics", "significance", "inference_inventory"}
ALLOWED = {
    "deflated": {"__future__", "math", "collections.abc", "statistics"},
    "significance": {"__future__", "math", "collections.abc", "dataclasses", "numpy",
                     "numpy.typing", "algo_analyze.deflated"},
    "portfolio": {"__future__", "hashlib", "json", "math", "dataclasses", "datetime",
                  "pathlib", "typing", "algo_analyze.deflated"},
    "reports": {
        "__future__", "math", "dataclasses", "pathlib", "statistics", "typing",
        "algo_backtest.metrics", "algo_analyze.deflated", "algo_analyze.portfolio",
        "algo_analyze.significance",
    },
}


def architecture_errors(module: str, source: str) -> list[str]:
    """Reject undeclared dependencies, relative-import bypasses, and dynamic imports."""
    errors: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports = [f"algo_analyze.{node.module}" if node.level else str(node.module)]
        else:
            imports = []
        errors.extend(f"{module}: forbidden dependency {name}"
                      for name in imports if name not in ALLOWED[module])
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {"__import__", "eval", "exec", "open"}):
            errors.append(f"{module}: forbidden dynamic/IO call {node.func.id}")
    return errors


def coverage_record(files: dict[str, Any], module: str) -> dict[str, Any]:
    """Require one unambiguous coverage record for each scoped module."""
    records = [value for name, value in files.items()
               if name.endswith(f"algo_analyze/{module}.py")]
    if len(records) != 1:
        raise ValueError(f"{module}: expected one coverage record, found {len(records)}")
    return dict(records[0])


def score_module(module: str, files: dict[str, Any]) -> list[str]:
    """Enforce 95% line coverage in core modules and CRAP <=8 on scoped functions."""
    source = (PACKAGE / f"{module}.py").read_text()
    errors = architecture_errors(module, source) if module in CORE else []
    data = coverage_record(files, module)
    executed, missing = len(data["executed_lines"]), len(data["missing_lines"])
    coverage = executed / (executed + missing)
    if module in CORE and coverage < .95:
        errors.append(f"{module}: line coverage {coverage:.1%} below 95%")
    if module == "cli" and coverage < .95:
        errors.append(f"{module}: line coverage {coverage:.1%} below 95%")
    for name, complexity, covered, crap in function_scores(source, data):
        if module == "cli" and name not in CLI_FUNCTIONS:
            continue
        print(f"{module}.{name}: CC={complexity}, coverage={covered:.1%}, CRAP={crap:.3f}")
        if crap > 8:
            errors.append(f"{module}.{name}: CRAP {crap:.3f} exceeds 8")
    return errors


def main() -> int:
    """Run the fixed story scope without excluding newly uncovered paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--architecture-only", action="store_true")
    parser.add_argument("--coverage", type=Path)
    args = parser.parse_args()
    if args.architecture_only:
        architecture_failures = [error for module in CORE for error in architecture_errors(
            module, (PACKAGE / f"{module}.py").read_text()
        )]
        for error in architecture_failures:
            print(f"FAIL: {error}")
        print(f"Inference architecture gate: {'FAIL' if architecture_failures else 'PASS'}")
        return int(bool(architecture_failures))
    if args.coverage is None:
        parser.error("--coverage is required unless --architecture-only is selected")
    files = json.loads(args.coverage.read_text())["files"]
    errors: list[str] = []
    for module in (*CORE, "cli"):
        try:
            errors.extend(score_module(module, files))
        except ValueError as exc:
            errors.append(str(exc))
    for error in errors:
        print(f"FAIL: {error}")
    print(f"Inference quality gate: {'FAIL' if errors else 'PASS'}")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
