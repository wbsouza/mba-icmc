"""Steps for deflated_sharpe.feature."""

from __future__ import annotations

import math
from typing import Any

import pytest
from algo_analyze.deflated import deflated_sharpe
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/deflated_sharpe.feature")


@pytest.fixture
def dctx() -> dict[str, Any]:
    """Per-scenario mutable context."""
    return {}


@given(
    parsers.re(
        r"an observed Sharpe of (?P<sharpe>-?\d+(?:\.\d+)?) from "
        r"(?P<count>\d+) trade returns with skew (?P<skew>-?\d+(?:\.\d+)?) "
        r"and kurtosis (?P<kurtosis>-?\d+(?:\.\d+)?)"
    )
)
def _observed_sharpe(
    dctx: dict[str, Any], sharpe: str, count: str, skew: str, kurtosis: str
) -> None:
    dctx["observed_sharpe"] = float(sharpe)
    dctx["n_returns"] = int(count)
    dctx["skew"] = float(skew)
    dctx["kurtosis"] = float(kurtosis)


@given(parsers.parse("{count:d} independent trial"))
@given(parsers.parse("{count:d} independent trials"))
def _independent_trials(dctx: dict[str, Any], count: int) -> None:
    dctx["n_trials"] = count


@given("trade returns with zero variance")
def _zero_variance_returns(dctx: dict[str, Any]) -> None:
    dctx["returns"] = [0.01, 0.01, 0.01]
    dctx["n_trials"] = 50


@given(parsers.parse("raw trade returns {values}"))
def _raw_returns(dctx: dict[str, Any], values: str) -> None:
    dctx["returns"] = [_nan_or_float(value.strip()) for value in values.split(",")]


@given(parsers.parse("an observed Sharpe of {sharpe:g} from {count:d} trade returns"))
def _observed_sharpe_no_moments(dctx: dict[str, Any], sharpe: float, count: int) -> None:
    dctx["observed_sharpe"] = sharpe
    dctx["n_returns"] = count


def _nan_or_float(value: str) -> float:
    """Parse a scenario return value, allowing ``nan`` for the malformed-input case."""
    return math.nan if value == "nan" else float(value)


@given(parsers.parse("deflated Sharpe inputs {sharpe}, {count}, {skew}, {kurtosis}, and {trials}"))
def _deflated_inputs(
    dctx: dict[str, Any], sharpe: str, count: str, skew: str, kurtosis: str, trials: str
) -> None:
    dctx["observed_sharpe"] = _optional_float(sharpe)
    dctx["n_returns"] = _optional_int(count)
    dctx["skew"] = float(skew)
    dctx["kurtosis"] = float(kurtosis)
    dctx["n_trials"] = int(trials)


@when("the deflated Sharpe ratio is computed")
def _compute(dctx: dict[str, Any]) -> None:
    """Compute the deflated Sharpe once and store either the result or error."""
    try:
        dctx["result"] = _call_deflated_sharpe(dctx)
    except ValueError as exc:
        dctx["error"] = exc


@when("the deflated Sharpe ratio is computed without specifying n_trials")
def _compute_default_trials(dctx: dict[str, Any]) -> None:
    """Call the public entry point without n_trials, exercising its real default."""
    try:
        dctx["result"] = deflated_sharpe(
            observed_sharpe=dctx.get("observed_sharpe"),
            n_returns=dctx.get("n_returns"),
            skew=dctx.get("skew", 0.0),
            kurtosis=dctx.get("kurtosis", 3.0),
            returns=dctx.get("returns"),
        )
    except ValueError as exc:
        dctx["error"] = exc


@when("the deflated Sharpe ratio is computed without specifying skew or kurtosis")
def _compute_default_moments(dctx: dict[str, Any]) -> None:
    """Call the public entry point without skew/kurtosis, exercising their real defaults."""
    try:
        dctx["result"] = deflated_sharpe(
            observed_sharpe=dctx.get("observed_sharpe"),
            n_returns=dctx.get("n_returns"),
            n_trials=dctx.get("n_trials", 1),
            returns=dctx.get("returns"),
        )
    except ValueError as exc:
        dctx["error"] = exc


@when("the deflated Sharpe ratio is computed twice")
def _compute_twice(dctx: dict[str, Any]) -> None:
    dctx["first"] = _call_deflated_sharpe(dctx)
    dctx["second"] = _call_deflated_sharpe(dctx)


def _call_deflated_sharpe(dctx: dict[str, Any]) -> float:
    """Call the public deflated Sharpe entry point from scenario context."""
    return deflated_sharpe(
        observed_sharpe=dctx.get("observed_sharpe"),
        n_returns=dctx.get("n_returns"),
        skew=dctx.get("skew", 0.0),
        kurtosis=dctx.get("kurtosis", 3.0),
        n_trials=dctx.get("n_trials", 1),
        returns=dctx.get("returns"),
    )


def _optional_float(value: str) -> float | None:
    """Parse a float value, allowing ``none`` for omitted scenario inputs."""
    return None if value == "none" else float(value)


def _optional_int(value: str) -> int | None:
    """Parse an integer value, allowing ``none`` for omitted scenario inputs."""
    return None if value == "none" else int(value)


@then(
    parsers.re(
        r"it equals (?P<expected>-?\d+(?:\.\d+)?(?:e-?\d+)?) within "
        r"tolerance (?P<tolerance>\d+(?:\.\d+)?(?:e-?\d+)?)"
    )
)
def _equals_within_tolerance(dctx: dict[str, Any], expected: str, tolerance: str) -> None:
    assert "error" not in dctx
    assert math.isclose(dctx["result"], float(expected), abs_tol=float(tolerance))


@then(parsers.re(r"it is lower than the observed Sharpe of (?P<observed>-?\d+(?:\.\d+)?)"))
def _lower_than_observed(dctx: dict[str, Any], observed: str) -> None:
    assert dctx["result"] < float(observed)


@then(parsers.re(r"it equals the observed Sharpe of (?P<observed>-?\d+(?:\.\d+)?) exactly"))
def _equals_observed_exactly(dctx: dict[str, Any], observed: str) -> None:
    assert "error" not in dctx
    assert dctx["result"] == float(observed)


@then("it raises an error naming the zero-variance input")
def _raises_zero_variance(dctx: dict[str, Any]) -> None:
    error = dctx.get("error")
    assert isinstance(error, ValueError)
    message = str(error)
    assert "returns" in message
    assert "zero variance" in message


@then(parsers.parse('it raises an error containing "{text}"'))
def _raises_error_containing(dctx: dict[str, Any], text: str) -> None:
    error = dctx.get("error")
    assert isinstance(error, ValueError)
    assert text in str(error)


@then("no NaN or infinite value is returned")
def _no_nan_or_infinite(dctx: dict[str, Any]) -> None:
    assert "result" not in dctx


@then("both deflated Sharpe values are byte-identical")
def _byte_identical(dctx: dict[str, Any]) -> None:
    assert dctx["first"].hex() == dctx["second"].hex()
