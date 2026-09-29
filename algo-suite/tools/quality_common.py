"""Shared static complexity helpers used by architecture quality gates."""

from __future__ import annotations

from typing import Any

from radon.complexity import cc_visit  # type: ignore[import-untyped]


def function_scores(source: str, data: dict[str, Any]) -> list[tuple[str, int, float, float]]:
    """Calculate CRAP = CC² × (1 - line coverage)³ + CC for each function."""
    executed = set(data["executed_lines"])
    statements = executed | set(data["missing_lines"])
    scores = []
    for function in (block for block in cc_visit(source) if not hasattr(block, "methods")):
        lines = statements.intersection(range(function.lineno, function.endline + 1))
        coverage = len(lines & executed) / len(lines) if lines else 1.0
        complexity = function.complexity
        crap = complexity**2 * (1 - coverage) ** 3 + complexity
        scores.append((function.fullname, complexity, coverage, crap))
    return scores
