"""Paired stationary bootstrap for the mean daily net-return difference.

Politis & Romano (1994), JASA 89, 1303–1313. Assumes stationary, weakly
 dependent paired returns; neither daily aggregation nor this test proves that.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from algo_analyze.deflated import InferenceUnavailable

DEFAULT_ALPHA = 0.05


@dataclass(frozen=True)
class BlockResult:
    """Auditable two-sided inference on the challenger-minus-baseline daily mean."""

    effect: float
    confidence_interval: tuple[float, float]
    p_value: float
    reject_null: bool
    block_length: int
    n_resamples: int
    seed: int
    n_observations: int
    expected_blocks: float
    alpha: float
    method: str = "paired_stationary_bootstrap"
    estimand: str = "mean daily net return: challenger minus baseline"
    null: str = "mean difference equals zero"
    sidedness: str = "two-sided"
    assumptions: str = "stationary weak dependence; finite moments; prespecified block length"


def _integer(name: str, value: int, minimum: int) -> None:
    """Reject booleans, nonintegers, and values below a setting's minimum."""
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")


def stationary_indices(
    n: int,
    block_length: int,
    n_resamples: int,
    seed: int,
) -> NDArray[np.int64]:
    """Draw circular, geometrically sized ordered blocks; use the same indices for both arms."""
    _integer("n", n, 2)
    _integer("block_length", block_length, 1)
    _integer("n_resamples", n_resamples, 100)
    _integer("seed", seed, 0)
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, n, size=(n_resamples, n), dtype=np.int64)
    restart = rng.random((n_resamples, n)) < 1 / block_length
    restart[:, 0] = True
    columns = np.arange(n, dtype=np.int64)
    last = np.maximum.accumulate(np.where(restart, columns, 0), axis=1)
    return (np.take_along_axis(starts, last, axis=1) + columns - last) % n


def paired_block_test(
    returns_a: Sequence[float],
    returns_b: Sequence[float],
    *,
    block_length: int,
    n_resamples: int,
    seed: int,
    alpha: float = DEFAULT_ALPHA,
) -> BlockResult:
    """Bootstrap null-centered paired differences; invert the same absolute-error distribution."""
    validate_block_settings(block_length, n_resamples, seed, alpha)
    difference, effect = _paired_difference(returns_a, returns_b, block_length)
    n = len(difference)
    indices = stationary_indices(n, block_length, n_resamples, seed)
    scale = float(np.max(np.abs(difference)))
    errors = np.abs(((difference / scale) - effect / scale)[indices].mean(axis=1)) * scale
    p_value = (int(np.count_nonzero(errors >= abs(effect))) + 1) / (n_resamples + 1)
    # Compare the same floating-point probabilities as the p-value decision.
    # Multiplying alpha by B+1 can round upward at exact boundaries (e.g. .07).
    p_grid = np.arange(1, n_resamples + 2) / (n_resamples + 1)
    rank = n_resamples - int(np.count_nonzero(p_grid < alpha))
    radius = float(np.sort(errors)[rank])
    if not math.isfinite(abs(effect) + radius):
        raise ValueError("confidence interval endpoints must be finite")
    return BlockResult(
        effect,
        (effect - radius, effect + radius),
        p_value,
        p_value < alpha,
        block_length,
        n_resamples,
        seed,
        n,
        n / block_length,
        alpha,
    )


def validate_block_settings(
    block_length: int, n_resamples: int, seed: int, alpha: float = DEFAULT_ALPHA,
) -> None:
    """Reject invalid prespecified settings even when portfolio evidence is unavailable."""
    _integer("block_length", block_length, 1)
    _integer("n_resamples", n_resamples, 100)
    _integer("seed", seed, 0)
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between zero and one")
    if alpha <= 1 / (n_resamples + 1):
        raise ValueError("resample count cannot resolve the requested alpha")


def _paired_difference(
    returns_a: Sequence[float], returns_b: Sequence[float], block_length: int,
) -> tuple[NDArray[np.float64], float]:
    """Validate paired history and uncertainty using scale-invariant variance."""
    a, b = np.asarray(returns_a, dtype=float), np.asarray(returns_b, dtype=float)
    if a.ndim != 1 or b.shape != a.shape or not np.isfinite([a, b]).all():
        raise ValueError("paired returns must have equal lengths and finite one-dimensional values")
    n = len(a)
    if n < 30 or n / block_length < 10:
        raise InferenceUnavailable("need >=30 observations and >=10 expected blocks")
    return _difference_uncertainty(a, b)


def _difference_uncertainty(
    a: NDArray[np.float64], b: NDArray[np.float64],
) -> tuple[NDArray[np.float64], float]:
    """Reject nonrepresentable or degenerate differences before resampling."""
    with np.errstate(over="ignore", invalid="ignore"):
        difference = b - a
        effect = float(difference.mean())
    if not np.isfinite(difference).all() or not math.isfinite(effect):
        raise ValueError("paired differences and their mean must be finite")
    scale = float(np.max(np.abs(difference)))
    scaled = difference / scale if scale else difference
    if float(scaled.var()) <= np.finfo(float).eps * float(np.mean(scaled**2)):
        raise InferenceUnavailable("degenerate paired difference; cannot estimate uncertainty")
    return difference, effect
