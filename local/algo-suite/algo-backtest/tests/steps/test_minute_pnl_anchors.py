"""Run the actual quote handler in native LEAN without data or order dependencies."""

import json
from collections.abc import Callable
from typing import Any

import pytest
from algo_backtest.lean_runner import LeanRun
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/minute_pnl_anchors.feature")

# Only the receiver's unrelated engine work is stubbed. Imports and the handler
# itself are real; this source executes inside the pinned LEAN container.
_PROBE = '''"""Data-free production on_data regression probe."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from AlgorithmImports import QCAlgorithm
from engine.chain_algorithm import ChainAlgorithm
from algo_backtest.chain.wiring import PnlWindows


class RecordingWindows(PnlWindows):
    """Record ordering while delegating all anchor arithmetic to production."""

    def __init__(self, events):
        """Share the receiver's event trace."""
        super().__init__()
        self.events = events
        self.latest = None

    def update(self, now, equity):
        """Observe a real update without replacing its behavior."""
        self.events.append([now.isoformat(), "pnl"])
        self.latest = super().update(now, equity)
        return self.latest


class Receiver:
    """Minimal receiver for the imported, unmodified production handler."""

    def __init__(self, midnight):
        """Expose only collaborators the early-return path may use."""
        self.events = []
        self._pnl = RecordingWindows(self.events)
        self._symbol = "EURUSD"
        self._trend_perception = None
        self.portfolio = SimpleNamespace(total_portfolio_value=12000.0)
        self.securities = {self._symbol: SimpleNamespace(price=1.0)}
        self.time = midnight - timedelta(minutes=1)
        self.final_time = midnight + timedelta(hours=4)

    def _closed_signal_bar(self, bar):
        """Model incomplete candles until the first 04:00 decision boundary."""
        self.events.append([self.time.isoformat(), "candle"])
        return self.time == self.final_time

    def _manage_open(self, price):
        """Observe minute-granularity position management without placing orders."""
        self.events.append([self.time.isoformat(), "manage"])

    def _indicators_ready(self):
        """Stop before unrelated chain work at the final complete candle."""
        self.events.append([self.time.isoformat(), "ready"])
        return False


def overnight(midnight):
    """Deliver every quote minute through production, including midnight."""
    receiver = Receiver(midnight)
    data = SimpleNamespace(quote_bars={receiver._symbol: object()})
    for minute in range(-1, 241):
        receiver.time = midnight + timedelta(minutes=minute)
        receiver.portfolio.total_portfolio_value = (
            12000.0 if minute < 0 else 10000.0 - 600.0 * minute / 240
        )
        ChainAlgorithm.on_data(receiver, data)
    result = {"events": receiver.events.copy(), "fractions": receiver._pnl.latest}
    result["repeat"] = receiver._pnl.update(receiver.time, 9400.0)
    return result


class main(QCAlgorithm):
    """Import real LEAN bindings and run isolated handler checks once."""

    def initialize(self):
        """Write measurements for host-side BDD assertions, without subscriptions."""
        self.set_start_date(2014, 5, 5)
        self.set_end_date(2014, 5, 6)
        self.set_cash(10000)
        observations = {
            "an ordinary day": overnight(datetime(2014, 5, 6)),
            "an ISO week": overnight(datetime(2014, 5, 5)),
            "an ISO week year": overnight(datetime(2014, 12, 29)),
        }
        receiver = Receiver(datetime(2014, 5, 6))
        ChainAlgorithm.on_data(receiver, SimpleNamespace(quote_bars={}))
        observations["missing"] = receiver.events
        Path("/Results/minute-pnl.json").write_text(json.dumps(observations))
        self.debug("MINUTE_PNL|DONE")
'''


@pytest.fixture(scope="module")
def pnl_probe(
    lean_backtest: Callable[..., LeanRun], tmp_path_factory: pytest.TempPathFactory
) -> dict[str, Any]:
    """Share one native run across all boundary examples; never fake AlgorithmImports."""
    root = tmp_path_factory.mktemp("minute-pnl")
    algo, results = root / "algo", root / "results"
    algo.mkdir()
    results.mkdir()
    (algo / "main.py").write_text(_PROBE)
    run = lean_backtest(algo_dir=algo, results_dir=results)
    assert run.exit_code == 0, run.logs[-12000:]
    assert "MINUTE_PNL|DONE" in run.logs, run.logs[-12000:]
    assert "ERROR::" not in run.logs, run.logs[-12000:]
    return dict(json.loads((results / "minute-pnl.json").read_text()))


@given("the native production quote handler and real PnL windows")
def native_handler(pnl_probe: dict[str, Any]) -> None:
    """Require successful execution inside LEAN before checking observations."""
    assert pnl_probe


@when(
    parsers.parse(
        "quote minutes cross {boundary} with midnight equity 10000 and 04:00 equity 9400"
    ),
    target_fixture="observation",
)
def boundary_observation(pnl_probe: dict[str, Any], boundary: str) -> dict[str, Any]:
    """Select the calendar boundary described by this scenario."""
    return dict(pnl_probe[boundary])


@then("every received quote updates PnL before checking candle completion")
def update_before_candle(observation: dict[str, Any]) -> None:
    """Require an update before every candle check, not just at the final boundary."""
    events = observation["events"]
    assert len(events) == 242 * 3 + 1
    for offset in range(0, 242 * 3, 3):
        update, candle, manage = events[offset : offset + 3]
        assert update[0] == candle[0] == manage[0]
        assert [update[1], candle[1], manage[1]] == ["pnl", "candle", "manage"]


@then("incomplete candles still manage the open position without evaluating the chain")
def incomplete_returns(observation: dict[str, Any]) -> None:
    """Only the complete final candle reaches the readiness guard."""
    events = observation["events"]
    assert sum(event[1] == "manage" for event in events) == 242
    assert [event for event in events if event[1] == "ready"] == [[events[-1][0], "ready"]]
    assert events[-1][0].endswith("T04:00:00")


@then(parsers.parse("the 04:00 daily PnL is -0.06 and weekly PnL is {weekly:g}"))
def loss_fractions(observation: dict[str, Any], weekly: float) -> None:
    """Pin the economic result independently of trace ordering."""
    assert observation["fractions"] == pytest.approx([-0.06, weekly])


@then("reading PnL again at 04:00 preserves both fractions")
def repeat_read(observation: dict[str, Any]) -> None:
    """Protect the repeated update retained by the production feature builder."""
    assert observation["repeat"] == observation["fractions"]


@when("a slice has no quote for the subscribed symbol")
def missing_quote(pnl_probe: dict[str, Any]) -> None:
    """Select the native empty-slice observation."""
    assert "missing" in pnl_probe


@then("no PnL update or candle or position work occurs")
def no_quote_work(pnl_probe: dict[str, Any]) -> None:
    """An unrelated slice must leave anchors and collaborators untouched."""
    assert pnl_probe["missing"] == []
