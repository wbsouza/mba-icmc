"""Steps for order_execution.feature — the order-execution engine against the real,
pinned LEAN container (Spec 04a). Uses the dedicated tests/algos/order_exec test
algorithm (parameterized Decision/size/stop-loss/adapter), not the price-driven
baselines, so each scenario controls exactly what OrderExecutor does.
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from algo_backtest.lean_runner import LeanRun, run_lean
from algo_backtest.materialize import materialize_month
from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import lean_data_dir_for, price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/order_execution.feature")

_EURUSD = build_instrument("EURUSD")
_ALGO_DIR = Path(__file__).parent.parent / "algos" / "order_exec"
_START = "20200102"
_END = "20200103"


@pytest.fixture
def octx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Clean ALGO_ env + tmp data root; default params any scenario can override."""
    for key in [k for k in os.environ if k.startswith("ALGO_")]:
        monkeypatch.delenv(key, raising=False)
    data_root = tmp_path / "data"
    monkeypatch.setenv("ALGO_DATA_ROOT", str(data_root))
    monkeypatch.setenv("ALGO_CONF_DIR", str(tmp_path / "conf"))
    return {
        "data_root": data_root,
        "params": {
            "start": _START, "end": _END, "broker_adapter": "oanda",
            "decision": "NO_TRADE", "size": "1.0",
        },
    }


def _flat_bars(first: datetime, count: int) -> list[QuoteBar]:
    bid, ask = 1.10000, 1.10010
    return [
        QuoteBar(
            timestamp=first + timedelta(minutes=i),
            bid_open=bid, bid_high=bid, bid_low=bid, bid_close=bid,
            ask_open=ask, ask_high=ask, ask_low=ask, ask_close=ask,
            tick_count=1,
        )
        for i in range(count)
    ]


@given("materialized EUR/USD minute data covering one trading day")
def _materialize_day(octx: dict[str, Any]) -> None:
    bars = _flat_bars(datetime(2020, 1, 2, 0, 0, tzinfo=UTC), 24 * 60)
    ParquetRepository(
        QuoteBar, price_path_for(octx["data_root"], _EURUSD, Timeframe.M1.value, 2020, 1)
    ).put(bars)
    materialize_month(octx["data_root"], _EURUSD, 2020, 1, __import__("zoneinfo").ZoneInfo("UTC"))


@given(parsers.parse("a strategy that emits one {decision} decision at a known bar"))
@given(parsers.parse("a strategy that emits {decision} at the current bar"))
def _decision(octx: dict[str, Any], decision: str) -> None:
    octx["params"]["decision"] = decision


@given("an open position from a prior BUY")
def _open_position(octx: dict[str, Any]) -> None:
    octx["params"]["open_position_first"] = "true"


@given("no open position")
def _no_open_position(octx: dict[str, Any]) -> None:
    pass  # default state — nothing to set


@given("a strategy that emits a BUY decision LEAN will reject for insufficient margin")
def _oversized_buy(octx: dict[str, Any]) -> None:
    octx["params"]["decision"] = "BUY"
    octx["params"]["size"] = "1000000"  # far beyond $100k cash's buying power


@given(parsers.parse("a strategy that emits {decision} with a computed stop distance"))
def _decision_with_stop(octx: dict[str, Any], decision: str) -> None:
    octx["params"]["decision"] = decision
    octx["params"]["stop_loss"] = "1.09500"
    octx["params"]["take_profit"] = "1.10500"


@given(parsers.parse('the strategy config selects the "{adapter}" brokerage adapter'))
def _select_adapter(octx: dict[str, Any], adapter: str) -> None:
    octx["params"]["broker_adapter"] = adapter
    octx["params"]["decision"] = "BUY"


@given("the strategy config names an unknown brokerage adapter")
def _unknown_adapter(octx: dict[str, Any]) -> None:
    octx["params"]["broker_adapter"] = "bogus"


def _run(octx: dict[str, Any], require_docker: None) -> LeanRun:
    results_dir = octx["data_root"] / "runs" / "order_exec"
    results_dir.mkdir(parents=True, exist_ok=True)
    subpath = lean_data_dir_for(octx["data_root"], _EURUSD, "minute").relative_to(
        octx["data_root"] / "lean-data"
    ).as_posix()
    run = run_lean(
        _ALGO_DIR, results_dir,
        data_mounts={subpath: lean_data_dir_for(octx["data_root"], _EURUSD, "minute")},
        parameters=octx["params"], timeout=600,
    )
    octx["run"] = run
    return run


@when("the backtest runs through the order-execution engine")
def _run_engine(octx: dict[str, Any], require_docker: None) -> None:
    _run(octx, require_docker)


@when("the backtest starts")
def _run_starts(octx: dict[str, Any], require_docker: None) -> None:
    _run(octx, require_docker)


@then("the backtest exits successfully")
def _exits_ok(octx: dict[str, Any]) -> None:
    run: LeanRun = octx["run"]
    assert run.exit_code == 0, run.logs


_CLOSED_RE = re.compile(r"ORDEREXEC_CLOSED_TRADES=(\d+)")
_FILL_RE = re.compile(
    r"ORDEREXEC_FILL\|decision=(?P<decision>\w+)\|status=(?P<status>\w+)\|"
    r"direction=(?P<direction>\w+)\|stop_loss=(?P<stop_loss>[\w.]+)\|"
    r"take_profit=(?P<take_profit>[\w.]+)\|reason=(?P<reason>.*)"
)


def _closed_trades(run: LeanRun) -> int:
    for line in run.grep("ORDEREXEC_CLOSED_TRADES="):
        match = _CLOSED_RE.search(line)
        if match:
            return int(match.group(1))
    raise AssertionError(f"no ORDEREXEC_CLOSED_TRADES line in logs:\n{run.logs}")


def _fill(run: LeanRun) -> dict[str, str]:
    for line in run.grep("ORDEREXEC_FILL|"):
        match = _FILL_RE.search(line)
        if match:
            return match.groupdict()
    raise AssertionError(f"no ORDEREXEC_FILL line in logs:\n{run.logs}")


@then(parsers.re(r"the run reports exactly (?P<n>\d+|one) closed trades?$"))
def _reports_closed(octx: dict[str, Any], n: str) -> None:
    assert _closed_trades(octx["run"]) == (1 if n == "one" else int(n))


@then("the run reports zero closed trades")
def _reports_zero(octx: dict[str, Any]) -> None:
    assert _closed_trades(octx["run"]) == 0


@then(parsers.parse('the recorded fill shows direction "{direction}"'))
def _fill_direction(octx: dict[str, Any], direction: str) -> None:
    fill = _fill(octx["run"])
    assert fill["status"] == "FILLED", fill
    assert fill["direction"] == direction, fill


@then("no new order is placed")
def _no_new_order(octx: dict[str, Any]) -> None:
    # The algo only executes once total (a guarded `_acted` flag); a second closed
    # trade would mean HOLD opened a new order instead of managing the existing one.
    assert _closed_trades(octx["run"]) == 0, octx["run"].logs


@then("the open position remains open at the end of the run")
def _position_open(octx: dict[str, Any]) -> None:
    assert "ORDEREXEC_INVESTED=True" in octx["run"].logs, octx["run"].logs


@then("the rejection is recorded in the run's audit trail")
def _rejection_recorded(octx: dict[str, Any]) -> None:
    fill = _fill(octx["run"])
    assert fill["status"] == "REJECTED", fill
    assert fill["reason"] not in ("None", ""), fill


@then("the recorded fill carries a stop-loss at the computed level")
def _stop_loss_set(octx: dict[str, Any]) -> None:
    fill = _fill(octx["run"])
    assert fill["status"] == "FILLED", fill
    assert float(fill["stop_loss"]) == float(octx["params"]["stop_loss"]), fill


@then("the recorded fill's risk parameters match the computed stop distance")
def _risk_params_match(octx: dict[str, Any]) -> None:
    fill = _fill(octx["run"])
    assert float(fill["stop_loss"]) == float(octx["params"]["stop_loss"]), fill
    assert float(fill["take_profit"]) == float(octx["params"]["take_profit"]), fill


@then("the run confirms the oanda brokerage model was applied")
def _brokerage_confirmed(octx: dict[str, Any]) -> None:
    assert "ORDEREXEC_BROKERAGE|adapter=oanda" in octx["run"].logs, octx["run"].logs


@then("the resulting fill is recorded normally under that model")
def _fill_recorded(octx: dict[str, Any]) -> None:
    fill = _fill(octx["run"])
    assert fill["status"] == "FILLED", fill


@then("it refuses to start before the first bar")
def _refuses_to_start(octx: dict[str, Any]) -> None:
    run: LeanRun = octx["run"]
    assert run.exit_code != 0, run.logs
    assert not run.grep("ORDEREXEC_FILL|"), "OnData ran despite the bad adapter"


@then("the error names the invalid adapter")
def _error_names_adapter(octx: dict[str, Any]) -> None:
    assert "bogus" in octx["run"].logs, octx["run"].logs
