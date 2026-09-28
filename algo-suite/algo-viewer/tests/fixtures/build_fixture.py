"""Build tests/fixtures/results.sqlite: one synthetic run through the real ingester.

Run from `algo-suite/`: `uv run python algo-viewer/tests/fixtures/build_fixture.py`. The
run's content lives in `fixture-run.json` next to this script; it is written with the
artifact shapes `algo-backtest` leaves on disk (see
algo-analyze/tests/features/results_db.feature) and ingested with entry bars ±2, so the
viewer's scenarios exercise the same database a real build produces.
"""

from __future__ import annotations

import csv
import json
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from algo_analyze.resultsdb import BuildRequest, RunsRoot, build_database
from algo_backtest.chain.audit import DecisionRow, FilterResultRow, write_decisions
from algo_core.bars import QuoteBar
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository

HERE = Path(__file__).resolve().parent
RUN_ID = "20260928T010000-fixture"
OUT = HERE / "results.sqlite"
LOG_PREFIX = "2026-09-28T02:28:11.1797446Z TRACE:: Debug: "


def _filter(spec: list[Any]) -> FilterResultRow:
    """`[name, recommendation, reason, veto, p_hat]` -> one audit-trail filter row."""
    name, recommendation, reason, veto, p_hat = spec
    return FilterResultRow(
        filter_name=name, recommendation=recommendation, reason=reason, confidence=None,
        veto=veto, enrichment=None if p_hat is None else {"p_hat": p_hat}, metadata=None,
    )


def _decisions(specs: list[Mapping[str, Any]]) -> list[DecisionRow]:
    """The fixture's decision rows in file order."""
    return [
        DecisionRow(
            trade_id=spec["trade_id"],
            timestamp=datetime.fromisoformat(spec["timestamp"]).replace(tzinfo=UTC),
            pair="EURUSD", features_hash=f"{i:064d}",
            filter_results=[_filter(f) for f in spec["filters"]],
            final_decision=spec["final_decision"], vetoed_by=spec["vetoed_by"],
        )
        for i, spec in enumerate(specs)
    ]


def _equity(run_dir: Path, samples: list[list[Any]]) -> None:
    """equity.csv with the drawdown column derived from the running peak."""
    peak = 0.0
    with (run_dir / "equity.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("time", "equity", "drawdown_pct"))
        for time, value in samples:
            peak = max(peak, float(value))
            writer.writerow((time, value, (peak - float(value)) / peak * 100.0))


def _m1(bars_root: Path, windows: list[Mapping[str, Any]]) -> None:
    """Gently rising M1 quotes over each window (bid, ask = bid + 2 pips)."""
    rows: list[QuoteBar] = []
    for w in windows:
        first = f"{w['day']}T{w['first_hour']:02d}:00:00"
        start = datetime.fromisoformat(first).replace(tzinfo=UTC)
        for i in range(int(w["hours"]) * 60):
            bid = float(w["base_bid"]) + 0.00001 * i
            ask = bid + 0.0002
            rows.append(QuoteBar(
                timestamp=start + timedelta(minutes=i), bid_open=bid, bid_high=bid + 0.00005,
                bid_low=bid - 0.00005, bid_close=bid, ask_open=ask, ask_high=ask + 0.00005,
                ask_low=ask - 0.00005, ask_close=ask, tick_count=10,
            ))
    path = price_path_for(bars_root, build_instrument("EURUSD"), "m1", 2016, 3)
    path.parent.mkdir(parents=True)
    ParquetRepository(QuoteBar, path).put(rows)


def write_run(run_dir: Path, spec: Mapping[str, Any]) -> None:
    """Every artifact of the fixture run, from the JSON spec."""
    run_dir.mkdir(parents=True)
    files = {
        "run.json": spec["run"], "metrics.json": spec["metrics"], "trades.json": spec["trades"],
        "trade-plans.json": spec["plans"], "main.json": {"orders": spec["orders"]},
        "strategy-provenance.json": spec["provenance"],
    }
    for name, document in files.items():
        (run_dir / name).write_text(json.dumps(document))
    (run_dir / "strategy-config.yaml").write_text(yaml.safe_dump(spec["config"]))
    (run_dir / "statement.md").write_text("\n".join(["# Account Statement", *spec.get("statement", [])]) + "\n")
    (run_dir / "log.txt").write_text("".join(f"{LOG_PREFIX}{line}\n" for line in spec["log"]))
    _equity(run_dir, spec["equity"])
    write_decisions(_decisions(spec["decisions"]), run_dir / "decisions.parquet")


def main() -> None:
    """Write the run, ingest it with ±2 entry bars, leave results.sqlite next to this file."""
    spec = json.loads((HERE / "fixture-run.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "fixture-job" / "data" / "runs"
        write_run(root / "hybrid" / RUN_ID, spec)
        _m1(Path(tmp) / "bars", spec["m1"])
        OUT.unlink(missing_ok=True)
        report = build_database(BuildRequest(
            roots=[RunsRoot(job="fixture-job", path=root)], out=OUT, bars_root=Path(tmp) / "bars",
            bars_before=2, bars_after=2,
        ))
    print(f"fixture: {len(report.ingested)} run(s) -> {OUT}")


if __name__ == "__main__":
    main()
