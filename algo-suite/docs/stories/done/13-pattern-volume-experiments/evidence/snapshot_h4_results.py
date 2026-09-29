"""Archive completed H4 evidence read-only; never edit experiment or old snapshot files."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

EVIDENCE = Path(__file__).resolve().parent
EXPERIMENTS = EVIDENCE.parents[4] / "build/experiments"
ROOTS = ("20260928-baseline-h4-v1", "20260928-hybrid-h4-v2")
FILTER_SECTIONS = {
    "F1": ("perception_source", "price_features"),
    "F2": ("indicator", "price_features"),
    "F3": ("pattern",),
    "F4": ("news_context",),
    "volume": ("volume_strength",),
    "F5": ("risk_guard",),
    "F6": ("capital_mgmt", "price_features"),
    "F7": ("meta_learner",),
}


def artifact(path: Path, content: bool = True) -> dict[str, Any]:
    """Capture exact source bytes or record missing evidence without inferring values."""
    if not path.is_file():
        return {"path": str(path), "status": "missing"}
    raw = path.read_bytes()
    result: dict[str, Any] = {"path": str(path), "status": "present",
                              "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    if content:
        result["value"] = json.loads(raw) if path.suffix == ".json" else raw.decode()
    return result


def require_complete(matrix: dict[str, Any]) -> None:
    """Require parent and integrity completion, not a shell exit status alone."""
    files = matrix["files"]
    exit_status = files["exit-status.json"].get("value", {})
    final = files["final-input-check.json"].get("value", {})
    if exit_status.get("exit_code") != 0 or final.get("ok") is not True:
        raise ValueError("Incomplete matrix: wait for exit 0 AND successful final-input-check")
    if final["errors"] or final["mismatches"]:
        raise ValueError("Integrity errors: retain failure; request a new experiment root")
    for entries in final["groups"].values():
        if any(entry["matches"] is not True for entry in entries.values()):
            raise ValueError("Integrity mismatch: do not publish completed matrix results")


def collect_matrix(root: Path) -> dict[str, Any]:
    """Retain manifests and every batch boundary check before admitting its cells."""
    names = ("manifest.json", "prepared-hashes.json", "execution-started.json",
             "exit-status.json", "final-input-check.json")
    paths = [root / name for name in names] + sorted(root.glob("batch-*-input-check.json"))
    matrix = {"root": str(root), "files": {path.name: artifact(path) for path in paths}}
    require_complete(matrix)
    return matrix


def validate_cell(run: dict[str, Any]) -> None:
    """Reconcile independent run, ledger, prepared config, and sealed model records."""
    files = run["files"]
    status, manifest = files["status.json"]["value"], files["run.json"]["value"]
    if status != {"backtest": 0, "exit_code": 0, "state": "succeeded", "training": 0}:
        raise ValueError("Incomplete cell: inspect status.json; no partial-result promotion")
    if manifest["success"] is not True:
        raise ValueError("Failed run.json: retain the failure instead of plotting success")
    if manifest["closed_trades"] != len(files["trades.json"]["value"]):
        raise ValueError("Trade count disagreement: audit ledger, never invert win rate")
    config = files["strategy-config.json"]["value"]
    if config != yaml.safe_load(files["strategy-config.yaml"]["value"]):
        raise ValueError("Config JSON/YAML mismatch: investigate before reporting")
    if config != files["prepared-config.json"]["value"]:
        raise ValueError("Prepared/runtime config mismatch: investigate before reporting")
    if config != run["model_provenance"]["strategy_config"]:
        raise ValueError("Training/runtime config mismatch: investigate before reporting")
    if files["model.json"]["sha256"] != files["hashes.json"]["value"]["model_sha256"]:
        raise ValueError("Model hash mismatch: investigate sealed training/backtest identity")


def collect_cell(root: Path, reference: str) -> dict[str, Any]:
    """Join actual results with the per-cell effective configuration and model identity."""
    result_names = ("run.json", "metrics.json", "trades.json", "equity.csv",
                    "strategy-config.json", "strategy-config.yaml", "strategy-provenance.json",
                    "inference-inputs.json")
    files = {name: artifact(root / "results" / name) for name in result_names}
    for name in ("status.json", "hashes.json", "commands.json", "template-settings.md",
                 "parameters.md", "training.log", "backtest.log"):
        files[name] = artifact(root / name)
    files["prepared-config.json"] = artifact(root / "strategy-config.json")
    files["model.json"] = artifact(root / "model.json", False)
    files["main.json"] = artifact(root / "results/main.json", False)
    files["decisions.parquet"] = artifact(root / "results/decisions.parquet", False)
    model = json.loads((root / "model.json").read_text())
    engine = json.loads((root / "results/main.json").read_text())
    run = {"reference": reference, "root": str(root), "status": "successful", "files": files,
           "model_provenance": model["provenance"],
           "engine_summary": {key: engine[key] for key in
                              ("algorithmConfiguration", "runtimeStatistics", "statistics")}}
    validate_cell(run)
    return run


def collect_interrupted() -> dict[str, Any]:
    """Keep hybrid v1's successful subset and ENOSPC failure distinct from v2."""
    root = EXPERIMENTS / "20260928-hybrid-h4-v1"
    manifest = artifact(root / "manifest.json")
    cells = []
    for name in manifest["value"]["plan"]["variants"]:
        paths = ("status.json", "backtest.log", "results/run.json", "strategy-config.json",
                 "strategy-config.yaml", "strategy-provenance.json", "hashes.json")
        cells.append({"root": str(root / name), "files": {
            path: artifact(root / name / path) for path in paths}})
    return {"root": str(root), "classification": "interrupted_ENOSPC_not_complete",
            "parent_exit_code_observed_by_controller": 1, "manifest": manifest, "cells": cells,
            "exit_status": artifact(root / "exit-status.json"),
            "final_input_check": artifact(root / "final-input-check.json")}


def parameter_sections(config: dict[str, Any]) -> dict[str, Any]:
    """Name every filter, explicitly marking absent sections instead of using defaults."""
    return {name: {key: config.get(key, "ABSENT in archived configuration") for key in keys}
            for name, keys in FILTER_SECTIONS.items()}


def appendix(snapshot: dict[str, Any]) -> str:
    """Repeat full per-cell parameters alongside each result, with artifact hash links."""
    lines = ["# H4 per-cell results and effective parameters", "",
             f"Clock confirmed: {snapshot['clock_confirmed_utc']}. Exploratory only.", "",
             "No fields are filled from current defaults. Absent filters are explicit.", "",
             "Closed trades are counted in trades.json and checked against run.json.", ""]
    for run in snapshot["runs"]:
        files = run["files"]
        lines += [f"## {run['reference']}", "", f"Source: `{run['root']}`.", "",
                  "### Actual result", "", "```json", json.dumps({
                      "run": files["run.json"]["value"], "metrics": files["metrics.json"]["value"],
                      "engine_summary": run["engine_summary"],
                      "model_sha256": files["model.json"]["sha256"],
                      "model_revision": run["model_provenance"]["git_revision"]}, indent=2),
                  "```", ""]
        for name, settings in parameter_sections(files["strategy-config.json"]["value"]).items():
            lines += [f"### {name}", "", "```json", json.dumps(settings, indent=2), "```", ""]
        lines += ["### Complete resolved configuration and per-field provenance", "", "```json",
                  json.dumps({"configuration": files["strategy-config.json"]["value"],
                              "provenance": files["strategy-provenance.json"]["value"]}, indent=2),
                  "```", "", "### Source fingerprints", "", "| Artifact | SHA-256 |",
                  "| --- | --- |"]
        lines += [f"| [{name}]({item['path']}) | {item.get('sha256', 'MISSING')} |"
                  for name, item in files.items()]
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    """Create a uniquely named archive only after both matrices meet completion gates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clock-utc", required=True, help="UTC timestamp confirmed by clock tool")
    args = parser.parse_args()
    clock = datetime.fromisoformat(args.clock_utc)
    stamp = clock.strftime("%Y%m%dT%H%M%SZ")
    started = datetime.now(UTC).isoformat()
    matrices = [collect_matrix(EXPERIMENTS / name) for name in ROOTS]
    runs: list[dict[str, Any]] = []
    for matrix in matrices:
        for variant in matrix["files"]["manifest.json"]["value"]["plan"]["variants"]:
            runs.append(collect_cell(Path(matrix["root"]) / variant, f"H{len(runs) + 1:02}"))
    snapshot = {"clock_confirmed_utc": args.clock_utc, "collection_started_utc": started,
                "collection_ended_utc": datetime.now(UTC).isoformat(),
                "classification": "exploratory", "matrices": matrices, "runs": runs,
                "interrupted_hybrid_v1": collect_interrupted(),
                "prior_snapshot": artifact(EVIDENCE / "snapshot-20260928T003601Z.json", False)}
    for name, content in ((f"h4-snapshot-{stamp}.json", json.dumps(snapshot, indent=2) + "\n"),
                          (f"h4-parameters-{stamp}.md", appendix(snapshot))):
        with (EVIDENCE / name).open("x") as handle:
            handle.write(content)
        print(EVIDENCE / name)


if __name__ == "__main__":
    main()
