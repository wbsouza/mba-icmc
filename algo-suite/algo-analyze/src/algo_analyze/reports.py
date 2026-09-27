"""Versioned inference reports; legacy artifacts are read-only and never relabeled."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from statistics import stdev
from typing import Any

from algo_backtest.metrics import metrics_from_artifact

from algo_analyze.deflated import (
    InferenceUnavailable,
    deflated_sharpe,
    return_moments,
    selection_threshold,
)
from algo_analyze.portfolio import (
    align_portfolios,
    load_portfolio_returns,
    source_hash,
)
from algo_analyze.significance import paired_block_test, validate_block_settings

LEGACY_NOTICE = "pre-v2 deflated_sharpe adjustments and pooled-trade p-values are exploratory"


def _selection(path: Path | None) -> dict[str, Any]:
    """Load a computed trial ledger or an explicitly declared external history."""
    if path is None or not path.exists():
        raise InferenceUnavailable("selection history absent; supply --selection manifest.json")
    raw = json.loads(path.read_text())
    if isinstance(raw, list):
        data = _selection_from_ledger(raw)
    elif isinstance(raw, dict) and isinstance(raw.get("trials"), list):
        data = _selection_from_ledger(raw["trials"], raw)
    elif isinstance(raw, dict):
        data = {**raw, "source_kind": "declared"}
    else:
        raise ValueError("selection history must be an object or trial ledger")
    required = {
        "n_trials",
        "trial_sharpe_std",
        "provenance",
        "frequency",
        "trial_count",
        "interim_looks",
    }
    if not required.issubset(data):
        raise ValueError(f"selection manifest requires {sorted(required)}")
    if data["frequency"] != "calendar-day":
        raise ValueError("trial Sharpe dispersion must use nonannualized calendar-day returns")
    _validate_selection_counts(data)
    data["source_sha256"] = source_hash(path)
    return data


def _selection_from_ledger(
    trials: list[Any], metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute DSR selection dispersion from an auditable trial ledger."""
    values = []
    for trial in trials:
        value = trial.get("daily_sharpe") if isinstance(trial, dict) else trial
        if type(value) not in (int, float) or not isinstance(value, (int, float)):
            raise ValueError("selection ledger requires finite daily_sharpe values")
        values.append(float(value))
    if len(values) < 2:
        raise ValueError("selection ledger requires at least two trials")
    result = dict(metadata or {})
    result.update(
        n_trials=result.get("n_trials", len(values)),
        trial_count=len(values),
        trial_sharpe_std=stdev(values),
        frequency=result.get("frequency", "calendar-day"),
        provenance=result.get("provenance", "computed from trial ledger"),
        interim_looks=result.get("interim_looks", 1),
        source_kind="computed",
    )
    if result["n_trials"] > len(values):
        raise ValueError("effective n_trials cannot exceed trial ledger length")
    return result


def _validate_selection_counts(data: dict[str, Any]) -> None:
    """Keep actual counts, effective counts, and provenance independently auditable."""
    for key in ("trial_count", "interim_looks", "n_trials"):
        if type(data[key]) is not int or data[key] < 1:
            raise ValueError(f"selection {key} must be a positive integer")
    if data["n_trials"] > data["trial_count"]:
        raise ValueError("effective n_trials cannot exceed actual trial_count")
    if not isinstance(data["provenance"], str) or not data["provenance"].strip():
        raise ValueError("selection provenance must be nonempty")


def metrics_report(run_dir: Path, selection_path: Path | None) -> dict[str, Any]:
    """Keep engine descriptive metrics separate from frequency-consistent inference."""
    headline = metrics_from_artifact(run_dir / "metrics.json")
    report: dict[str, Any] = {
        "schema_version": 2,
        "descriptive_metrics": headline.as_dict(),
        "descriptive_metrics_sha256": source_hash(run_dir / "metrics.json"),
        "deflated_sharpe_probability": None,
        "legacy_notice": LEGACY_NOTICE,
        "dsr_assumptions": "classical asymptotic expression; serial dependence not corrected",
    }
    try:
        series = load_portfolio_returns(run_dir)
        report["portfolio"] = series.metadata
        moments = return_moments(series.returns)
        report["moments"] = {
            **moments,
            "estimator": "sample SD ddof1; central moments m3/m2^1.5,m4/m2^2",
        }
        selection = _selection(selection_path)
        report["selection"] = selection
        probability = deflated_sharpe(
            observed_sharpe=float(moments["observed_sharpe"]),
            n_returns=int(moments["n_returns"]),
            skew=float(moments["skew"]),
            kurtosis=float(moments["kurtosis"]),
            n_trials=selection["n_trials"],
            trial_sharpe_std=selection["trial_sharpe_std"],
            provenance=selection["provenance"],
        )
        report.update(
            status="available",
            deflated_sharpe_probability=probability,
            selection_threshold=selection_threshold(
                selection["n_trials"], selection["trial_sharpe_std"]
            ),
        )
    except InferenceUnavailable as exc:
        report.update(status="unavailable", reason=str(exc))
    return report


def significance_report(
    run_a: Path,
    run_b: Path,
    *,
    block_lengths: list[int],
    n_resamples: int,
    seed: int,
    block_rule: str,
) -> dict[str, Any]:
    """Record all declared sensitivity lengths; never select the smallest p-value."""
    if not block_lengths or len(set(block_lengths)) != len(block_lengths) or not block_rule.strip():
        raise ValueError("declare unique block lengths and a nonempty prespecified --block-rule")
    for length in block_lengths:
        validate_block_settings(length, n_resamples, seed)
    report: dict[str, Any] = {
        "schema_version": 2,
        "run_a": run_a.name,
        "run_b": run_b.name,
        "legacy_notice": LEGACY_NOTICE,
        "block_rule": block_rule,
        "prespecified_block_lengths": block_lengths,
        "seed": seed,
        "n_resamples": n_resamples,
    }
    try:
        a, b = load_portfolio_returns(run_a), load_portfolio_returns(run_b)
        align_portfolios(a, b)
        report["portfolio_a"], report["portfolio_b"] = a.metadata, b.metadata
        results = []
        for length in block_lengths:
            try:
                result = paired_block_test(
                    a.returns, b.returns, block_length=length, n_resamples=n_resamples, seed=seed
                )
                results.append({"status": "available", **asdict(result)})
            except InferenceUnavailable as exc:
                results.append(
                    {"status": "unavailable", "block_length": length, "reason": str(exc)}
                )
        report.update(status=results[0]["status"], primary=results[0], sensitivity=results[1:])
    except InferenceUnavailable as exc:
        report.update(status="unavailable", reason=str(exc))
    return report


def migration_inventory(data_root: Path) -> dict[str, Any]:
    """Inventory correctability without changing historical files or assuming search counts."""
    runs = []
    for path in sorted((data_root / "runs").rglob("metrics.json")):
        try:
            report = metrics_report(path.parent, None)
            runs.append({"run": str(path.parent.relative_to(data_root)), **report})
        except (ValueError, FileNotFoundError) as exc:
            runs.append(
                {
                    "run": str(path.parent.relative_to(data_root)),
                    "status": "invalid",
                    "reason": str(exc),
                }
            )
    return {
        "schema_version": 2,
        "legacy_notice": LEGACY_NOTICE,
        "runs": runs,
        "action": "preserve historical artifacts; regenerate into separate v2 outputs",
    }
