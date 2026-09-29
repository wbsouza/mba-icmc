"""Deterministic QA check for a finished chain-strategy run (see qa-procedure.md).

Exit code 0 means every check passed for every run directory given; 1 otherwise. The
checks prove the machinery — decisions became trades, the account started from the
requested cash, and the parameters the run used are auditable — not the strategy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq


def _check(run_dir: Path, cash: float) -> list[tuple[str, bool, str]]:
    """Every (check name, passed, detail) triple for one run directory."""
    run = json.loads((run_dir / "run.json").read_text())
    main = json.loads((run_dir / "main.json").read_text())
    config = json.loads((run_dir / "strategy-config.json").read_text())
    trades = json.loads((run_dir / "trades.json").read_text())
    log = (run_dir / "log.txt").read_text()
    decisions = pq.read_table(run_dir / "decisions.parquet").to_pydict()  # type: ignore[no-untyped-call]
    finals = set(decisions["final_decision"])
    joined = sum(1 for trade_id in decisions["trade_id"] if trade_id is not None)
    equity = [row[1] for row in main["charts"]["Strategy Equity"]["series"]["Equity"]["values"]]
    stats = main["statistics"]
    meta = config["meta_learner"]
    return [
        ("run succeeded", run["success"] is True, f"success={run['success']}"),
        ("closed trades > 0", len(trades) > 0, f"closed_trades={len(trades)}"),
        ("BUY and SELL decided", {"BUY", "SELL"} <= finals, f"decisions={sorted(finals)}"),
        ("decisions join trades", joined > 0, f"rows with trade_id={joined}"),
        ("starting cash logged", f"_STARTING_CASH={cash:.1f}" in log, f"expected {cash:.1f}"),
        ("start equity = cash", float(stats["Start Equity"]) == cash, stats["Start Equity"]),
        ("equity not flat", len(set(equity)) > 1, f"points={len(equity)}"),
        ("regime gate off", meta.get("regime_gate") is False, f"gate={meta.get('regime_gate')}"),
        (
            "thresholds recorded",
            {"theta_high", "theta_low"} <= meta.keys(),
            f"theta_high={meta.get('theta_high')} theta_low={meta.get('theta_low')}",
        ),
        (
            "F5/F6 sections recorded",
            {"risk_guard", "capital_mgmt"} <= config.keys(),
            f"sections={sorted(config)}",
        ),
    ]


def main() -> int:
    """Print one line per check per run and return the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--cash", type=float, required=True, help="the --param cash the runs used")
    args = parser.parse_args()
    failed = False
    for run_dir in args.run_dirs:
        print(f"== {run_dir}")
        for name, passed, detail in _check(run_dir, args.cash):
            print(f"  [{'PASS' if passed else 'FAIL'}] {name}: {detail}")
            failed |= not passed
    print("QA:", "FAIL" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
