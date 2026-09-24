"""Steps for significance.feature."""

from __future__ import annotations

from typing import Any

import pytest
from algo_analyze.significance import MCPResult, mcp_test
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/significance.feature")


@pytest.fixture
def sctx() -> dict[str, Any]:
    """Return per-scenario mutable context for MCP examples."""
    return {}


@given(parsers.parse("baseline returns {values}"))
def _baseline_returns(sctx: dict[str, Any], values: str) -> None:
    """Store the baseline return sample from a comma-separated scenario value."""
    sctx["returns_a"] = _parse_returns(values)


@given(parsers.parse("comparison returns {values}"))
def _comparison_returns(sctx: dict[str, Any], values: str) -> None:
    """Store the comparison return sample from a comma-separated scenario value."""
    sctx["returns_b"] = _parse_returns(values)


@given(parsers.parse("{count:d} permutations with seed {seed:d}"))
def _permutation_settings(sctx: dict[str, Any], count: int, seed: int) -> None:
    """Store deterministic permutation settings for the scenario."""
    sctx["n_permutations"] = count
    sctx["seed"] = seed


@when("the permutation test is computed")
def _compute(sctx: dict[str, Any]) -> None:
    """Compute the MCP test once, storing either the result or ValueError."""
    try:
        sctx["result"] = _call_mcp_test(sctx)
    except ValueError as exc:
        sctx["error"] = exc


@when("the permutation test is computed twice")
def _compute_twice(sctx: dict[str, Any]) -> None:
    """Compute the MCP test twice with identical seeded inputs."""
    sctx["first"] = _call_mcp_test(sctx)
    sctx["second"] = _call_mcp_test(sctx)


def _call_mcp_test(sctx: dict[str, Any]) -> MCPResult:
    """Call the public MCP entry point from scenario context."""
    return mcp_test(
        sctx["returns_a"],
        sctx["returns_b"],
        n_permutations=sctx["n_permutations"],
        seed=sctx["seed"],
    )


def _parse_returns(values: str) -> list[float]:
    """Parse comma-separated decimal returns from a feature step."""
    return [float(value.strip()) for value in values.split(",")]


@then("both p-values are byte-identical")
def _same_p_value(sctx: dict[str, Any]) -> None:
    """Assert seeded runs produce exactly the same p-value bits."""
    assert sctx["first"].p_value.hex() == sctx["second"].p_value.hex()


@then("both reject-null decisions are identical")
def _same_reject_decision(sctx: dict[str, Any]) -> None:
    """Assert seeded runs produce exactly the same boolean decision."""
    assert sctx["first"].reject_null == sctx["second"].reject_null


@then(parsers.parse("the p-value is below {threshold:g}"))
def _p_value_below(sctx: dict[str, Any], threshold: float) -> None:
    """Assert the computed p-value is below a scenario threshold."""
    assert "error" not in sctx
    assert sctx["result"].p_value < threshold


@then("the null hypothesis is rejected")
def _rejects_null(sctx: dict[str, Any]) -> None:
    """Assert the MCP result rejects equal return distributions."""
    assert sctx["result"].reject_null is True


@then(parsers.parse("the p-value equals {expected:g} exactly"))
def _p_value_equals(sctx: dict[str, Any], expected: float) -> None:
    """Assert the computed p-value exactly matches the expected value."""
    assert "error" not in sctx
    assert sctx["result"].p_value == expected


@then("the null hypothesis is not rejected")
def _does_not_reject_null(sctx: dict[str, Any]) -> None:
    """Assert the MCP result preserves the null hypothesis."""
    assert sctx["result"].reject_null is False


@then(parsers.parse('it raises an error containing "{text}"'))
def _raises_error_containing(sctx: dict[str, Any], text: str) -> None:
    """Assert the stored error contains the required fail-fast detail."""
    error = sctx.get("error")
    assert isinstance(error, ValueError)
    assert text in str(error)
