"""Validate real completed paired CLI runs without rerunning expensive backtests.

Run with --data-root DATA --runs baseline/STAMP --runs baseline-dsha/STAMP --out OUT.
Native readiness/timing tests and quality gates remain separate mandatory QA stages.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pyarrow.parquet as pq


def require(condition: bool, message: str) -> None:
    """Fail even under python -O."""
    if not condition:
        raise AssertionError(message)


def digest(path: Path) -> str:
    """Hash authentic source bytes."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect_run(root: Path, run_id: str, strategy: str, out: Path) -> dict:
    """Require completion and copy only small genuine artifacts."""
    run = root / "runs" / run_id
    manifest = json.loads((run / "run.json").read_text())
    require(manifest["success"] is True, f"{run_id}: unsuccessful")
    require(manifest["strategy"] == strategy, f"{run_id}: wrong strategy")
    trades = json.loads((run / "trades.json").read_text())
    require(len(trades) == manifest["closed_trades"], "trade count mismatch")
    destination = out / strategy
    destination.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in ("run.json", "metrics.json", "trades.json", "decisions.parquet", "log.txt"):
        hashes[name] = digest(run / name)
        if name in ("run.json", "metrics.json"):
            shutil.copyfile(run / name, destination / name)
    model_hashes = set(re.findall(r"MODEL_SHA256=([a-f0-9]{64})", (run / "log.txt").read_text()))
    require(len(model_hashes) == 1, f"{run_id}: missing/inconsistent actual model hash")
    config_path = run / "strategy-config.json"
    require(config_path.is_file(), f"{run_id}: missing engine-written strategy-config.json")
    config = json.loads(config_path.read_text())
    hashes["strategy-config.json"] = digest(config_path)
    origin = "engine-written strategy-config.json"
    shutil.copyfile(config_path, destination / "strategy-config.json")
    return {
        "run_id": run_id,
        "manifest": manifest,
        "artifact_sha256": hashes,
        "model_sha256": next(iter(model_hashes)),
        "config": config,
        "config_origin": origin,
        "reproduce_backtest": shlex.join(
            [
                "algo-backtest",
                "run",
                "--strategy",
                strategy,
                "--symbol",
                manifest["symbol"],
                "--from",
                manifest["start"],
                "--to",
                manifest["end"],
                *[
                    part
                    for key, value in manifest["params"].items()
                    for part in ("--param", f"{key}={value}")
                ],
            ]
        ),
    }


def compare_configs(baseline: dict, candidate: dict) -> None:
    """Require matching window, account settings and frozen F7 model."""
    for key in ("symbol", "start", "end", "params"):
        require(baseline["manifest"][key] == candidate["manifest"][key], f"different {key}")
    require(baseline["model_sha256"] == candidate["model_sha256"], "F7 model was not frozen")
    require(baseline["config"].get("perception_source", "ema") == "ema", "wrong baseline")
    require(
        candidate["config"]["perception_source"] == "double_smoothed_heikin_ashi",
        "wrong candidate perception",
    )
    require(
        candidate["config"]["double_smoothed_heikin_ashi"]
        == {"period1": 6, "period2": 2, "higher_tf_minutes": 60},
        "wrong candidate smoothing",
    )
    exclude = {"extends", "perception_source", "double_smoothed_heikin_ashi"}
    stable = [
        {k: v for k, v in run["config"].items() if k not in exclude}
        for run in (baseline, candidate)
    ]
    require(stable[0] == stable[1], "non-perception strategy settings changed")


def decisions(root: Path, run_id: str) -> dict:
    """Extract genuine F1 results and feature hashes from the audit trail."""
    rows = pq.read_table(root / "runs" / run_id / "decisions.parquet").to_pylist()
    require(bool(rows), f"{run_id}: no decisions")
    return {
        row["timestamp"]: {
            "features_hash": row["features_hash"],
            "f1": next(item for item in row["filter_results"] if item["filter_name"] == "F1_trend"),
        }
        for row in rows
    }


def compare_decisions(root: Path, run_ids: list[str]) -> dict:
    """Validate consumed directions and compare overlapping decision observations."""
    baseline, candidate = (decisions(root, run_id) for run_id in run_ids)
    for value in candidate.values():
        reason = value["f1"]["reason"]
        directions = re.findall(r"(?:higher_tf_)?trend_direction=(-?[\d.]+)", reason)
        require(len(directions) == 2, f"missing directions: {reason}")
        require(
            all(float(number) in (-1.0, 1.0) for number in directions),
            f"consumed unready/non-directional candidate: {reason}",
        )
    require(min(candidate) > min(baseline), "candidate warm-up no longer starts later")
    require(len(candidate) < len(baseline), "candidate warm-up no longer omits early decisions")
    shared = sorted(baseline.keys() & candidate.keys())
    require(bool(shared), "no overlapping decisions")
    changed = sum(baseline[t]["features_hash"] != candidate[t]["features_hash"] for t in shared)
    f1_changed = sum(baseline[t]["f1"] != candidate[t]["f1"] for t in shared)
    strengths_checked = 0
    for timestamp in shared:
        strengths = [
            re.search(r"trend_strength=([\d.]+)", data[timestamp]["f1"]["reason"])
            for data in (baseline, candidate)
        ]
        if all(strengths):
            require(strengths[0][1] == strengths[1][1], "trend strength changed")
            strengths_checked += 1
    require(changed > 0 and f1_changed > 0, "no observed candidate perception change")
    require(strengths_checked > 0, "no comparable strength observations")
    return {
        "baseline_rows": len(baseline),
        "candidate_rows": len(candidate),
        "shared_timestamps": len(shared),
        "changed_features": changed,
        "changed_f1_results": f1_changed,
        "equal_strength_observations": strengths_checked,
        "first_baseline_timestamp": str(min(baseline)),
        "first_candidate_timestamp": str(min(candidate)),
        "timing_limit": (
            "Per-bar readiness/candle state absent; "
            "native integration tests verify closed-bar timing."
        ),
    }


def ablation(root: Path, run_ids: list[str], out: Path) -> list[dict]:
    """Drive the public analyzer CLI, preserving its actual JSON and CSV."""
    command = [
        "algo-analyze",
        "ablation",
        "--runs",
        run_ids[0],
        "--runs",
        run_ids[1],
        "--baseline",
        Path(run_ids[0]).name,
    ]
    result = subprocess.run(
        command,
        env={**os.environ, "ALGO_DATA_ROOT": str(root)},
        capture_output=True,
        text=True,
        check=False,
    )
    (out / "ablation-cli.stdout.txt").write_text(result.stdout)
    (out / "ablation-cli.stderr.txt").write_text(result.stderr)
    require(result.returncode == 0, f"ablation CLI failed: {result.stderr}")
    rows = json.loads(result.stdout)
    require(len(rows) == 2, "expected exactly two ablation rows")
    require(
        {row["run_id"] for row in rows} == {Path(item).name for item in run_ids},
        "unexpected ablation run IDs",
    )
    with (out / "ablation.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (out / "commands.txt").write_text(
        "ALGO_DATA_ROOT=" + shlex.quote(str(root)) + " " + shlex.join(command) + "\n"
    )
    return rows


def write_report(out: Path, evidence: dict) -> None:
    """Explain the frozen-model comparison without implying profitability."""
    columns = ("strategy", "total_return", "sharpe", "max_drawdown", "hit_rate")
    lines = [
        "# Perception-source ablation with frozen EMA-trained F7 model",
        "",
        "EURUSD historical minute quotes; identical window and account parameters. "
        "This short smoke comparison is not evidence of profitability.",
        "",
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    lines.extend(
        "| " + " | ".join(str(row[key]) for key in columns) + " |" for row in evidence["ablation"]
    )
    lines.extend(
        [
            "",
            "The CSV and CLI JSON contain the actual completed-run metrics. "
            "qa-evidence.json records artifact, frozen model and input ZIP hashes, "
            "decision comparisons, and configuration provenance.",
            "",
            "Pass 1 is LEAN Wilder(6); pass 2 is LEAN LWMA(2), matching MT4's "
            "default second period of 2 (the historical Java implementation used 1). "
            "Ties classify down. LEAN warmup and bar boundaries may differ from MT4.",
            "",
            "Both resolved configurations are engine-written strategy-config.json artifacts. "
            "Their hashes are recorded; no QA snapshot fallback is accepted. "
            "Actual model parity is checked from each engine log.",
            "",
            "Decision artifacts expose consumed directions and feature hashes, but "
            "not per-bar readiness or underlying candle times. Native integration "
            "acceptance tests are the timing/readiness gate. Workspace, coverage, "
            "complexity and mutation gates are recorded separately.",
            "",
        ]
    )
    (out / "README.md").write_text("\n".join(lines))


def data_provenance(root: Path, manifest: dict) -> dict:
    """Hash the shared daily input ZIPs, including one prior day of warmup."""
    first = date.fromisoformat(manifest["start"]) - timedelta(days=1)
    last = date.fromisoformat(manifest["end"])
    folder = root / "lean-data" / "forex" / "oanda" / "minute" / manifest["symbol"].lower()
    hashes = {}
    current = first
    while current <= last:
        path = folder / f"{current:%Y%m%d}_quote.zip"
        if path.is_file():
            hashes[str(path.relative_to(root))] = digest(path)
        current += timedelta(days=1)
    require(bool(hashes), "no actual input ZIPs found")
    return {
        "source": "existing materialized OANDA-format historical quotes",
        "input_zip_sha256": hashes,
        "limit": "Hashes cover the window and one prior day, not an engine access trace.",
    }


def main() -> None:
    """Fail deterministically on missing artifacts or invalid comparisons."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--runs", action="append", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--code-revision", required=True, help="Clean commit used for both runs")
    args = parser.parse_args()
    require(len(args.runs) == 2 and len(set(args.runs)) == 2, "provide two distinct --runs IDs")
    args.out.mkdir(parents=True, exist_ok=True)
    root = args.data_root.resolve()
    runs = [
        inspect_run(root, run_id, strategy, args.out)
        for run_id, strategy in zip(args.runs, ("baseline", "baseline-dsha"), strict=True)
    ]
    compare_configs(*runs)
    evidence = {
        "scope": "real completed-run artifact QA; native and quality gates separate",
        "code_revision": args.code_revision,
        "runs": runs,
        "data_provenance": data_provenance(root, runs[0]["manifest"]),
        "decision_comparison": compare_decisions(root, args.runs),
        "ablation": ablation(root, args.runs, args.out),
    }
    (args.out / "qa-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    write_report(args.out, evidence)
    print(f"PASS: completed-run artifact QA: {args.runs}; evidence: {args.out}")


if __name__ == "__main__":
    main()
