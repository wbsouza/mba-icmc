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
# Registered extensions (method-design.md): candidate block-length rules at thesis-scale
# windows, each with its own scenario-index range so every study reproduces independently.
EXTENSION_OBSERVATIONS = (90, 180)


def rule_block_length(n: int) -> int:
    """First candidate rule, L = max(1, floor(n^(1/3)))."""
    return max(1, math.floor(round(math.pow(n, 1 / 3), 9)))


def guard_block_length(n: int) -> int:
    """Second candidate rule, the maximal feasible length under the ten-block guard."""
    return max(1, n // 10)


EXTENSION_RULES = (
    ("floor(n^(1/3))", rule_block_length, 6),
    ("floor(n/10)", guard_block_length, 18),
)


def wilson(successes: int, count: int) -> list[float]:
    """Compute a two-sided Wilson 95 percent binomial interval independently."""
    z = 1.959963984540054
    p = successes / count
    divisor = 1 + z * z / count
    center = (p + z * z / (2 * count)) / divisor
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count**2)) / divisor
    return [center - radius, center + radius]


def paired_sample(
    rng: np.random.Generator, phi: float, effect: float, observations: int = OBSERVATIONS,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Generate the registered stationary AR(1) difference and shared baseline."""
    n = observations + BURN_IN
    innovations = rng.normal(0, 0.01 * math.sqrt(1 - phi**2), n)
    differences = np.empty(n)
    differences[0] = rng.normal(0, 0.01)
    for index in range(1, n):
        differences[index] = phi * differences[index - 1] + innovations[index]
    baseline = rng.normal(0, 0.01, observations)
    return baseline, baseline + differences[BURN_IN:] + effect


def scenario(
    phi: float, effect: float, scenario_index: int,
    observations: int = OBSERVATIONS, block_lengths: tuple[int, ...] = BLOCK_LENGTHS,
    primary: int = 20,
) -> list[dict[str, object]]:
    """Evaluate all declared settings with identical samples and bootstrap seeds."""
    rejections = dict.fromkeys(block_lengths, 0)
    disagreements = dict.fromkeys(block_lengths, 0)
    seeds = np.random.SeedSequence([SEED, scenario_index]).spawn(REPLICATIONS)
    for seed in seeds:
        rng = np.random.default_rng(seed)
        a, b = paired_sample(rng, phi, effect, observations)
        bootstrap_seed = int(rng.integers(0, 2**32))
        for length in block_lengths:
            result = paired_block_test(
                a.tolist(), b.tolist(), block_length=length,
                n_resamples=RESAMPLES, seed=bootstrap_seed,
            )
            rejections[length] += result.reject_null
            lower, upper = result.confidence_interval
            disagreements[length] += result.reject_null != (lower > 0 or upper < 0)
    return [summarize(phi, effect, length, rejections[length], disagreements[length],
                      observations, primary)
            for length in block_lengths]


def summarize(
    phi: float, effect: float, length: int, rejections: int, disagreements: int,
    observations: int = OBSERVATIONS, primary: int = 20,
) -> dict[str, object]:
    """Report every outcome; gates apply only to the registered primary setting."""
    rate = rejections / REPLICATIONS
    gate = None
    if length == primary and effect == 0:
        gate = rate <= NULL_BOUND
    if length == primary and effect == 0.002 and observations == OBSERVATIONS:
        gate = rate > 0.8
    role = "IID comparator" if length == 1 else "primary" if length == primary else "sensitivity"
    return {
        "phi": phi, "mean_effect": effect, "n_observations": observations,
        "block_length": length, "role": role,
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
        (0.2, 100, 0.0, 3.0, 10, 0.1),
    ]]
    (destination / "formula-reference.json").write_text(json.dumps(fixtures, indent=2) + "\n")
    rows = []
    scenarios = [(phi, effect) for phi in (0.0, 0.6) for effect in (0.0, 0.001, 0.002)]
    for index, (phi, effect) in enumerate(scenarios):
        results = scenario(phi, effect, index)
        rows.extend(results)
        print(json.dumps(results), flush=True)
    extension = [(n, phi, effect) for n in EXTENSION_OBSERVATIONS
                 for phi in (0.0, 0.6) for effect in (0.0, 0.001, 0.002)]
    for name, rule_function, first_index in EXTENSION_RULES:
        for offset, (n, phi, effect) in enumerate(extension, start=first_index):
            rule = rule_function(n)
            results = scenario(phi, effect, offset, n, (1, rule), rule)
            for row in results:
                row["block_length_rule"] = name
            rows.extend(results)
            print(json.dumps(results), flush=True)
    config = {
        "seed": SEED, "replications": REPLICATIONS, "observations": OBSERVATIONS,
        "burn_in": BURN_IN, "resamples": RESAMPLES, "block_lengths": BLOCK_LENGTHS,
        "primary_block_length": 20, "null_gate_bound": NULL_BOUND,
        "extensions": [
            {
                "block_length_rule": name,
                "observations": EXTENSION_OBSERVATIONS,
                "rule_lengths": {n: rule_function(n) for n in EXTENSION_OBSERVATIONS},
                "scenario_indices": list(range(first, first + len(extension))),
                "gates": "null rejection <= null_gate_bound at the rule length; power reported",
            }
            for name, rule_function, first in EXTENSION_RULES
        ],
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
