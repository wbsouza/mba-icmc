"""Build isolated ablation comparison rows from completed backtest run artifacts."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from algo_backtest.metrics import metrics_from_artifact  # type: ignore[import-untyped]


@dataclass(frozen=True)
class AblationRow:
    """One run's metrics plus its total-return delta against the baseline run."""

    run_id: str
    strategy: str
    symbol: str
    start: str
    end: str
    total_return: float
    sharpe: float
    max_drawdown: float
    hit_rate: float
    delta_total_return: float


def build_ablation_table(run_dirs: Sequence[Path], *, baseline: str) -> list[AblationRow]:
    """Load run metrics and compare each run's total return with ``baseline``.

    Args:
        run_dirs: Completed run directories. Each directory must contain ``metrics.json``
            and a complete ``run.json`` manifest.
        baseline: Run identifier to compare against. The identifier is the run directory name.

    Raises:
        FileNotFoundError: a run directory, run manifest, or metrics artifact is missing.
        ValueError: the baseline identifier is absent or a run manifest is malformed.
    """
    rows = [_load_run(run_dir) for run_dir in run_dirs]
    baseline_row = _baseline_row(rows, baseline)
    return [
        AblationRow(
            run_id=row.run_id,
            strategy=row.strategy,
            symbol=row.symbol,
            start=row.start,
            end=row.end,
            total_return=row.total_return,
            sharpe=row.sharpe,
            max_drawdown=row.max_drawdown,
            hit_rate=row.hit_rate,
            delta_total_return=row.total_return - baseline_row.total_return,
        )
        for row in rows
    ]


@dataclass(frozen=True)
class _RunRow:
    """Internal run row before baseline deltas are known."""

    run_id: str
    strategy: str
    symbol: str
    start: str
    end: str
    total_return: float
    sharpe: float
    max_drawdown: float
    hit_rate: float


def _load_run(run_dir: Path) -> _RunRow:
    """Load one run directory, failing fast when required artifacts are absent."""
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run {run_dir.name!r} is missing: {run_dir}")
    metrics_path = run_dir / "metrics.json"
    if not metrics_path.is_file():
        raise FileNotFoundError(f"run {run_dir.name!r} has no metrics artifact: {metrics_path}")
    metrics = metrics_from_artifact(metrics_path)
    manifest = _load_manifest(run_dir)
    return _RunRow(
        run_id=run_dir.name,
        strategy=str(manifest.get("strategy", run_dir.name)),
        symbol=str(manifest.get("symbol", "")),
        start=str(manifest.get("start", "")),
        end=str(manifest.get("end", "")),
        total_return=metrics.total_return,
        sharpe=metrics.sharpe,
        max_drawdown=metrics.max_drawdown,
        hit_rate=metrics.hit_rate,
    )


def _load_manifest(run_dir: Path) -> dict[str, Any]:
    """Load required run metadata from ``run.json`` and reject malformed manifests."""
    path = run_dir / "run.json"
    if not path.is_file():
        raise FileNotFoundError(f"run {run_dir.name!r} has no run manifest: {path}")
    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"run {run_dir.name!r} has an invalid run manifest: {path}") from exc
    if not isinstance(document, dict):
        raise ValueError(f"run {run_dir.name!r} has a non-object run manifest: {path}")
    _require_manifest_fields(run_dir, document)
    return document


def _require_manifest_fields(run_dir: Path, document: dict[str, Any]) -> None:
    """Require the metadata emitted by ``algo_backtest.artifacts.RunManifest``."""
    for name in ("strategy", "symbol", "start", "end"):
        value = document.get(name)
        if not isinstance(value, str) or not value:
            manifest_path = run_dir / "run.json"
            raise ValueError(
                f"run {run_dir.name!r} manifest has no {name!r}: {manifest_path}"
            )


def _baseline_row(rows: list[_RunRow], baseline: str) -> _RunRow:
    """Return the baseline row or fail with the available run identifiers."""
    for row in rows:
        if row.run_id == baseline:
            return row
    known = ", ".join(row.run_id for row in rows) or "<none>"
    raise ValueError(f"baseline run {baseline!r} was not provided; known runs: {known}")
