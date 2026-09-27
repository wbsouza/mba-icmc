"""Check perception dependency boundaries and coverage-weighted complexity.

Run from algo-suite after collecting host and native-runtime coverage::

    uv run python tools/perception_quality.py --coverage build/perception-coverage.json

The coverage JSON uses coverage.py's ``coverage json`` format. Every executable
line must appear, including native-runtime modules; missing files fail the gate.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any, cast

from radon.complexity import cc_visit  # type: ignore[import-untyped]

PACKAGE = Path(__file__).resolve().parents[1] / "algo-backtest/src/algo_backtest/perception"
# The pure transform/config remain host-importable. Only the runtime adapters may
# depend on QuantConnect; perception must never import engine or chain policy.
ALLOWED = {
    "__init__": set(),
    "config": set(),
    "heikin_ashi": set(),
    "lean_indicator": {"algo_backtest.perception.heikin_ashi", "QuantConnect.Indicators"},
    "multi_timeframe": {
        "algo_backtest.perception.heikin_ashi",
        "algo_backtest.perception.lean_indicator",
        "QuantConnect.Data.Market",
        "QuantConnect.Data.Consolidators",
    },
}


def dependencies(tree: ast.AST) -> set[str]:
    """Collect static imports and the adapters' literal import_module calls."""
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "import_module" and node.args
        ):
            modules.add(ast.literal_eval(node.args[0]))
    return modules


def architecture_errors(path: Path, source: str) -> list[str]:
    """Reject new modules and imports crossing the explicit dependency contract."""
    if path.stem not in ALLOWED:
        return [f"{path.name}: module has no dependency contract"]
    internal = {
        module for module in dependencies(ast.parse(source))
        if module.startswith(("algo_backtest", "QuantConnect", "AlgorithmImports"))
    }
    return [
        f"{path.name}: forbidden dependency {module}"
        for module in sorted(internal - ALLOWED[path.stem])
    ]


def covered_file(files: dict[str, Any], path: Path) -> dict[str, Any]:
    """Match coverage from either host source paths or mounted LEAN source paths."""
    suffix = f"algo_backtest/perception/{path.name}"
    matches = [data for name, data in files.items() if name.endswith(suffix)]
    if len(matches) != 1:
        raise ValueError(f"{path.name}: expected one coverage record, found {len(matches)}")
    return cast(dict[str, Any], matches[0])


def function_scores(source: str, data: dict[str, Any]) -> list[tuple[str, int, float, float]]:
    """Calculate CRAP = CC² × (1 - line coverage)³ + CC for each function."""
    executed = set(data["executed_lines"])
    statements = executed | set(data["missing_lines"])
    functions = [block for block in cc_visit(source) if not hasattr(block, "methods")]
    scores = []
    for function in functions:
        lines = statements.intersection(range(function.lineno, function.endline + 1))
        coverage = len(lines & executed) / len(lines) if lines else 1.0
        complexity = function.complexity
        crap = complexity**2 * (1 - coverage)**3 + complexity
        scores.append((function.fullname, complexity, coverage, crap))
    return scores


def check(coverage_path: Path, threshold: float) -> int:
    """Print reviewable function scores and fail on dependency or CRAP violations."""
    files = json.loads(coverage_path.read_text())["files"]
    errors = []
    for path in sorted(PACKAGE.glob("*.py")):
        source = path.read_text()
        errors.extend(architecture_errors(path, source))
        if path.stem == "__init__":
            continue
        try:
            scores = function_scores(source, covered_file(files, path))
        except ValueError as exc:
            errors.append(str(exc))
            continue
        for name, complexity, coverage, crap in scores:
            print(f"{path.name}:{name} CC={complexity} coverage={coverage:.1%} CRAP={crap:.3f}")
            if crap > threshold:
                errors.append(f"{path.name}:{name}: CRAP {crap:.3f} exceeds {threshold}")
    for error in errors:
        print(f"FAIL: {error}")
    print(f"Perception architecture and CRAP gate: {'FAIL' if errors else 'PASS'}")
    return int(bool(errors))


def main() -> int:
    """Read the coverage artifact and run the story's deterministic Cleaner gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=8.0)
    args = parser.parse_args()
    return check(args.coverage, args.threshold)


if __name__ == "__main__":
    raise SystemExit(main())
