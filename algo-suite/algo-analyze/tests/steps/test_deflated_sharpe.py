"""Independent Eq2 reference scenarios (100 observations, skew0, Pearson kurtosis3)."""

from typing import Any

import pytest
from algo_analyze.deflated import deflated_sharpe
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/deflated_sharpe.feature")


@pytest.fixture
def dctx() -> dict[str, Any]:
    """Isolate each equation fixture."""
    return {}


@given(parsers.parse("DSR inputs SR {sr:g} trials {trials:d} dispersion {dispersion:g}"))
def inputs(dctx: dict[str, Any], sr: float, trials: int, dispersion: float) -> None:
    """Use explicitly supplied moments with a frozen reference provenance."""
    dctx["inputs"] = dict(
        observed_sharpe=sr,
        n_returns=100,
        skew=0.0,
        kurtosis=3.0,
        n_trials=trials,
        trial_sharpe_std=dispersion,
        provenance="independent scipy Eq2 reference, supplied normal moments",
    )


@given("DSR has missing dispersion")
def missing(dctx: dict[str, Any]) -> None:
    """Represent unavailable search dispersion."""
    dctx["inputs"]["trial_sharpe_std"] = None


@given(parsers.parse("invalid DSR {field} value {value}"))
def invalid(dctx: dict[str, Any], field: str, value: str) -> None:
    """Replace one field with a malformed scientific input."""
    dctx["inputs"][field] = int(value) if field in ("n_returns", "n_trials") else float(value)


@when("classical DSR is computed")
def compute(dctx: dict[str, Any]) -> None:
    """Run the public equation with no silent distribution defaults."""
    try:
        dctx["result"] = deflated_sharpe(**dctx["inputs"])
    except ValueError as exc:
        dctx["error"] = str(exc)


@then(parsers.parse("DSR matches the independent probability {expected:g}"))
def reference(dctx: dict[str, Any], expected: float) -> None:
    """Compare to frozen separately calculated CDF with double precision tolerance."""
    assert dctx["result"] == pytest.approx(expected, abs=1e-12, rel=0)
    assert 0 <= dctx["result"] <= 1


@then("one hundred trials has lower probability")
def monotonic(dctx: dict[str, Any]) -> None:
    """Selection over more independent trials raises the threshold."""
    assert deflated_sharpe(**{**dctx["inputs"], "n_trials": 100}) < dctx["result"]


@then(parsers.parse('DSR fails mentioning "{reason}"'))
def error(dctx: dict[str, Any], reason: str) -> None:
    """Require an actionable diagnostic."""
    assert reason in dctx["error"]
