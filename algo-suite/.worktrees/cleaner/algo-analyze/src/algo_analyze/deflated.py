"""Deflated Sharpe ratio statistics."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

_EULER_MASCHERONI = 0.5772156649015329


@dataclass(frozen=True)
class _DeflatedSharpeInputs:
    """Validated closed-form inputs for the deflated Sharpe statistic."""

    observed_sharpe: float
    n_returns: int
    skew: float
    kurtosis: float
    n_trials: int


def deflated_sharpe(
    *,
    observed_sharpe: float | None = None,
    n_returns: int | None = None,
    skew: float = 0.0,
    kurtosis: float = 3.0,
    n_trials: int = 1,
    returns: Sequence[float] | None = None,
) -> float:
    """Return the Bailey-Lopez de Prado deflated Sharpe ratio.

    Args:
        observed_sharpe: Naive Sharpe ratio observed after strategy search.
        n_returns: Number of trade returns used to estimate the observed Sharpe.
        skew: Return distribution skewness.
        kurtosis: Return distribution kurtosis.
        n_trials: Number of independent strategy trials considered.
        returns: Optional raw trade returns. When provided, they are validated for
            zero variance and can supply `observed_sharpe`/`n_returns`.

    Raises:
        ValueError: inputs are non-finite, underspecified, or imply an invalid
            Sharpe standard error.
    """
    inferred_sharpe, inferred_count = _infer_sharpe_from_returns(returns)
    sharpe = inferred_sharpe if observed_sharpe is None else observed_sharpe
    count = inferred_count if n_returns is None else n_returns
    inputs = _validated_inputs(sharpe, count, skew, kurtosis, n_trials)
    if inputs.n_trials == 1:
        return inputs.observed_sharpe
    return inputs.observed_sharpe - _sharpe_standard_error(
        inputs.observed_sharpe, inputs.n_returns, inputs.skew, inputs.kurtosis
    ) * _expected_max_z(inputs.n_trials)


def _infer_sharpe_from_returns(returns: Sequence[float] | None) -> tuple[float | None, int | None]:
    """Validate optional raw returns and infer Sharpe/count when present."""
    if returns is None:
        return None, None
    values = [float(value) for value in returns]
    if len(values) < 2:
        raise ValueError(
            "returns must contain at least two observations; provide more trade returns"
        )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("returns must be finite; remove NaN or infinite trade returns")
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    if variance == 0.0:
        raise ValueError(
            "returns have zero variance; provide varying trade returns or pass a "
            "precomputed observed_sharpe with n_returns"
        )
    return mean / math.sqrt(variance), len(values)


def _validated_inputs(
    observed_sharpe: float | None,
    n_returns: int | None,
    skew: float,
    kurtosis: float,
    n_trials: int,
) -> _DeflatedSharpeInputs:
    """Return validated closed-form inputs or fail fast when undefined."""
    if observed_sharpe is None:
        raise ValueError("observed_sharpe is required when returns are not provided")
    if n_returns is None:
        raise ValueError("n_returns is required when returns are not provided")
    if n_returns < 2:
        raise ValueError("n_returns must be at least 2 to estimate Sharpe uncertainty")
    if n_trials < 1:
        raise ValueError("n_trials must be at least 1")
    values = {
        "observed_sharpe": observed_sharpe,
        "skew": skew,
        "kurtosis": kurtosis,
    }
    for name, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite; got {value!r}")
    if _variance_term(observed_sharpe, skew, kurtosis) <= 0.0:
        raise ValueError(
            "observed_sharpe, skew, and kurtosis imply non-positive Sharpe variance; "
            "check the input moments"
        )
    return _DeflatedSharpeInputs(
        observed_sharpe=observed_sharpe,
        n_returns=n_returns,
        skew=skew,
        kurtosis=kurtosis,
        n_trials=n_trials,
    )


def _sharpe_standard_error(
    observed_sharpe: float, n_returns: int, skew: float, kurtosis: float
) -> float:
    """Return the standard error of the observed Sharpe estimate."""
    return math.sqrt(_variance_term(observed_sharpe, skew, kurtosis) / (n_returns - 1))


def _variance_term(observed_sharpe: float, skew: float, kurtosis: float) -> float:
    """Return the numerator of the Sharpe standard-error expression."""
    return 1.0 - skew * observed_sharpe + ((kurtosis - 1.0) / 4.0) * observed_sharpe**2


def _expected_max_z(n_trials: int) -> float:
    """Approximate the expected maximum of N independent standard-normal trials."""
    if n_trials == 1:
        return 0.0
    normal = NormalDist()
    return (1.0 - _EULER_MASCHERONI) * normal.inv_cdf(
        1.0 - 1.0 / n_trials
    ) + _EULER_MASCHERONI * normal.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
