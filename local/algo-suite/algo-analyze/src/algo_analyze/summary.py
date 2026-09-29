"""Aggregate experiment manifests into the canonical Chapter-4 summary table (Stage F2).

A backtest *experiment* (Stage F1) writes one `experiment.json` per experiment under
`runs/experiments/<experiment>/`, holding one flat row per run. F2 unions those rows across
every successful experiment into a single deterministic CSV — the table the thesis cites
and audits. It reads the experiment manifests only (not the per-run artifacts); the
manifest is already the row contract.

Contract:
  * Source: `runs/experiments/*/experiment.json`. A directory with only
    `experiment-error.json` (a failed experiment) is skipped; a directory with **both** a
    manifest and an error artifact is an inconsistent state and fails fast.
  * Each manifest row must have **exactly** SUMMARY_COLUMNS — missing/unknown columns or a
    wrong-typed field fails fast, naming the manifest path and the field.
  * Output is deterministic: manifest paths are sorted before loading and rows are sorted
    by (experiment, run_id), so re-running without data changes yields a byte-stable CSV
    (the CSV carries no timestamp). The write is atomic (temp file + os.replace).

Not analytics — no deltas, ranking, or significance tests; the table just tabulates so a
baseline and a (later) hybrid strategy sit side by side, ready for comparison.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict, cast

from algo_core.atomicio import write_text_atomic

SUMMARY_COLUMNS: tuple[str, ...] = (
    "experiment", "run_id", "strategy", "symbol", "from", "to",
    "success", "closed_trades", "total_return", "sharpe", "max_drawdown",
    "hit_rate", "run_dir",
)


SummaryRow = TypedDict(
    "SummaryRow",
    {
        "experiment": str, "run_id": str, "strategy": str, "symbol": str,
        "from": str, "to": str, "success": bool, "closed_trades": int,
        "total_return": float, "sharpe": float, "max_drawdown": float,
        "hit_rate": float, "run_dir": str,
    },
)


def _is_number(value: Any) -> bool:
    """Whether value is a real number (int/float but not bool)."""
    return isinstance(value, int | float) and not isinstance(value, bool)


# (column, predicate, human description) — drives one validation loop (low complexity).
_FIELD_CHECKS: tuple[tuple[str, Callable[[Any], bool], str], ...] = (
    ("experiment", lambda v: isinstance(v, str), "a string"),
    ("run_id", lambda v: isinstance(v, str), "a string"),
    ("strategy", lambda v: isinstance(v, str), "a string"),
    ("symbol", lambda v: isinstance(v, str), "a string"),
    ("from", lambda v: isinstance(v, str), "a string"),
    ("to", lambda v: isinstance(v, str), "a string"),
    ("success", lambda v: isinstance(v, bool), "a boolean"),
    ("closed_trades", lambda v: isinstance(v, int) and not isinstance(v, bool), "an integer"),
    ("total_return", _is_number, "numeric"),
    ("sharpe", _is_number, "numeric"),
    ("max_drawdown", _is_number, "numeric"),
    ("hit_rate", _is_number, "numeric"),
    ("run_dir", lambda v: isinstance(v, str), "a string path"),
)


def discover_experiment_manifests(data_root: Path) -> list[Path]:
    """Find every successful experiment manifest under data_root, sorted for determinism.

    Raises:
        ValueError: no experiments directory, an experiment with both a manifest and an
            error artifact (inconsistent), or no successful experiments at all (fail fast).
    """
    base = data_root / "runs" / "experiments"
    if not base.is_dir():
        raise ValueError(
            f"no experiments under {base}; run `algo-backtest experiment run --spec ...` first"
        )
    manifests: list[Path] = []
    for directory in sorted(p for p in base.iterdir() if p.is_dir()):
        manifest = directory / "experiment.json"
        error = directory / "experiment-error.json"
        if manifest.is_file() and error.is_file():
            raise ValueError(
                f"{directory}: has both experiment.json and experiment-error.json; resolve "
                "the inconsistent experiment state (re-run or remove the stale artifact)"
            )
        if manifest.is_file():
            manifests.append(manifest)
    if not manifests:
        raise ValueError(
            f"no successful experiment manifests under {base}; every experiment failed or "
            "none completed — check the experiment-error.json artifacts"
        )
    return manifests


def load_summary_rows(manifests: list[Path]) -> list[SummaryRow]:
    """Load + validate every run row across the manifests, sorted deterministically.

    Beyond per-row shape, enforces the producer/consumer integrity the canonical table
    relies on: each row's `experiment` matches its manifest's name, only successful runs
    are aggregated, and `(experiment, run_id)` is unique across the whole summary.

    Raises:
        ValueError: a manifest is not valid JSON / not an experiment manifest; a row has
            the wrong columns or a wrong-typed field; a row's experiment disagrees with the
            manifest; a row is not successful; or a duplicate (experiment, run_id) appears.
    """
    rows: list[SummaryRow] = []
    for path in manifests:
        document = _load_manifest(path)
        name = str(document["experiment"])
        rows.extend(_checked_row(row, path, name) for row in document["runs"])
    _reject_duplicates(rows)
    rows.sort(key=lambda row: (row["experiment"], row["run_id"]))
    return rows


def _checked_row(raw: Any, path: Path, experiment_name: str) -> SummaryRow:
    """Validate a row's shape, then its provenance: experiment match + success=true."""
    row = _validate_row(raw, path)
    if row["experiment"] != experiment_name:
        raise ValueError(
            f"{path}: run {row['run_id']!r} is labeled experiment {row['experiment']!r} "
            f"but the manifest is {experiment_name!r}"
        )
    if not row["success"]:
        raise ValueError(
            f"{path}: run {row['run_id']!r} has success=false; the summary aggregates only "
            "successful runs — re-run it or remove it"
        )
    return row


def _reject_duplicates(rows: list[SummaryRow]) -> None:
    """Fail fast on a repeated (experiment, run_id) — the table's identity must be unique."""
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (row["experiment"], row["run_id"])
        if key in seen:
            raise ValueError(
                f"duplicate (experiment, run_id) {key}; run ids must be unique across the summary"
            )
        seen.add(key)


def write_summary_csv(rows: list[SummaryRow], out: Path) -> Path:
    """Write the rows to a CSV at `out` atomically (temp file + os.replace).

    Atomic because this is a thesis-facing artifact: a reader never sees a half-written
    table. Column order is fixed to SUMMARY_COLUMNS.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(SUMMARY_COLUMNS))
    writer.writeheader()
    writer.writerows(rows)
    write_text_atomic(out, buffer.getvalue())
    return out


def _load_manifest(path: Path) -> dict[str, Any]:
    """Parse + structurally validate one experiment manifest (fail fast)."""
    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path}: not valid JSON ({exc}); the experiment manifest is corrupt"
        ) from exc
    if not isinstance(document, dict) or not isinstance(document.get("experiment"), str):
        raise ValueError(f"{path}: not an experiment manifest (missing the 'experiment' name)")
    if not isinstance(document.get("runs"), list):
        raise ValueError(f"{path}: experiment manifest has no 'runs' list")
    return document


def _validate_row(row: Any, path: Path) -> SummaryRow:
    """Validate one run row against the exact column contract (fail fast)."""
    if not isinstance(row, dict):
        raise ValueError(f"{path}: run row is not a mapping: {row!r}")
    keys = set(row)
    expected = set(SUMMARY_COLUMNS)
    if keys != expected:
        missing = sorted(expected - keys)
        unknown = sorted(keys - expected)
        raise ValueError(
            f"{path}: run row has wrong columns (missing={missing}, unknown={unknown})"
        )
    for field, ok, description in _FIELD_CHECKS:
        if not ok(row[field]):
            raise ValueError(
                f"{path}: run field {field!r} must be {description}, got {row[field]!r}"
            )
    return cast(SummaryRow, {column: row[column] for column in SUMMARY_COLUMNS})
