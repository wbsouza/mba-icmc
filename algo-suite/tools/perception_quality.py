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
    "offline": {"algo_backtest.perception.heikin_ashi"},
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


def merge_native_coverage(coverage_path: Path, native_dir: Path, output: Path) -> None:
    """Union native traced lines with the host's executable-line universe."""
    traces = list(native_dir.rglob("perception-native-lines.json"))
    if len(traces) != 1:
        raise ValueError(f"Expected one native trace artifact, found {len(traces)}")
    native = json.loads(traces[0].read_text())
    report = json.loads(coverage_path.read_text())
    for path in sorted(PACKAGE.glob("*.py")):
        if path.stem == "__init__":
            continue
        data = covered_file(report["files"], path)
        suffix = f"algo_backtest/perception/{path.name}"
        traced = [lines for name, lines in native.items() if name.endswith(suffix)]
        if path.stem in {"lean_indicator", "multi_timeframe"} and len(traced) != 1:
            raise ValueError(f"{path.name}: missing or ambiguous native trace")
        statements = set(data["executed_lines"]) | set(data["missing_lines"])
        executed = (set(data["executed_lines"]) | set().union(*traced)) & statements
        data["executed_lines"] = sorted(executed)
        data["missing_lines"] = sorted(statements - executed)
        # Host percentages/branch data no longer describe this merged line-only report.
        for field in ("summary", "executed_branches", "missing_branches"):
            data.pop(field, None)
    report.pop("totals", None)
    report["meta"]["branch_coverage"] = False
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2))


def check_architecture() -> int:
    """Run the dependency gate without coverage or a native runtime."""
    errors = [error for path in sorted(PACKAGE.glob("*.py"))
              for error in architecture_errors(path, path.read_text())]
    for error in errors:
        print(f"FAIL: {error}")
    print(f"Perception architecture gate: {'FAIL' if errors else 'PASS'}")
    return int(bool(errors))


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
    parser.add_argument("--architecture-only", action="store_true")
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--native-lines-dir", type=Path)
    parser.add_argument(
        "--merged-coverage", type=Path, default=Path("build/perception-coverage.json")
    )
    parser.add_argument("--threshold", type=float, default=8.0)
    args = parser.parse_args()
    if args.architecture_only:
        return check_architecture()
    if args.coverage is None:
        parser.error("--coverage is required unless --architecture-only is selected")
    if args.native_lines_dir is not None:
        merge_native_coverage(args.coverage, args.native_lines_dir, args.merged_coverage)
        args.coverage = args.merged_coverage
    return check(args.coverage, args.threshold)


if __name__ == "__main__":
    raise SystemExit(main())
