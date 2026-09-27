"""Bailey–López de Prado (2014), Eq. 2; nonannualized Sharpe, Pearson kurtosis."""

from __future__ import annotations

import math
from collections.abc import Sequence
from statistics import NormalDist, mean, stdev


class InferenceUnavailable(ValueError):
    """Valid artifacts cannot support the requested inference."""


def return_moments(returns: Sequence[float]) -> dict[str, float | int]:
    """Estimate sample Sharpe (ddof=1), and uncorrected standardized central moments."""
    if len(returns) < 4 or not all(math.isfinite(x) for x in returns):
        raise ValueError("moments require at least four finite daily returns")
    centered, average, scale = _scaled_center(returns)
    variance = mean([x**2 for x in centered])
    sharpe = (average / scale) / stdev(centered)
    return {
        "observed_sharpe": sharpe,
        "n_returns": len(returns),
        "skew": mean([x**3 for x in centered]) / variance**1.5,
        "kurtosis": mean([x**4 for x in centered]) / variance**2,
    }


def _scaled_center(returns: Sequence[float]) -> tuple[list[float], float, float]:
    """Normalize centered returns before powers to avoid finite-input overflow/underflow."""
    average = mean(returns)
    scale = max(abs(x - average) for x in returns)
    if not math.isfinite(scale):
        raise ValueError("return centering overflow; use finite representable returns")
    if scale == 0:
        raise InferenceUnavailable("zero return variance; Sharpe and moments undefined")
    centered = [(x - average) / scale for x in returns]
    return centered, average, scale


def selection_threshold(n_trials: int, trial_sharpe_std: float | None) -> float:
    """Expected maximum using across-trial Sharpe SD and registered effective trial count."""
    if type(n_trials) is not int or n_trials < 1:
        raise ValueError("n_trials must be a positive integer")
    _validate_dispersion(trial_sharpe_std)
    if n_trials == 1:
        return 0.0
    if trial_sharpe_std is None:
        raise InferenceUnavailable("multi-trial DSR requires across-trial Sharpe dispersion")
    normal = NormalDist()
    gamma = 0.5772156649015329
    threshold = trial_sharpe_std * (
        (1 - gamma) * normal.inv_cdf(1 - 1 / n_trials)
        + gamma * normal.inv_cdf(1 - 1 / (n_trials * math.e))
    )
    if not math.isfinite(threshold):
        raise ValueError("selection threshold must be finite")
    return threshold


def _validate_dispersion(trial_sharpe_std: float | None) -> None:
    """Reject malformed or negative trial dispersion before special-casing one trial."""
    if trial_sharpe_std is not None and (
        isinstance(trial_sharpe_std, bool)
        or not isinstance(trial_sharpe_std, int | float)
        or not math.isfinite(trial_sharpe_std)
        or trial_sharpe_std < 0
    ):
        raise ValueError("trial_sharpe_std must be finite and nonnegative")


def deflated_sharpe(
    *,
    observed_sharpe: float,
    n_returns: int,
    skew: float,
    kurtosis: float,
    n_trials: int,
    trial_sharpe_std: float | None,
    provenance: str,
) -> float:
    """Compute classical DSR probability; serial-dependence validity is not established."""
    if not provenance.strip():
        raise InferenceUnavailable("selection history provenance is required")
    if type(n_returns) is not int or n_returns < 4:
        raise ValueError("n_returns must be an integer of at least four")
    if not all(math.isfinite(x) for x in (observed_sharpe, skew, kurtosis)):
        raise ValueError("Sharpe and moments must be finite")
    if kurtosis < 1 + skew * skew - 1e-12:
        raise ValueError("Pearson kurtosis must be at least 1 + skew squared")
    threshold = selection_threshold(n_trials, trial_sharpe_std)
    variance = _sampling_variance(observed_sharpe, skew, kurtosis)
    z = (observed_sharpe - threshold) * math.sqrt((n_returns - 1) / variance)
    return NormalDist().cdf(z)


def _sampling_variance(observed_sharpe: float, skew: float, kurtosis: float) -> float:
    """Reject nonrepresentable sampling variances rather than emit a false probability."""
    try:
        variance = 1 - skew * observed_sharpe + (kurtosis - 1) * observed_sharpe**2 / 4
    except OverflowError as exc:
        raise ValueError("DSR sampling variance overflow") from exc
    if not math.isfinite(variance) or variance <= 0:
        raise ValueError("DSR sampling variance must be finite and positive")
    return variance
