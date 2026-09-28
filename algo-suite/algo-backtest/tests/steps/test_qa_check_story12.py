"""Steps for qa_check_story12.feature — the story-12 QA gate script.

The script under test lives with the story's evidence
(docs/stories/in-progress/12-execution-realism/evidence/qa_check.py) and is loaded by path.
Every Given accumulates the artifacts of a synthetic run directory in `qa_ctx` from the
feature's tables; the When step writes them to tmp_path in the real artifact shapes
(run.json, strategy-config.{json,yaml}, strategy-provenance.json, trade-plans.json,
trades.json, main.json, statement.md, equity.png, equity.csv, report.html), applies the
scenario's deviations and runs the script's `main`, capturing its PASS/FAIL lines.
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import re
import shutil
import sys
from datetime import date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/qa_check_story12.feature")

_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "docs/stories/in-progress/12-execution-realism/evidence/qa_check.py"
)
_CHECK_LINE = re.compile(r"^\s+\[(PASS|FAIL)\] (.+?): (.*)$")
_FILTERS = [
    "f1_trend",
    "f2_indicator",
    "f3_pattern",
    "f5_risk_guard",
    "f6_capital_mgmt",
    "f7_meta_learner",
]
_REPORT = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Account Performance'
    "</title><style>body{background:#0f1419}</style></head><body><h1>Account Performance</h1>"
    '<svg viewBox="0 0 10 10"></svg></body></html>\n'
)
_PNG_HEADER = b"\x89PNG\r\n\x1a\n" + bytes(32)


def _load_script() -> ModuleType:
    """Import the QA script from its evidence path as a module."""
    spec = importlib.util.spec_from_file_location("qa_check_story12", _SCRIPT)
    assert spec is not None and spec.loader is not None, _SCRIPT
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve string annotations via sys.modules
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def qa_ctx(tmp_path: Path) -> dict[str, Any]:
    """Accumulated artifacts and deviations of one scenario's run directory."""
    return {
        "tmp": tmp_path,
        "run": {},
        "config": {"schema_version": 2, "filters": _FILTERS},
        "source": "default",
        "plans": [],
        "orders": {},
        "trades": [],
        "equity": [],
        "field_sets": [],
        "absent": [],
        "texts": {},
        "replaced": {},
        "second": None,
        "second_absent": None,
        "checks": {},
        "exit": None,
    }


# --- fixture assembly ------------------------------------------------------------------


def _json_cell(text: str) -> Any:
    """A table cell holding a JSON literal (numbers, strings, lists, null, booleans)."""
    return json.loads(text)


def _set_path(document: Any, path: str, value: Any) -> None:
    """Assign `value` at a dotted `path` (list indexes numeric, dict keys as written); a
    flat document keyed by dotted paths (strategy-provenance.json) is addressed directly."""
    if isinstance(document, dict) and path in document:
        document[path] = value
        return
    parts = path.split(".")
    target = document
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    last = parts[-1]
    if isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value


def _leaf_paths(document: dict[str, Any], prefix: str = "") -> list[str]:
    """Dotted paths of every parameter (a list counts as one), as the loader attributes them."""
    paths: list[str] = []
    for key, value in document.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            paths.extend(_leaf_paths(value, f"{path}."))
        else:
            paths.append(path)
    return paths


def _equity_csv(samples: list[tuple[str, float]]) -> str:
    """`equity.csv` text: time, equity, drawdown_pct from the running peak."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("time", "equity", "drawdown_pct"))
    peak = float("-inf")
    for moment, value in samples:
        peak = max(peak, value)
        writer.writerow((moment, value, (peak - value) / peak * 100.0))
    return buffer.getvalue()


def _main_json(qa_ctx: dict[str, Any]) -> dict[str, Any]:
    """LEAN's result JSON, minimal but shaped like the engine's (orders keyed by id)."""
    return {
        "totalPerformance": {"closedTrades": qa_ctx["trades"]},
        "orders": qa_ctx["orders"],
        "statistics": {"Start Equity": f"{qa_ctx['cash']:.2f}"},
    }


def _write_run_dir(qa_ctx: dict[str, Any], run_dir: Path) -> None:
    """Write every artifact the accumulated state describes into `run_dir`."""
    run_dir.mkdir(parents=True, exist_ok=True)
    config = qa_ctx["config"]
    documents: dict[str, Any] = {
        "run.json": {**qa_ctx["run"], "closed_trades": len(qa_ctx["trades"])},
        "strategy-config.json": config,
        "strategy-provenance.json": dict.fromkeys(_leaf_paths(config), qa_ctx["source"]),
        "trade-plans.json": qa_ctx["plans"],
        "trades.json": qa_ctx["trades"],
        "main.json": _main_json(qa_ctx),
    }
    for name, document in documents.items():
        (run_dir / name).write_text(json.dumps(document, indent=1))
    (run_dir / "strategy-config.yaml").write_text(yaml.safe_dump(config, sort_keys=True))
    (run_dir / "statement.md").write_text("# Account Statement\n")
    (run_dir / "equity.png").write_bytes(_PNG_HEADER)
    (run_dir / "report.html").write_text(_REPORT)
    (run_dir / "equity.csv").write_text(_equity_csv(qa_ctx["equity"]))


def _apply_field_set(run_dir: Path, artifact: str, path: str, value: Any) -> None:
    """Set one field of a written artifact; `strategy-config` edits the JSON and the YAML."""
    names = (
        ["strategy-config.json", "strategy-config.yaml"]
        if artifact == "strategy-config"
        else [artifact]
    )
    for name in names:
        file = run_dir / name
        if name.endswith(".yaml"):
            document = yaml.safe_load(file.read_text())
            _set_path(document, path, value)
            file.write_text(yaml.safe_dump(document, sort_keys=True))
        else:
            document = json.loads(file.read_text())
            _set_path(document, path, value)
            file.write_text(json.dumps(document, indent=1))


def _apply_deviations(qa_ctx: dict[str, Any], run_dir: Path) -> None:
    """Field sets, whole-document replacements, text overrides and removals, in that order."""
    for artifact, path, value in qa_ctx["field_sets"]:
        _apply_field_set(run_dir, artifact, path, value)
    for artifact, document in qa_ctx["replaced"].items():
        (run_dir / artifact).write_text(json.dumps(document))
    for artifact, text in qa_ctx["texts"].items():
        (run_dir / artifact).write_text(text)
    for artifact in qa_ctx["absent"]:
        (run_dir / artifact).unlink()


def _second_run_dir(qa_ctx: dict[str, Any], first: Path) -> Path:
    """A copy of the first run under another window: run.json and equity.csv times shifted."""
    run_id, start, end, absent = qa_ctx["second"]
    second = first.parent / run_id
    shutil.copytree(first, second)
    run = json.loads((second / "run.json").read_text())
    shift = date.fromisoformat(start) - date.fromisoformat(run["start"])
    run.update({"start": start, "end": end})
    (second / "run.json").write_text(json.dumps(run, indent=1))
    samples = [
        ((datetime.fromisoformat(moment) + shift).isoformat(), value)
        for moment, value in qa_ctx["equity"]
    ]
    (second / "equity.csv").write_text(_equity_csv(samples))
    if absent != "none":
        (second / absent).unlink()
    return second


def _run_script(
    qa_ctx: dict[str, Any], run_dirs: list[Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """Run the script's `main` over `run_dirs`, keeping the exit code and every check line."""
    qa_ctx["exit"] = _load_script().main([str(run_dir) for run_dir in run_dirs])
    for line in capsys.readouterr().out.splitlines():
        match = _CHECK_LINE.match(line)
        if match:
            qa_ctx["checks"][match.group(2)] = match.group(1)


# --- Given -----------------------------------------------------------------------------


@given(
    parsers.parse(
        'a finished run directory for strategy "{strategy}" on "{symbol}" from "{start}" to '
        '"{end}" with cash {cash:g}'
    )
)
def _run_manifest(
    qa_ctx: dict[str, Any], strategy: str, symbol: str, start: str, end: str, cash: float
) -> None:
    qa_ctx["cash"] = cash
    qa_ctx["run"] = {
        "strategy": strategy,
        "symbol": symbol,
        "start": start,
        "end": end,
        "params": {"cash": f"{cash:g}"},
        "success": True,
        "broker_adapter": "oanda",
    }


@given(parsers.parse('the resolved "{section}" section'))
def _section(qa_ctx: dict[str, Any], section: str, datatable: list[list[str]]) -> None:
    _header, *rows = datatable
    qa_ctx["config"][section] = {key: _json_cell(value) for key, value in rows}


@given(parsers.parse('every resolved parameter is attributed to "{source}"'))
def _provenance(qa_ctx: dict[str, Any], source: str) -> None:
    qa_ctx["source"] = source


@given("the equity samples")
def _equity(qa_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    _header, *rows = datatable
    qa_ctx["equity"] = [(moment, float(value)) for moment, value in rows]


@given("a planned trade")
def _plan(qa_ctx: dict[str, Any], datatable: list[list[str]]) -> None:
    _header, *rows = datatable
    qa_ctx["plans"].append({field: _json_cell(value) for field, value in rows})


@given(parsers.parse("LEAN booked order {order_id:d} for {units:g} units"))
def _booked(qa_ctx: dict[str, Any], order_id: int, units: float) -> None:
    qa_ctx["orders"][str(order_id)] = {"id": order_id, "quantity": units, "type": 0, "status": 3}


@given(
    parsers.parse(
        'the trade entered by order {entry:d} closed by order {exit_:d} at "{exit_time}" with '
        "profit {profit:g} and fees {fees:g}"
    )
)
def _closed(
    qa_ctx: dict[str, Any], entry: int, exit_: int, exit_time: str, profit: float, fees: float
) -> None:
    plan = next(p for p in qa_ctx["plans"] if p["entry_order_id"] == entry)
    qa_ctx["trades"].append(
        {
            "orderIds": [entry, exit_],
            "entryTime": plan["entry_time"] + "Z",
            "exitTime": exit_time,
            "entryPrice": plan["entry_price"],
            "exitPrice": plan["entry_price"],
            "quantity": abs(plan["quantity"]),
            "direction": 0 if plan["direction"] == "buy" else 1,
            "profitLoss": profit,
            "totalFees": fees,
            "isWin": profit > 0,
            "duration": "00:10:00",
        }
    )


@given(
    parsers.parse(
        'a second planned trade entered by order {entry:d} at "{entry_time}" and closed by order '
        '{exit_:d} at "{exit_time}"'
    )
)
def _second_plan(
    qa_ctx: dict[str, Any], entry: int, entry_time: str, exit_: int, exit_time: str
) -> None:
    plan = {**qa_ctx["plans"][0], "entry_order_id": entry, "entry_time": entry_time}
    qa_ctx["plans"].append(plan)
    qa_ctx["orders"][str(entry)] = {"id": entry, "quantity": plan["quantity"], "type": 0}
    if exit_time != "open":
        _closed(qa_ctx, entry, exit_, exit_time, 0.0, 0.0)


@given(parsers.parse('the artifact "{artifact}" field "{path}" is set to {value}'))
def _field_set(qa_ctx: dict[str, Any], artifact: str, path: str, value: str) -> None:
    qa_ctx["field_sets"].append((artifact, path, _json_cell(value)))


@given(parsers.parse('the artifact "{artifact}" is replaced by {document}'))
def _replaced(qa_ctx: dict[str, Any], artifact: str, document: str) -> None:
    qa_ctx["replaced"][artifact] = _json_cell(document)


@given(parsers.parse('the artifact "{artifact}" contains "{text}"'))
def _text(qa_ctx: dict[str, Any], artifact: str, text: str) -> None:
    qa_ctx["texts"][artifact] = text.replace("\\n", "\n")


@given(parsers.parse('the artifact "{artifact}" is absent'))
def _absent(qa_ctx: dict[str, Any], artifact: str) -> None:
    qa_ctx["absent"].append(artifact)


@given(
    parsers.parse('a second finished run "{run_id}" of the same strategy from "{start}" to "{end}"')
)
def _second_run(qa_ctx: dict[str, Any], run_id: str, start: str, end: str) -> None:
    qa_ctx["second"] = (run_id, start, end, "none")


@given(parsers.parse('the second run\'s artifact "{artifact}" is absent'))
def _second_absent(qa_ctx: dict[str, Any], artifact: str) -> None:
    run_id, start, end, _ = qa_ctx["second"]
    qa_ctx["second"] = (run_id, start, end, artifact)


# --- When ------------------------------------------------------------------------------


@when("I run the QA check on the run directory")
def _run_one(qa_ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    run_dir = qa_ctx["tmp"] / "runs" / "baseline" / "20260927T000000-deadbeef"
    _write_run_dir(qa_ctx, run_dir)
    _apply_deviations(qa_ctx, run_dir)
    _run_script(qa_ctx, [run_dir], capsys)


@when("I run the QA check on both run directories")
def _run_both(qa_ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    first = qa_ctx["tmp"] / "runs" / "baseline" / "20260927T000000-deadbeef"
    _write_run_dir(qa_ctx, first)
    _apply_deviations(qa_ctx, first)
    _run_script(qa_ctx, [first, _second_run_dir(qa_ctx, first)], capsys)


# --- Then ------------------------------------------------------------------------------


@then("every check reports PASS")
def _all_pass(qa_ctx: dict[str, Any]) -> None:
    failed = sorted(name for name, verdict in qa_ctx["checks"].items() if verdict != "PASS")
    assert qa_ctx["checks"], "the script printed no check lines"
    assert not failed, failed


@then(parsers.parse('check "{name}" reports {verdict}'))
def _check_reports(qa_ctx: dict[str, Any], name: str, verdict: str) -> None:
    assert name in qa_ctx["checks"], f"no check named {name!r}; got {sorted(qa_ctx['checks'])}"
    assert qa_ctx["checks"][name] == verdict, f"{name}: {qa_ctx['checks'][name]}"


@then(parsers.parse("the QA exit code is {code:d}"))
def _exit_code(qa_ctx: dict[str, Any], code: int) -> None:
    assert qa_ctx["exit"] == code
