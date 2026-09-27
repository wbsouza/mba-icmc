"""Steps for run_baseline_chain.feature — the F1-F7 "baseline" chain wiring smoke test.

pytest-bdd binds step text per module, not globally across collected files, so the
handful of generic steps this feature shares with run_baseline.feature (CLI invocation,
exit-code/error assertions, swing-data materialization, artifact checks) are
self-contained here rather than cross-imported from test_run_baseline.py — same step
text, same behavior, kept independently importable. Only "bctx" and "require_docker"
are true fixtures (from conftest.py), not step functions, so no duplication there.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import algo_backtest
import pytest
import yaml
from algo_backtest.chain.audit import DecisionRow
from algo_backtest.cli import app
from algo_backtest.materialize import materialize_month
from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/run_baseline_chain.feature")

_EURUSD = build_instrument("EURUSD")


@pytest.fixture
def bctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Clean ALGO_ env + tmp data root (zero-config => UTC). No Docker (guard steps)."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    data_root = tmp_path / "data"
    monkeypatch.setenv("ALGO_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    monkeypatch.setenv("ALGO_BROKER__ADAPTER", "oanda")
    return {"data_root": data_root}


def _swing_bars(first: datetime, count: int = 60) -> list[QuoteBar]:
    """Triangular price swing (up then down), same shape as run_baseline.feature's fixture."""
    bars = []
    for i in range(count):
        offset = min(i, count - 1 - i)
        mid = 1.3800 + 0.0003 * offset
        bid = round(mid, 5)
        ask = round(mid + 0.0001, 5)
        bars.append(
            QuoteBar(
                timestamp=first + timedelta(minutes=i),
                bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid,
                ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask,
                tick_count=1,
            )
        )
    return bars


@when(parsers.parse('I run "{command}"'))
def _run_cli(bctx: dict[str, Any], command: str) -> None:
    bctx["cli"] = CliRunner().invoke(app, command.split()[1:])


@given("materialized EUR/USD minute data with a price swing in 2014-05")
def _materialize_swing(bctx: dict[str, Any]) -> None:
    bars = _swing_bars(datetime(2014, 5, 7, 13, 0, tzinfo=UTC))
    ParquetRepository(
        QuoteBar, price_path_for(bctx["data_root"], _EURUSD, Timeframe.M1.value, 2014, 5)
    ).put(bars)
    materialize_month(bctx["data_root"], _EURUSD, 2014, 5, ZoneInfo("UTC"))


@when(
    "I run baseline over the 2014-05-08 to 2014-05-09 test span with size 0.5, cash 10000 "
    "and that model"
)
def _run_baseline_chain(bctx: dict[str, Any], require_docker: None) -> None:
    bctx["cli"] = CliRunner().invoke(
        app,
        [
            "run", "--strategy", "baseline", "--symbol", "EURUSD",
            "--from", "2014-05-08", "--to", "2014-05-09", "--param", "size=0.5",
            "--param", "cash=10000",
            "--model", str(bctx["model"]),
        ],
    )


@given(
    parsers.parse(
        'an external strategies directory with "{name}" extending baseline with theta_high '
        "{high:g} and theta_low {low:g}"
    )
)
def _external_variant_dir(
    bctx: dict[str, Any], tmp_path: Path, name: str, high: float, low: float
) -> None:
    root = tmp_path / "strategies"
    (root / name).mkdir(parents=True)
    body = {"extends": "baseline", "meta_learner": {"theta_high": high, "theta_low": low}}
    (root / name / "config.yaml").write_text(yaml.safe_dump(body))
    bctx["strategies_root"] = root


@when(
    parsers.parse(
        "I run {name} from that directory over the 2014-05-08 to 2014-05-09 test span with "
        "size 0.5, cash 10000 and that model"
    )
)
def _run_external_variant(bctx: dict[str, Any], require_docker: None, name: str) -> None:
    bctx["cli"] = CliRunner().invoke(
        app,
        [
            "run", "--strategy", name, "--strategies-dir", str(bctx["strategies_root"]),
            "--symbol", "EURUSD", "--from", "2014-05-08", "--to", "2014-05-09",
            "--param", "size=0.5", "--param", "cash=10000", "--model", str(bctx["model"]),
        ],
    )


@then(
    parsers.parse(
        'the run\'s strategy-config.json under "{name}" records theta_high {high:g} and '
        "theta_low {low:g}"
    )
)
def _recorded_thresholds(bctx: dict[str, Any], name: str, high: float, low: float) -> None:
    configs = list((bctx["data_root"] / "runs" / name).glob("*/strategy-config.json"))
    assert configs, f"no strategy-config.json under runs/{name}"
    recorded = json.loads(configs[0].read_text())["meta_learner"]
    assert (recorded["theta_high"], recorded["theta_low"]) == (high, low)


@then(
    parsers.parse(
        'the run\'s strategy-provenance.json under "{name}" attributes "{key1}" to "{src1}" '
        'and "{key2}" to "{src2}"'
    )
)
def _recorded_provenance(
    bctx: dict[str, Any], name: str, key1: str, src1: str, key2: str, src2: str
) -> None:
    files = list((bctx["data_root"] / "runs" / name).glob("*/strategy-provenance.json"))
    assert files, f"no strategy-provenance.json under runs/{name}"
    provenance = json.loads(files[0].read_text())
    assert provenance[key1] == src1 and provenance[key2] == src2, provenance


@then(
    parsers.parse(
        'the bootstrap output lists strategy parameter "{key}" = {value} from "{source}"'
    )
)
def _bootstrap_parameter(bctx: dict[str, Any], key: str, value: str, source: str) -> None:
    expected = f"strategy[baseline] {key} = {value}  # {source}"
    assert expected in bctx["cli"].output.splitlines(), bctx["cli"].output


@then(parsers.parse("the run command exits with code {code:d}"))
def _exit_code(bctx: dict[str, Any], code: int) -> None:
    assert bctx["cli"].exit_code == code, bctx["cli"].output


@then("the strategy run exits successfully")
def _exit_ok(bctx: dict[str, Any]) -> None:
    assert bctx["cli"].exit_code == 0, bctx["cli"].output


@then("the error says cash must be positive")
def _cash_positive(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "cash" in out and "positive" in out


@then("the error says size must be in range")
def _size_range(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "size" in out and "(0, 1]" in out


@then("the error says params must be exactly")
def _params_must_be_exactly(bctx: dict[str, Any]) -> None:
    """Distinguishes a real `_check_keys` rejection from an unrelated failure (e.g. "no
    lean-data") that happens to also exit 2 -- both scenarios run against a fresh,
    unmaterialized data root, so exit code alone can't tell which check actually fired.
    """
    assert "params must be exactly" in bctx["cli"].output, bctx["cli"].output


@then("a metrics summary is reported")
def _metrics_reported(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "metrics:" in out and "total_return=" in out, out


@then("the run artifacts are written under the data root")
def _artifacts_written(bctx: dict[str, Any]) -> None:
    runs = bctx["data_root"] / "runs" / "baseline"
    assert list(runs.glob("*/run.json")), f"no run.json under {runs}"
    assert list(runs.glob("*/trades.json")), f"no trades.json under {runs}"
    assert list(runs.glob("*/metrics.json")), f"no metrics.json under {runs}"


@then("the container log shows the F1-F7 chain actually evaluated a decision")
def _chain_evaluated(bctx: dict[str, Any]) -> None:
    """Prove FilterChain.run() executed inside LEAN, not just that the CLI exited 0.

    CLI success + written artifacts can't distinguish "the chain ran" from "the chain
    was silently skipped" -- main.py logs one BASELINE_DECISION|... line (LEAN's own
    debug-message throttling collapses repeats, so at least one, not necessarily many)
    every time `on_data` reaches `self._chain.run(state)`. LEAN persists its container
    stdout as `log.txt` in the run's own results directory, so this reads that real
    file rather than needing a second, CLI-bypassing `run_lean()` call.
    """
    runs = bctx["data_root"] / "runs" / "baseline"
    logs = list(runs.glob("*/log.txt"))
    assert logs, f"no log.txt under {runs}"
    assert any("BASELINE_DECISION|" in log.read_text() for log in logs), (
        f"no BASELINE_DECISION line in {[str(p) for p in logs]} -- the chain never ran"
    )


def _run_dir(bctx: dict[str, Any]) -> Path:
    """The single run directory this scenario's CLI invocation just created."""
    data_root: Path = bctx["data_root"]
    runs = list((data_root / "runs" / "baseline").glob("*"))
    assert len(runs) == 1, f"expected exactly one baseline run dir, found {runs}"
    return runs[0]


@then("decisions.parquet is written under the run's results directory")
def _decisions_parquet_written(bctx: dict[str, Any]) -> None:
    assert (_run_dir(bctx) / "decisions.parquet").exists()


@then("at least one decisions.parquet row is joined to a trades.json trade")
def _decisions_join_nonempty(bctx: dict[str, Any]) -> None:
    """Without this, the join proof above passes vacuously when no trade ever filled."""
    run_dir = _run_dir(bctx)
    rows = ParquetRepository(DecisionRow, run_dir / "decisions.parquet").read_all()
    trades = json.loads((run_dir / "trades.json").read_text())
    closed_ids = {str(trade["orderIds"][0]) for trade in trades if trade.get("orderIds")}
    joined = [row for row in rows if row.trade_id in closed_ids]
    assert joined, (
        f"no decisions.parquet row joins a closed trades.json trade ({len(rows)} rows, "
        f"{len(trades)} closed trades) -- the join is unproven"
    )


@when("I run baseline with the bundled hybrid model as --model")
def _run_with_hybrid_model(bctx: dict[str, Any]) -> None:
    model = Path(algo_backtest.__file__).parent / "algos" / "hybrid" / "f7_meta_learner.json"
    bctx["cli"] = CliRunner().invoke(
        app,
        [
            "run", "--strategy", "baseline", "--symbol", "EURUSD", "--from", "2014-05-07",
            "--to", "2014-05-09", "--param", "size=0.5",
            "--param", "cash=10000", "--model", str(model),
        ],
    )


@then("the error names the model's families and the strategy's declared families")
def _families_error(bctx: dict[str, Any]) -> None:
    out = bctx["cli"].output
    assert "was trained on families" in out and "meta_learner.families" in out, out
