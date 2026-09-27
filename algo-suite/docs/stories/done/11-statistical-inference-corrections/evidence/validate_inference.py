"""Reproduce the prospectively registered Story 11 finite simulation and DSR fixtures.

Run from algo-suite: uv run --with mpmath python docs/stories/<state>/
11-statistical-inference-corrections/evidence/validate_inference.py
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
from pathlib import Path

import numpy as np
from algo_analyze.deflated import deflated_sharpe
from algo_analyze.significance import paired_block_test
from numpy.typing import NDArray

SEED = 20260927
REPLICATIONS = 300
OBSERVATIONS = 1200
BURN_IN = 300
RESAMPLES = 499
BLOCK_LENGTHS = (1, 10, 20, 40)
NULL_BOUND = 0.05 + 3 * math.sqrt(0.05 * 0.95 / REPLICATIONS)


def wilson(successes: int, count: int) -> list[float]:
    """Compute a two-sided Wilson 95 percent binomial interval independently."""
    z = 1.959963984540054
    p = successes / count
    divisor = 1 + z * z / count
    center = (p + z * z / (2 * count)) / divisor
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count**2)) / divisor
    return [center - radius, center + radius]


def paired_sample(
    rng: np.random.Generator, phi: float, effect: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Generate the registered stationary AR(1) difference and shared baseline."""
    n = OBSERVATIONS + BURN_IN
    innovations = rng.normal(0, 0.01 * math.sqrt(1 - phi**2), n)
    differences = np.empty(n)
    differences[0] = rng.normal(0, 0.01)
    for index in range(1, n):
        differences[index] = phi * differences[index - 1] + innovations[index]
    baseline = rng.normal(0, 0.01, OBSERVATIONS)
    return baseline, baseline + differences[BURN_IN:] + effect


def scenario(phi: float, effect: float, scenario_index: int) -> list[dict[str, object]]:
    """Evaluate all sensitivity settings with identical samples and bootstrap seeds."""
    rejections = dict.fromkeys(BLOCK_LENGTHS, 0)
    disagreements = dict.fromkeys(BLOCK_LENGTHS, 0)
    seeds = np.random.SeedSequence([SEED, scenario_index]).spawn(REPLICATIONS)
    for seed in seeds:
        rng = np.random.default_rng(seed)
        a, b = paired_sample(rng, phi, effect)
        bootstrap_seed = int(rng.integers(0, 2**32))
        for length in BLOCK_LENGTHS:
            result = paired_block_test(
                a.tolist(), b.tolist(), block_length=length,
                n_resamples=RESAMPLES, seed=bootstrap_seed,
            )
            rejections[length] += result.reject_null
            lower, upper = result.confidence_interval
            disagreements[length] += result.reject_null != (lower > 0 or upper < 0)
    return [summarize(phi, effect, length, rejections[length], disagreements[length])
            for length in BLOCK_LENGTHS]


def summarize(
    phi: float, effect: float, length: int, rejections: int, disagreements: int,
) -> dict[str, object]:
    """Report every outcome, with gates applied only to the registered primary setting."""
    rate = rejections / REPLICATIONS
    gate = None
    if length == 20 and effect == 0:
        gate = rate <= NULL_BOUND
    if length == 20 and effect == 0.002:
        gate = rate > 0.8
    return {
        "phi": phi, "mean_effect": effect, "block_length": length,
        "role": "IID comparator" if length == 1 else "primary" if length == 20 else "sensitivity",
        "rejections": rejections, "replications": REPLICATIONS,
        "rejection_rate": rate, "wilson_95_interval": wilson(rejections, REPLICATIONS),
        "registered_gate_pass": gate, "p_interval_disagreements": disagreements,
    }


def reference_fixture(sr: float, n: int, skew: float, kurtosis: float,
                      trials: int, dispersion: float | None) -> dict[str, object]:
    """Evaluate Eq. 2 at 80 digits using inverse erf independently of production."""
    mp = importlib.import_module("mpmath")
    mp.mp.dps = 80
    threshold = mp.mpf(0)
    if trials > 1:
        threshold = mp.mpf(str(dispersion)) * (
            (1 - mp.euler) * mp.sqrt(2) * mp.erfinv(1 - mp.mpf(2) / trials)
            + mp.euler * mp.sqrt(2) * mp.erfinv(1 - mp.mpf(2) / (trials * mp.e))
        )
    ratio = mp.mpf(str(sr))
    variance = 1 - mp.mpf(str(skew)) * ratio + (mp.mpf(str(kurtosis)) - 1) * ratio**2 / 4
    z = (ratio - threshold) * mp.sqrt((n - 1) / variance)
    expected = (1 + mp.erf(z / mp.sqrt(2))) / 2
    actual = deflated_sharpe(observed_sharpe=sr, n_returns=n, skew=skew,
                            kurtosis=kurtosis, n_trials=trials,
                            trial_sharpe_std=dispersion, provenance="registered formula fixture")
    return {
        "observed_sharpe": sr, "n_returns": n, "skew": skew, "kurtosis": kurtosis,
        "n_trials": trials, "trial_sharpe_std": dispersion,
        "expected_threshold_80_digits": str(threshold),
        "expected_probability_80_digits": str(expected), "production_probability": actual,
        "absolute_error": abs(actual - float(expected)),
        "pass_tolerance_1e_12": abs(actual - float(expected)) <= 1e-12,
    }


def source_hashes() -> dict[str, str]:
    """Identify the numerical source files exercised by this validation process."""
    paths = [Path(function.__code__.co_filename)
             for function in (deflated_sharpe, paired_block_test)]
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def main() -> None:
    """Write independent references and the complete unfiltered simulation results."""
    destination = Path(__file__).resolve().parent
    sources = source_hashes()
    fixtures = [reference_fixture(*args) for args in [
        (0.0, 100, 0.0, 3.0, 1, None),
        (0.1, 252, 0.0, 3.0, 1, None),
        (0.15, 500, -0.5, 4.0, 20, 0.08),
        (-0.05, 1200, 0.3, 5.0, 50, 0.04),
        (0.25, 1250, -1.0, 6.0, 100, 0.1),
    ]]
    (destination / "formula-reference.json").write_text(json.dumps(fixtures, indent=2) + "\n")
    rows = []
    scenarios = [(phi, effect) for phi in (0.0, 0.6) for effect in (0.0, 0.001, 0.002)]
    for index, (phi, effect) in enumerate(scenarios):
        results = scenario(phi, effect, index)
        rows.extend(results)
        print(json.dumps(results), flush=True)
    config = {
        "seed": SEED, "replications": REPLICATIONS, "observations": OBSERVATIONS,
        "burn_in": BURN_IN, "resamples": RESAMPLES, "block_lengths": BLOCK_LENGTHS,
        "primary_block_length": 20, "null_gate_bound": NULL_BOUND,
        "marginal_difference_sd": 0.01, "baseline_sd": 0.01,
        "seed_construction": "SeedSequence([20260927, scenario_index]).spawn(300)",
        "numpy_version": np.__version__, "production_source_sha256": sources,
    }
    report = {"configuration": config, "results": rows,
              "all_registered_gates_pass": all(
                  row["registered_gate_pass"] is not False for row in rows)}
    (destination / "simulation-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"all_registered_gates_pass": report["all_registered_gates_pass"]}))
    checks = [report["all_registered_gates_pass"], sources == source_hashes(),
              all(row["p_interval_disagreements"] == 0 for row in rows),
              all(fixture["pass_tolerance_1e_12"] for fixture in fixtures)]
    if not all(checks):
        raise SystemExit("FAIL: formula, calibration, interval or source-stability gate")


if __name__ == "__main__":
    main()
