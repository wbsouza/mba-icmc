"""Deterministic QA check for a finished story-12 (execution realism) run directory.

    uv run python docs/stories/in-progress/12-execution-realism/evidence/qa_check.py \\
        <run_dir> [<run_dir> ...] [--risk-tolerance 0.05] [--lot-step 1] [--pip-size 0.0001]

One ``[PASS]``/``[FAIL]`` line per check per run directory, a final ``QA: PASS|FAIL`` line,
exit code 0 when every check passed and 1 otherwise. The checks prove the machinery — every
trade plan traces to the resolved ``capital_mgmt``/``execution`` sections, every planned
entry to an order LEAN booked, every artifact present, auditable and self-contained — never
the strategy's economics (see qa-procedure.md).

Everything is read from the run directory's artifacts; nothing imports LEAN or re-runs the
engine: ``run.json`` (params.cash), ``strategy-config.json`` / ``strategy-config.yaml``,
``strategy-provenance.json``, ``trade-plans.json`` (``engine/trade_plan.py`` records),
``trades.json``, LEAN's result JSON (``orders``), ``statement.md``, ``equity.png``,
``equity.csv`` and ``report.html``. With two or more run directories the script also runs
``algo-analyze equity-curves`` over them into a temporary directory and checks that the
three ``equity-consolidated.*`` files appear.

Plan geometry (``chain/filters/f6_capital_mgmt.py``, ``rules/trail_stop.py``), all in pips
from the entry fill: stop = base × (1 − stop_loss_shrink), floored at max(min_stop_pips,
min_stop_factor × execution.broker_stop_level_pips) — for ``stop_distance_source: fixed`` the
base is ``stop_loss_pips`` so the distance is checked exactly, for ``atr``/``swing`` the base
is a bar feature the artifacts do not carry so only the floor is checked; target =
stop × at_level_ratio + (at_level_ratio + 1) × spread; trail arms at the same shape and moves
the stop to stop × to_level_ratio + spread. The pip size is derived from the quote precision
of the recorded fill prices (5 decimals → 0.0001) unless ``--pip-size`` is given.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

CONFIG_JSON = "strategy-config.json"
CONFIG_YAML = "strategy-config.yaml"
PROVENANCE_FILE = "strategy-provenance.json"
PLANS_FILE = "trade-plans.json"
TRADES_FILE = "trades.json"
RUN_FILE = "run.json"
EQUITY_CSV = "equity.csv"
REPORT_HTML = "report.html"
STATEMENT_FILES = ("statement.md", "equity.png", REPORT_HTML)
EQUITY_COLUMNS = ("time", "equity", "drawdown_pct")
CONSOLIDATED_FILES = (
    "equity-consolidated.csv",
    "equity-consolidated.png",
    "equity-consolidated.html",
)
FORBIDDEN_HTML = ("<script", "http://", "https://")
# Tolerance on a recorded price offset against the formula, in pips (LEAN rounds order
# prices to the instrument's tick, one tenth of a pip).
PRICE_TOLERANCE_PIPS = 0.01
# The pre-story-12 default plan: one full-size target at twice the stop distance.
DEFAULT_TARGETS: tuple[dict[str, float], ...] = ({"at_level_ratio": 2.0, "close_fraction": 1.0},)
# How many per-plan problems a FAIL line spells out before summarising the rest.
MAX_PROBLEMS_SHOWN = 3


@dataclass(frozen=True)
class Check:
    """One verdict: the check's name, whether it passed and the evidence behind it."""

    name: str
    passed: bool
    detail: str

    def line(self) -> str:
        """The console line for this check."""
        return f"  [{'PASS' if self.passed else 'FAIL'}] {self.name}: {self.detail}"


@dataclass(frozen=True)
class Options:
    """Command-line tolerances."""

    risk_tolerance: float
    lot_step: float
    pip_size: float | None


@dataclass(frozen=True)
class RunArtifacts:
    """The parsed artifacts of one run directory; ``None`` where a file is absent or broken."""

    run_dir: Path
    run: dict[str, Any] | None
    config: dict[str, Any] | None
    yaml_doc: Any
    yaml_present: bool
    provenance: dict[str, Any] | None
    plans: list[dict[str, Any]] | None
    trades: list[dict[str, Any]]
    result: dict[str, Any] | None


@dataclass(frozen=True)
class PlanRules:
    """What the resolved config says every plan must look like."""

    risk_per_trade: float
    pip_value_per_lot: float
    lot_notional_units: float
    floor_pips: float
    fixed_stop_pips: float | None
    source: str
    spread_pips: float
    targets: tuple[tuple[float, float], ...]
    trail_stops: tuple[tuple[float, float], ...]
    max_concurrent: int | None


PlanProblem = Callable[[dict[str, Any]], str | None]


# --- loading ---------------------------------------------------------------------------


def _json_file(path: Path) -> Any:
    """The parsed JSON document at ``path``, or ``None`` when absent or malformed."""
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _dict_or_none(document: Any) -> dict[str, Any] | None:
    """``document`` when it is a JSON object, else ``None``."""
    return document if isinstance(document, dict) else None


def _plan_list(document: Any) -> list[dict[str, Any]] | None:
    """``document`` when it is a JSON list of objects, else ``None``."""
    if isinstance(document, list) and all(isinstance(item, dict) for item in document):
        return document
    return None


def _find_result(run_dir: Path) -> dict[str, Any] | None:
    """LEAN's full result JSON: the ``*.json`` exposing ``totalPerformance.closedTrades``."""
    candidates = [run_dir / "main.json", *sorted(run_dir.glob("*.json"))]
    for path in candidates:
        if path.name.endswith(("-summary.json", "-order-events.json")):
            continue
        document = _dict_or_none(_json_file(path))
        if document is None:
            continue
        performance = document.get("totalPerformance")
        if isinstance(performance, dict) and "closedTrades" in performance:
            return document
    return None


def _yaml_file(path: Path) -> tuple[Any, bool]:
    """``(parsed document, present)`` for a YAML artifact; a broken file parses to ``None``."""
    if not path.is_file():
        return None, False
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")), True
    except yaml.YAMLError:
        return None, True


def load_artifacts(run_dir: Path) -> RunArtifacts:
    """Read every artifact the checks look at; absence is recorded, never raised."""
    yaml_doc, yaml_present = _yaml_file(run_dir / CONFIG_YAML)
    trades = _plan_list(_json_file(run_dir / TRADES_FILE))
    return RunArtifacts(
        run_dir=run_dir,
        run=_dict_or_none(_json_file(run_dir / RUN_FILE)),
        config=_dict_or_none(_json_file(run_dir / CONFIG_JSON)),
        yaml_doc=yaml_doc,
        yaml_present=yaml_present,
        provenance=_dict_or_none(_json_file(run_dir / PROVENANCE_FILE)),
        plans=_plan_list(_json_file(run_dir / PLANS_FILE)),
        trades=trades or [],
        result=_find_result(run_dir),
    )


# --- pure helpers ----------------------------------------------------------------------


def parse_time(text: str) -> datetime:
    """An ISO-8601 artifact timestamp (LEAN's trailing ``Z`` accepted) as an aware UTC time."""
    moment = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    return moment.astimezone(UTC) if moment.tzinfo else moment.replace(tzinfo=UTC)


def decimals_of(value: float) -> int:
    """How many significant decimals a recorded price carries (``1.13115`` → 5)."""
    text = repr(float(value))
    if "e" in text or "." not in text:
        return 0
    return len(text.split(".", 1)[1].rstrip("0"))


def derive_pip_size(prices: Sequence[float]) -> float | None:
    """The pip size from the quote precision of real fill prices: 10 × the finest tick
    (5 decimals → 0.0001, 3 → 0.01); ``None`` when no price carries two decimals."""
    decimals = max((decimals_of(price) for price in prices), default=0)
    return 10.0 ** (1 - decimals) if decimals >= 2 else None


def leaf_paths(document: Mapping[str, Any], prefix: str = "") -> Iterator[str]:
    """Dotted paths of every parameter in a nested mapping; a list is one parameter."""
    for key, value in document.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            yield from leaf_paths(value, f"{path}.")
        else:
            yield path


def plan_rules(config: Mapping[str, Any]) -> PlanRules | None:
    """The plan constraints the resolved config implies, ``None`` without ``capital_mgmt``."""
    capital = config.get("capital_mgmt")
    if not isinstance(capital, Mapping):
        return None
    execution = config.get("execution") or {}
    risk_guard = config.get("risk_guard") or {}
    broker_stop = float(execution.get("broker_stop_level_pips", 0.0))
    floor = max(
        float(capital.get("min_stop_pips", 0.0)),
        float(capital.get("min_stop_factor", 1.0)) * broker_stop,
    )
    source = str(capital.get("stop_distance_source", "fixed"))
    shrunk = float(capital["stop_loss_pips"]) * (1.0 - float(capital.get("stop_loss_shrink", 0.0)))
    cap = risk_guard.get("max_concurrent_trades_per_account")
    return PlanRules(
        risk_per_trade=float(capital["risk_per_trade"]),
        pip_value_per_lot=float(capital["pip_value_per_lot"]),
        lot_notional_units=float(capital["lot_notional_units"]),
        floor_pips=floor,
        fixed_stop_pips=max(floor, shrunk) if source == "fixed" else None,
        source=source,
        spread_pips=float(execution.get("spread_pips", 0.0)),
        targets=tuple(
            (float(t["at_level_ratio"]), float(t["close_fraction"]))
            for t in capital.get("targets", DEFAULT_TARGETS)
        ),
        trail_stops=tuple(
            (float(s["at_level_ratio"]), float(s["to_level_ratio"]))
            for s in capital.get("trail_stops", ())
        ),
        max_concurrent=int(cap) if isinstance(cap, int) and not isinstance(cap, bool) else None,
    )


def _sign(plan: Mapping[str, Any]) -> float:
    """+1 for a buy plan, −1 for a sell plan (the sign of a favourable price move)."""
    return 1.0 if plan["direction"] == "buy" else -1.0


def offset_pips(plan: Mapping[str, Any], price: float, pip: float) -> float:
    """``price`` as a signed distance from the plan's entry, in pips, positive in profit."""
    return _sign(plan) * (price - float(plan["entry_price"])) / pip


def stop_pips(plan: Mapping[str, Any], pip: float) -> float:
    """The plan's stop distance in pips (positive when the stop is on the losing side)."""
    return -offset_pips(plan, float(plan["stop_loss"]), pip)


def max_concurrent(intervals: Sequence[tuple[datetime, datetime | None]]) -> int:
    """The most intervals open at once; an interval without an end stays open forever."""
    events: list[tuple[datetime, int]] = []
    for start, end in intervals:
        events.append((start, 1))
        if end is not None:
            events.append((end, -1))
    # Sort closes before opens at the same instant: a plan entered as another exits is not
    # concurrent with it.
    events.sort(key=lambda event: (event[0], event[1]))
    peak = current = 0
    for _, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def balance_before(moment: datetime, cash: float, trades: Sequence[Mapping[str, Any]]) -> float:
    """Starting cash plus the net P/L of every trade closed at or before ``moment``."""
    realized = sum(
        float(trade["profitLoss"]) - float(trade.get("totalFees", 0.0))
        for trade in trades
        if parse_time(str(trade["exitTime"])) <= moment
    )
    return cash + realized


def _each_plan(name: str, plans: Sequence[dict[str, Any]], problem: PlanProblem, ok: str) -> Check:
    """Apply ``problem`` to every plan; FAIL listing the first problems, else PASS with ``ok``."""
    problems: list[str] = []
    for plan in plans:
        try:
            found = problem(plan)
        except (KeyError, TypeError, ValueError) as exc:
            found = f"order {plan.get('entry_order_id')!r}: malformed record ({exc!r})"
        if found is not None:
            problems.append(found)
    if problems:
        shown = "; ".join(problems[:MAX_PROBLEMS_SHOWN])
        rest = len(problems) - MAX_PROBLEMS_SHOWN
        return Check(name, False, shown + (f" (+{rest} more)" if rest > 0 else ""))
    return Check(name, True, f"{len(plans)} plan(s); {ok}")


# --- config and provenance checks ------------------------------------------------------


def check_config_present(artifacts: RunArtifacts) -> Check:
    """``strategy-config.json`` is a JSON object carrying the ``capital_mgmt`` section."""
    name = f"{CONFIG_JSON} present"
    if artifacts.config is None:
        return Check(name, False, f"{CONFIG_JSON} missing or not a JSON object")
    if plan_rules(artifacts.config) is None:
        return Check(name, False, f"{CONFIG_JSON} has no capital_mgmt section")
    return Check(name, True, f"sections={sorted(artifacts.config)}")


def check_config_yaml(artifacts: RunArtifacts) -> Check:
    """``strategy-config.yaml`` parses to exactly the document ``strategy-config.json`` holds."""
    name = f"{CONFIG_YAML} matches {CONFIG_JSON}"
    if not artifacts.yaml_present:
        return Check(name, False, f"{CONFIG_YAML} missing")
    if artifacts.config is None:
        return Check(name, False, f"{CONFIG_JSON} missing, nothing to compare against")
    if artifacts.yaml_doc != artifacts.config:
        return Check(name, False, "the YAML and JSON resolved configs differ")
    return Check(name, True, f"{len(list(leaf_paths(artifacts.config)))} parameters identical")


def _bad_source(source: Any) -> bool:
    """Whether a provenance value is neither ``default`` nor ``<name>/config.yaml``."""
    if not isinstance(source, str):
        return True
    if source == "default":
        return False
    name, sep, file = source.rpartition("/")
    return not (bool(sep) and bool(name) and "/" not in name and file == "config.yaml")


def check_provenance(artifacts: RunArtifacts) -> Check:
    """Every resolved parameter has a source, and each is ``<name>/config.yaml`` or ``default``."""
    name = "provenance sources are config.yaml or default"
    if artifacts.provenance is None:
        return Check(name, False, f"{PROVENANCE_FILE} missing or not a JSON object")
    bad = sorted(k for k, v in artifacts.provenance.items() if _bad_source(v))
    if bad:
        return Check(name, False, f"unexpected sources for {bad[:MAX_PROBLEMS_SHOWN]}")
    if artifacts.config is not None:
        unattributed = sorted(set(leaf_paths(artifacts.config)) - set(artifacts.provenance))
        if unattributed:
            return Check(name, False, f"parameters without a source: {unattributed[:3]}")
    sources = sorted(set(artifacts.provenance.values()))
    return Check(name, True, f"{len(artifacts.provenance)} parameters from {sources}")


# --- trade-plan checks -----------------------------------------------------------------


def check_plans_present(artifacts: RunArtifacts) -> Check:
    """``trade-plans.json`` is a JSON list of plan records (empty for a run without entries)."""
    name = f"{PLANS_FILE} present"
    if artifacts.plans is None:
        return Check(name, False, f"{PLANS_FILE} missing or not a JSON list of records")
    return Check(name, True, f"{len(artifacts.plans)} record(s)")


def _stop_problem(plan: dict[str, Any], rules: PlanRules, pip: float) -> str | None:
    """The stop is on the losing side, at or above the floor, and exact for a fixed source."""
    order, distance = plan["entry_order_id"], stop_pips(plan, pip)
    if distance <= 0:
        return f"order {order}: stop {plan['stop_loss']} is not on the losing side of entry"
    if distance < rules.floor_pips - PRICE_TOLERANCE_PIPS:
        return f"order {order}: stop {distance:.2f} pips below the floor {rules.floor_pips:g}"
    if rules.fixed_stop_pips is not None and (
        abs(distance - rules.fixed_stop_pips) > PRICE_TOLERANCE_PIPS
    ):
        return (
            f"order {order}: stop {distance:.2f} pips, fixed rule gives {rules.fixed_stop_pips:g}"
        )
    return None


def _targets_problem(plan: dict[str, Any], rules: PlanRules, pip: float) -> str | None:
    """Target count, close fractions, price offsets and exit quantities follow the config."""
    order, targets = plan["entry_order_id"], plan["take_profits"]
    if len(targets) != len(rules.targets):
        return f"order {order}: {len(targets)} take-profit(s), config has {len(rules.targets)}"
    distance = stop_pips(plan, pip)
    for index, (target, (ratio, fraction)) in enumerate(zip(targets, rules.targets, strict=True)):
        expected = distance * ratio + (ratio + 1.0) * rules.spread_pips
        actual = offset_pips(plan, float(target["price"]), pip)
        if abs(actual - expected) > PRICE_TOLERANCE_PIPS:
            return f"order {order}: target[{index}] at {actual:.2f} pips, formula {expected:.2f}"
        if abs(float(target["close_fraction"]) - fraction) > 1e-9:
            return (
                f"order {order}: target[{index}] closes {target['close_fraction']}, not {fraction}"
            )
    closed = sum(abs(float(target["quantity"])) for target in targets)
    if closed > abs(float(plan["quantity"])) + 1e-6:
        return f"order {order}: targets close {closed:g} units of a {plan['quantity']} position"
    return None


def _trail_problem(plan: dict[str, Any], rules: PlanRules, pip: float) -> str | None:
    """Trail step count and the arming/destination prices follow the config."""
    order, steps = plan["entry_order_id"], plan["trail_stops"]
    if len(steps) != len(rules.trail_stops):
        return f"order {order}: {len(steps)} trail step(s), config has {len(rules.trail_stops)}"
    distance = stop_pips(plan, pip)
    for index, (step, (at_ratio, to_ratio)) in enumerate(
        zip(steps, rules.trail_stops, strict=True)
    ):
        at_expected = distance * at_ratio + (at_ratio + 1.0) * rules.spread_pips
        to_expected = distance * to_ratio + rules.spread_pips
        at_actual = offset_pips(plan, float(step["at_price"]), pip)
        to_actual = offset_pips(plan, float(step["to_price"]), pip)
        if abs(at_actual - at_expected) > PRICE_TOLERANCE_PIPS:
            return (
                f"order {order}: trail[{index}] arms at {at_actual:.2f} pips, not {at_expected:.2f}"
            )
        if abs(to_actual - to_expected) > PRICE_TOLERANCE_PIPS:
            return f"order {order}: trail[{index}] moves to {to_actual:.2f}, not {to_expected:.2f}"
    return None


def _spread_problem(plan: dict[str, Any], rules: PlanRules) -> str | None:
    """The plan's recorded spread is the ``execution.spread_pips`` the run resolved."""
    if abs(float(plan["spread_pips"]) - rules.spread_pips) > 1e-9:
        return (
            f"order {plan['entry_order_id']}: spread {plan['spread_pips']} pips, "
            f"execution.spread_pips {rules.spread_pips:g}"
        )
    return None


def _join_problem(plan: dict[str, Any], orders: Mapping[str, Any], lot_step: float) -> str | None:
    """The entry order exists in LEAN's result with the plan's quantity."""
    order_id = plan["entry_order_id"]
    order = orders.get(str(order_id))
    if not isinstance(order, Mapping):
        return f"order {order_id}: not in the LEAN result's orders"
    booked, planned = abs(float(order["quantity"])), abs(float(plan["quantity"]))
    if abs(booked - planned) > lot_step - 1e-9:
        return f"order {order_id}: LEAN booked {booked:g} units, plan records {planned:g}"
    return None


def _lots_problem(plan: dict[str, Any], rules: PlanRules, lot_step: float) -> str | None:
    """lots × lot_notional_units is the position size (snapped down by at most one lot step)
    and the quantity's sign is the plan's direction."""
    order, quantity = plan["entry_order_id"], float(plan["quantity"])
    if quantity == 0 or (quantity > 0) != (plan["direction"] == "buy"):
        return f"order {order}: quantity {quantity:g} contradicts direction {plan['direction']!r}"
    notional = float(plan["lots"]) * rules.lot_notional_units
    difference = notional - abs(quantity)
    if difference < -1e-6 or difference >= lot_step:
        return f"order {order}: {plan['lots']} lots = {notional:g} units, quantity {quantity:g}"
    return None


def _risk_problem(
    plan: dict[str, Any],
    rules: PlanRules,
    pip: float,
    cash: float,
    trades: Sequence[dict[str, Any]],
    tolerance: float,
) -> str | None:
    """lots × stop pips × pip value stays within risk_per_trade of the balance at entry."""
    risk = float(plan["lots"]) * stop_pips(plan, pip) * rules.pip_value_per_lot
    balance = balance_before(parse_time(str(plan["entry_time"])), cash, trades)
    budget = rules.risk_per_trade * balance
    if risk > budget * (1.0 + tolerance) + 1e-9:
        return (
            f"order {plan['entry_order_id']}: risks {risk:.2f} against a budget of "
            f"{budget:.2f} ({rules.risk_per_trade:g} × balance {balance:.2f})"
        )
    return None


def _cash(artifacts: RunArtifacts) -> float | None:
    """The run's ``--param cash`` from ``run.json``, ``None`` when unrecorded."""
    params = (artifacts.run or {}).get("params")
    if not isinstance(params, Mapping) or "cash" not in params:
        return None
    try:
        return float(params["cash"])
    except (TypeError, ValueError):
        return None


def _fill_prices(artifacts: RunArtifacts) -> list[float]:
    """Every recorded fill price: plan entries and the ledger's entry/exit prices."""
    prices = [float(plan["entry_price"]) for plan in artifacts.plans or () if "entry_price" in plan]
    for trade in artifacts.trades:
        prices.extend(float(trade[key]) for key in ("entryPrice", "exitPrice") if key in trade)
    return prices


def _concurrency_check(
    plans: Sequence[dict[str, Any]], trades: Sequence[dict[str, Any]], rules: PlanRules
) -> Check:
    """Open planned positions never exceed ``risk_guard.max_concurrent_trades_per_account``."""
    name = "concurrent positions within risk_guard cap"
    exits = {
        int(trade["orderIds"][0]): parse_time(str(trade["exitTime"]))
        for trade in trades
        if trade.get("orderIds")
    }
    intervals = [
        (parse_time(str(plan["entry_time"])), exits.get(int(plan["entry_order_id"])))
        for plan in plans
    ]
    peak = max_concurrent(intervals)
    if rules.max_concurrent is None:
        return Check(name, True, f"peak {peak} open position(s); no cap configured")
    if peak > rules.max_concurrent:
        return Check(name, False, f"peak {peak} open position(s), cap {rules.max_concurrent}")
    return Check(name, True, f"peak {peak} open position(s), cap {rules.max_concurrent}")


def _plan_checks(artifacts: RunArtifacts, rules: PlanRules, options: Options) -> list[Check]:
    """The per-plan checks, once the plans, config and pip size are all available."""
    plans = artifacts.plans or []
    pip = options.pip_size or derive_pip_size(_fill_prices(artifacts))
    if pip is None and plans:
        return [Check("pip size", False, "no fill price fixes the precision; pass --pip-size")]
    pip = pip or 1.0  # unused without plans
    orders = (artifacts.result or {}).get("orders") or {}
    cash = _cash(artifacts)
    stop_ok = f"source={rules.source}, floor {rules.floor_pips:g} pips" + (
        f", fixed stop {rules.fixed_stop_pips:g} pips" if rules.fixed_stop_pips is not None else ""
    )
    checks = [
        _each_plan(
            "plan stop distance within capital_mgmt bounds",
            plans,
            lambda p: _stop_problem(p, rules, pip),
            stop_ok,
        ),
        _each_plan(
            "plan targets match capital_mgmt.targets",
            plans,
            lambda p: _targets_problem(p, rules, pip),
            f"{len(rules.targets)} target(s) each",
        ),
        _each_plan(
            "plan trail steps match capital_mgmt.trail_stops",
            plans,
            lambda p: _trail_problem(p, rules, pip),
            f"{len(rules.trail_stops)} step(s) each",
        ),
        _each_plan(
            "plan spread equals execution.spread_pips",
            plans,
            lambda p: _spread_problem(p, rules),
            f"{rules.spread_pips:g} pips",
        ),
        _each_plan(
            "plan entry orders join the LEAN result",
            plans,
            lambda p: _join_problem(p, orders, options.lot_step),
            f"{len(orders)} orders booked",
        ),
        _each_plan(
            "plan lots match quantity",
            plans,
            lambda p: _lots_problem(p, rules, options.lot_step),
            f"lot = {rules.lot_notional_units:g} units",
        ),
    ]
    if cash is None:
        checks.append(
            Check("position risk within risk_per_trade", False, "run.json has no params.cash")
        )
    else:
        checks.append(
            _each_plan(
                "position risk within risk_per_trade",
                plans,
                lambda p: _risk_problem(
                    p, rules, pip, cash, artifacts.trades, options.risk_tolerance
                ),
                f"risk_per_trade {rules.risk_per_trade:g} of the balance at entry, "
                f"tolerance {options.risk_tolerance:g}",
            )
        )
    checks.append(_concurrency_check(plans, artifacts.trades, rules))
    return checks


# --- statement, equity and report checks -----------------------------------------------


def check_statement_files(run_dir: Path) -> list[Check]:
    """``statement.md``, ``equity.png`` and ``report.html`` exist and are not empty."""
    checks = []
    for name in STATEMENT_FILES:
        path = run_dir / name
        present = path.is_file() and path.stat().st_size > 0
        detail = f"{path.stat().st_size} bytes" if present else "missing or empty"
        checks.append(Check(f"{name} present", present, detail))
    return checks


def _equity_rows(path: Path) -> list[list[str]]:
    """The CSV rows of ``equity.csv`` (empty when the file is absent)."""
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.reader(handle))


def check_equity_csv(artifacts: RunArtifacts) -> Check:
    """``equity.csv`` has the ``time,equity,drawdown_pct`` header and opens at the cash."""
    name = f"{EQUITY_CSV} starts at cash"
    rows = _equity_rows(artifacts.run_dir / EQUITY_CSV)
    if not rows:
        return Check(name, False, f"{EQUITY_CSV} missing or empty")
    if tuple(rows[0]) != EQUITY_COLUMNS:
        return Check(name, False, f"header {rows[0]!r}, expected {list(EQUITY_COLUMNS)!r}")
    if len(rows) < 2:
        return Check(name, False, "no equity samples")
    cash = _cash(artifacts)
    if cash is None:
        return Check(name, False, "run.json has no params.cash to compare against")
    try:
        first = float(rows[1][1])
    except (IndexError, ValueError):
        return Check(name, False, f"first row {rows[1]!r} has no numeric equity")
    if abs(first - cash) > 0.005:
        return Check(name, False, f"first equity {first:.2f}, cash {cash:.2f}")
    return Check(name, True, f"{len(rows) - 1} samples, first equity {first:.2f} == cash")


def check_report_self_contained(run_dir: Path) -> Check:
    """``report.html`` carries no script and no external resource reference."""
    name = f"{REPORT_HTML} self-contained"
    path = run_dir / REPORT_HTML
    if not path.is_file():
        return Check(name, False, f"{REPORT_HTML} missing")
    text = path.read_text(encoding="utf-8").lower()
    found = [token for token in FORBIDDEN_HTML if token in text]
    if found:
        return Check(name, False, f"contains {found}")
    return Check(name, True, f"{len(text)} chars, no script, no http(s) reference")


# --- multi-run check -------------------------------------------------------------------


def _analyze_command() -> str | None:
    """The ``algo-analyze`` console script of the active environment, if installed."""
    found = shutil.which("algo-analyze")
    if found:
        return found
    sibling = Path(sys.executable).with_name("algo-analyze")
    return str(sibling) if sibling.is_file() else None


def check_equity_curves(run_dirs: Sequence[Path], out_dir: Path) -> Check:
    """``algo-analyze equity-curves`` over the runs writes the three consolidated files."""
    name = "equity-curves consolidates the runs"
    command = _analyze_command()
    if command is None:
        return Check(name, False, "algo-analyze is not installed in this environment")
    argv = [command, "equity-curves", "--out", str(out_dir)]
    for run_dir in run_dirs:
        argv.extend(["--run", str(run_dir)])
    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout).strip().splitlines()[-1:]
        return Check(name, False, f"exit {completed.returncode}: {' '.join(tail)}")
    missing = [f for f in CONSOLIDATED_FILES if not (out_dir / f).is_file()]
    if missing:
        return Check(name, False, f"not written: {missing}")
    return Check(name, True, f"{len(run_dirs)} runs -> {out_dir}: {list(CONSOLIDATED_FILES)}")


# --- driver ----------------------------------------------------------------------------


def check_run(run_dir: Path, options: Options) -> list[Check]:
    """Every check for one run directory, in report order."""
    artifacts = load_artifacts(run_dir)
    checks = [
        check_config_present(artifacts),
        check_config_yaml(artifacts),
        check_provenance(artifacts),
        check_plans_present(artifacts),
    ]
    rules = plan_rules(artifacts.config) if artifacts.config is not None else None
    if rules is None:
        checks.append(
            Check("plan checks", False, "no resolved capital_mgmt to check plans against")
        )
    elif artifacts.plans is None:
        checks.append(Check("plan checks", False, f"{PLANS_FILE} missing; plan checks skipped"))
    else:
        checks.extend(_plan_checks(artifacts, rules, options))
    checks.extend(check_statement_files(run_dir))
    checks.append(check_equity_csv(artifacts))
    checks.append(check_report_self_contained(run_dir))
    return checks


def run_qa(run_dirs: Sequence[Path], options: Options, analyze_out: Path | None) -> bool:
    """Print every check for every run (and the multi-run check); ``True`` when all passed."""
    all_passed = True
    for run_dir in run_dirs:
        print(f"== {run_dir}")
        for check in check_run(run_dir, options):
            print(check.line())
            all_passed &= check.passed
    if len(run_dirs) >= 2:
        print("== consolidated")
        check = _consolidated(run_dirs, analyze_out)
        print(check.line())
        all_passed &= check.passed
    print("QA:", "PASS" if all_passed else "FAIL")
    return all_passed


def _consolidated(run_dirs: Sequence[Path], analyze_out: Path | None) -> Check:
    """The equity-curves check into ``analyze_out`` or a temporary directory."""
    if analyze_out is not None:
        analyze_out.mkdir(parents=True, exist_ok=True)
        return check_equity_curves(run_dirs, analyze_out)
    with tempfile.TemporaryDirectory(prefix="qa-equity-curves-") as scratch:
        return check_equity_curves(run_dirs, Path(scratch))


def build_parser() -> argparse.ArgumentParser:
    """The command-line interface."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    parser.add_argument("run_dirs", nargs="+", type=Path, help="finished run directories")
    parser.add_argument(
        "--risk-tolerance",
        type=float,
        default=0.05,
        help="relative slack on risk_per_trade × balance (default 0.05)",
    )
    parser.add_argument(
        "--lot-step",
        type=float,
        default=1.0,
        help="the broker's order-size step in units (OANDA 1; default 1)",
    )
    parser.add_argument(
        "--pip-size",
        type=float,
        default=None,
        help="pip size in price units (default: derived from the recorded fill prices)",
    )
    parser.add_argument(
        "--analyze-out",
        type=Path,
        default=None,
        help="keep the equity-curves output here instead of a temporary directory",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the arguments, run the checks and return the process exit code (0 = PASS)."""
    args = build_parser().parse_args(argv)
    options = Options(
        risk_tolerance=args.risk_tolerance, lot_step=args.lot_step, pip_size=args.pip_size
    )
    return 0 if run_qa(list(args.run_dirs), options, args.analyze_out) else 1


if __name__ == "__main__":
    sys.exit(main())
