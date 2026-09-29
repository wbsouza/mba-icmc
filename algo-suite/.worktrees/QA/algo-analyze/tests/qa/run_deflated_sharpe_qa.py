"""Executable QA procedure for the deflated Sharpe ratio function.

The companion procedure is ``spec-algo-analyze-deflated-sharpe.qa.md``. This
lane has no CLI yet, so the public ``deflated_sharpe`` function is the tested
interface as documented by the procedure.
"""

from __future__ import annotations

import math

from algo_analyze.deflated import deflated_sharpe


class QaFailure(AssertionError):
    """Raised when an executable QA check fails."""


def main() -> None:
    """Run the complete automated QA procedure."""
    _many_trials_golden_value()
    _single_trial_noop()
    _zero_variance_fails_fast()
    _deterministic()
    _invalid_closed_form_inputs_fail_fast()
    _raw_returns_infer_sharpe_and_count()
    _malformed_raw_returns_fail_fast()
    _defaults_match_the_documented_contract()
    _boundary_inputs_match_the_formula()


def _many_trials_golden_value() -> None:
    """Verify the documented many-trial golden value."""
    value = deflated_sharpe(
        observed_sharpe=0.5,
        n_returns=100,
        skew=0.0,
        kurtosis=3.0,
        n_trials=50,
    )
    _expect_close(value, 0.2573452749201449, "many-trial golden value")
    _expect(value < 0.5, "deflated value is lower than observed Sharpe")


def _single_trial_noop() -> None:
    """Verify a single trial returns the observed Sharpe exactly."""
    value = deflated_sharpe(
        observed_sharpe=0.5,
        n_returns=100,
        skew=0.0,
        kurtosis=3.0,
        n_trials=1,
    )
    _expect(value == 0.5, "single trial is an exact no-op")


def _zero_variance_fails_fast() -> None:
    """Verify zero-variance raw returns raise a useful error."""
    try:
        deflated_sharpe(returns=[0.01, 0.01], n_trials=50)
    except ValueError as exc:
        message = str(exc)
        _expect("zero variance" in message, "zero-variance error names the input")
        return
    raise QaFailure("zero-variance returns did not raise")


def _deterministic() -> None:
    """Verify the closed-form computation is deterministic."""
    first = deflated_sharpe(
        observed_sharpe=0.5,
        n_returns=100,
        skew=0.0,
        kurtosis=3.0,
        n_trials=50,
    )
    second = deflated_sharpe(
        observed_sharpe=0.5,
        n_returns=100,
        skew=0.0,
        kurtosis=3.0,
        n_trials=50,
    )
    _expect(first.hex() == second.hex(), "deflated Sharpe is byte-identical")


def _invalid_closed_form_inputs_fail_fast() -> None:
    """Verify invalid closed-form inputs fail fast with useful messages."""
    cases = [
        (
            _closed_form_kwargs(None, 100, 0.0, 3.0, 50),
            "observed_sharpe",
        ),
        (
            _closed_form_kwargs(0.5, None, 0.0, 3.0, 50),
            "n_returns",
        ),
        (
            _closed_form_kwargs(0.5, 1, 0.0, 3.0, 50),
            "at least 2",
        ),
        (
            _closed_form_kwargs(0.5, 100, 0.0, 3.0, 0),
            "n_trials",
        ),
        (
            _closed_form_kwargs(0.5, 100, math.nan, 3.0, 50),
            "skew",
        ),
        (
            _closed_form_kwargs(math.nan, 100, 0.0, 3.0, 50),
            "observed_sharpe",
        ),
        (
            _closed_form_kwargs(0.5, 100, 0.0, math.nan, 50),
            "kurtosis",
        ),
        (
            _closed_form_kwargs(3.0, 100, 10.0, 1.0, 50),
            "non-positive Sharpe",
        ),
        (
            _closed_form_kwargs(1.0, 100, 1.0, 1.0, 50),
            "non-positive Sharpe",
        ),
    ]
    for kwargs, expected in cases:
        _expect_raises(expected, **kwargs)


def _raw_returns_infer_sharpe_and_count() -> None:
    """Verify raw returns can provide the observed Sharpe and sample count."""
    value = deflated_sharpe(returns=[0.02, -0.01, 0.03, 0.01, -0.02], n_trials=1)
    _expect_close(value, 0.28934569330224724, "raw-return inferred Sharpe")


def _malformed_raw_returns_fail_fast() -> None:
    """Verify malformed raw return inputs fail fast."""
    cases = [([0.01], "at least two"), ([0.01, math.nan], "finite")]
    for returns, expected in cases:
        try:
            deflated_sharpe(returns=returns)
        except ValueError as exc:
            _expect(expected in str(exc), f"raw returns error contains {expected!r}")
            continue
        raise QaFailure(f"raw returns {returns!r} did not raise")


def _defaults_match_the_documented_contract() -> None:
    """Verify omitted optional inputs use their documented defaults."""
    raw_default_trials = deflated_sharpe(returns=[0.02, -0.01, 0.03, 0.01, -0.02])
    _expect_close(raw_default_trials, 0.28934569330224724, "default trial count")

    normal_moments = deflated_sharpe(observed_sharpe=0.5, n_returns=100, n_trials=50)
    _expect_close(normal_moments, 0.2573452749201449, "default skew and kurtosis")


def _boundary_inputs_match_the_formula() -> None:
    """Verify boundary and non-zero-skew examples from the accepted feature."""
    cases = [
        (0.5, 2, 0.0, 3.0, 50, -1.9143840300901647),
        (0.3, 100, 0.0, 1.0, 50, 0.07122293121210274),
        (0.5, 100, 0.2, 3.0, 50, 0.2683808710765412),
    ]
    for sharpe, count, skew, kurtosis, trials, expected in cases:
        value = deflated_sharpe(
            observed_sharpe=sharpe,
            n_returns=count,
            skew=skew,
            kurtosis=kurtosis,
            n_trials=trials,
        )
        _expect_close(value, expected, f"boundary input {sharpe}, {count}, {skew}")


def _expect_raises(expected: str, **kwargs: float | int | None) -> None:
    """Assert that ``deflated_sharpe`` raises a message containing ``expected``."""
    try:
        deflated_sharpe(**kwargs)
    except ValueError as exc:
        _expect(expected in str(exc), f"error contains {expected!r}")
        return
    raise QaFailure(f"{kwargs!r} did not raise")


def _closed_form_kwargs(
    observed_sharpe: float | None,
    n_returns: int | None,
    skew: float,
    kurtosis: float,
    n_trials: int,
) -> dict[str, float | int | None]:
    """Build keyword arguments for closed-form validation cases."""
    return {
        "observed_sharpe": observed_sharpe,
        "n_returns": n_returns,
        "skew": skew,
        "kurtosis": kurtosis,
        "n_trials": n_trials,
    }


def _expect_close(actual: float, expected: float, message: str) -> None:
    """Raise when two finite floats differ beyond the procedure tolerance."""
    _expect(math.isfinite(actual), f"{message}: actual value is finite")
    if abs(actual - expected) > 1e-9:
        raise QaFailure(f"{message}: expected {expected}, got {actual}")


def _expect(condition: bool, message: str) -> None:
    """Raise a readable QA failure when a condition is false."""
    if not condition:
        raise QaFailure(message)


if __name__ == "__main__":
    main()
