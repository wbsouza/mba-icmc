"""Monte-Carlo permutation significance tests for strategy return samples."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

MIN_PERMUTATIONS = 100
DEFAULT_ALPHA = 0.05


@dataclass(frozen=True)
class MCPResult:
    """Result of a two-sample Monte-Carlo permutation test."""

    p_value: float
    reject_null: bool
    observed_difference: float
    n_permutations: int


def mcp_test(
    returns_a: Iterable[float],
    returns_b: Iterable[float],
    *,
    n_permutations: int,
    seed: int,
) -> MCPResult:
    """Test whether two return samples differ under random relabeling.

    The statistic is the absolute difference in sample means. The p-value uses
    the standard plus-one correction: ``(extreme + 1) / (n_permutations + 1)``.

    Raises:
        ValueError: if either return sample is too small, contains non-finite
            values, or if the permutation count/seed is invalid.
    """
    sample_a = _validated_returns("returns_a", returns_a)
    sample_b = _validated_returns("returns_b", returns_b)
    _validate_permutation_count(n_permutations)
    _validate_seed(seed)

    observed = abs(_mean(sample_a) - _mean(sample_b))
    combined = [*sample_a, *sample_b]
    size_a = len(sample_a)
    rng = random.Random(seed)
    extreme = 0

    for _ in range(n_permutations):
        shuffled = combined[:]
        rng.shuffle(shuffled)
        diff = abs(_mean(shuffled[:size_a]) - _mean(shuffled[size_a:]))
        if diff >= observed:
            extreme += 1

    p_value = (extreme + 1) / (n_permutations + 1)
    return MCPResult(
        p_value=p_value,
        reject_null=p_value < DEFAULT_ALPHA,
        observed_difference=observed,
        n_permutations=n_permutations,
    )


def _validated_returns(name: str, values: Iterable[float]) -> tuple[float, ...]:
    """Return a finite float tuple for one strategy, failing fast by input name."""
    if isinstance(values, str | bytes):
        raise ValueError(f"{name} must be an iterable of numeric returns, not text")
    try:
        sample = tuple(float(value) for value in values)
    except TypeError as exc:
        raise ValueError(f"{name} must be an iterable of numeric returns") from exc
    except ValueError as exc:
        raise ValueError(f"{name} must contain only numeric returns") from exc

    if len(sample) < 2:
        raise ValueError(f"{name} must contain at least two returns")
    if not all(math.isfinite(value) for value in sample):
        raise ValueError(f"{name} must contain only finite returns")
    return sample


def _validate_permutation_count(n_permutations: int) -> None:
    """Validate the permutation count before any sampling occurs."""
    if isinstance(n_permutations, bool) or not isinstance(n_permutations, int):
        raise ValueError("n_permutations must be an integer")
    if n_permutations < MIN_PERMUTATIONS:
        raise ValueError(f"n_permutations must be at least {MIN_PERMUTATIONS}")


def _validate_seed(seed: int) -> None:
    """Validate the deterministic random seed."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")


def _mean(values: Sequence[float]) -> float:
    """Return the arithmetic mean of a non-empty numeric sequence."""
    return sum(values) / len(values)
