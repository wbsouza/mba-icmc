"""Steps for equity_curves.feature — the consolidated multi-run equity overlay.

Run directories are assembled in tmp_path from a hand-written run.json and equity.csv
(the artifact `algo-backtest statement --run` writes). Equity values given in a step are
sampled at successive UTC midnights from the run's start date.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from algo_analyze.cli import app
from algo_analyze.equity import (
    Consolidation,
    CurvePoint,
    chart_title,
    consolidate,
    load_run_equity,
    parse_labels,
    summary_line,
    write_consolidated,
)
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

scenarios("../features/equity_curves.feature")


@pytest.fixture
def ectx(tmp_path: Path) -> dict[str, Any]:
    """Accumulated fixture state: run directories, labels, results."""
    return {"runs": {}, "labels": [], "tmp": tmp_path}


def _floats(text: str) -> list[float]:
    """A comma-separated list of numbers -> floats."""
    return [float(v) for v in text.split(",")]


def _write_run(
    ectx: dict[str, Any], run_id: str, strategy: str, start: str, end: str, values: list[float]
) -> Path:
    """Write run.json + equity.csv (midnight samples from `start`) for one run directory."""
    run_dir: Path = ectx["tmp"] / "runs" / strategy / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps({
        "strategy": strategy, "symbol": "EURUSD", "start": start, "end": end, "params": {},
        "success": True, "closed_trades": 0,
    }))
    first = datetime.fromisoformat(start).replace(tzinfo=UTC)
    peak, lines = float("-inf"), ["time,equity,drawdown_pct"]
    for i, value in enumerate(values):
        peak = max(peak, value)
        dd = (peak - value) / peak * 100.0
        lines.append(f"{(first + timedelta(days=i)).isoformat()},{value},{dd}")
    (run_dir / "equity.csv").write_text("\n".join(lines) + "\n")
    ectx["runs"][run_id] = run_dir
    return run_dir


# --- Given -----------------------------------------------------------------------------


@given("an output directory for the consolidated curves")
def _out_dir(ectx: dict[str, Any]) -> None:
    ectx["out"] = ectx["tmp"] / "analysis" / "curves"


@given(
    parsers.parse(
        'a run "{run_id}" of strategy "{strategy}" from "{start}" to "{end}" with equity {values}'
    )
)
def _run(
    ectx: dict[str, Any], run_id: str, strategy: str, start: str, end: str, values: str
) -> None:
    _write_run(ectx, run_id, strategy, start, end, _floats(values))


@given(
    parsers.parse(
        'a run "{run_id}" of strategy "{strategy}" from "{start}" to "{end}" with no equity '
        "samples"
    )
)
def _empty_run(ectx: dict[str, Any], run_id: str, strategy: str, start: str, end: str) -> None:
    _write_run(ectx, run_id, strategy, start, end, [])


@given(parsers.parse('the run "{run_id}" lacks "{artifact}"'))
def _lacks(ectx: dict[str, Any], run_id: str, artifact: str) -> None:
    (ectx["runs"][run_id] / artifact).unlink()


@given(parsers.parse('the run "{run_id}" equity.csv header is "{header}"'))
def _foreign_header(ectx: dict[str, Any], run_id: str, header: str) -> None:
    path = ectx["runs"][run_id] / "equity.csv"
    _old, *rows = path.read_text().splitlines()
    path.write_text("\n".join([header, *rows]) + "\n")


@given(parsers.parse('the label "{label}"'))
def _label(ectx: dict[str, Any], label: str) -> None:
    ectx["labels"].append(label)


# --- When ------------------------------------------------------------------------------


def _run_dirs(ectx: dict[str, Any]) -> list[Path]:
    """The run directories in the order the Given steps declared them."""
    return list(ectx["runs"].values())


@when("I consolidate the runs")
def _consolidate(ectx: dict[str, Any]) -> None:
    consolidation, paths = write_consolidated(_run_dirs(ectx), ectx["labels"], ectx["out"])
    ectx["consolidation"], ectx["paths"] = consolidation, paths
    # The pure path must agree with the orchestrated one.
    runs = [load_run_equity(d) for d in _run_dirs(ectx)]
    assert consolidate(runs, parse_labels(ectx["labels"])) == consolidation


@when("I consolidate the runs expecting failure")
def _consolidate_failing(ectx: dict[str, Any]) -> None:
    with pytest.raises((FileNotFoundError, ValueError)) as exc_info:
        write_consolidated(_run_dirs(ectx), ectx["labels"], ectx["out"])
    ectx["error"] = str(exc_info.value)


@when("I run the equity-curves command on those runs")
def _run_cli(ectx: dict[str, Any]) -> None:
    args = ["equity-curves", "--out", str(ectx["out"])]
    for run_dir in _run_dirs(ectx):
        args += ["--run", str(run_dir)]
    ectx["cli"] = CliRunner().invoke(app, args)


# --- Then ------------------------------------------------------------------------------


def _points_of(ectx: dict[str, Any], run_id: str) -> list[CurvePoint]:
    consolidation: Consolidation = ectx["consolidation"]
    return [p for p in consolidation.points if p.run_id == run_id]


def _csv_rows(ectx: dict[str, Any]) -> list[dict[str, str]]:
    with ectx["paths"].csv.open(newline="") as handle:
        return list(csv.DictReader(handle))


@then(parsers.parse("the consolidated rows list the runs in the order {order}"))
def _run_order(ectx: dict[str, Any], order: str) -> None:
    consolidation: Consolidation = ectx["consolidation"]
    seen: list[str] = []
    for point in consolidation.points:
        if point.run_id not in seen:
            seen.append(point.run_id)
    assert seen == [r.strip() for r in order.split(",")]


@then(parsers.parse("the strategies in the summary are {names}"))
def _summary_strategies(ectx: dict[str, Any], names: str) -> None:
    consolidation: Consolidation = ectx["consolidation"]
    assert [s.strategy for s in consolidation.summaries] == [n.strip() for n in names.split(",")]


@then(parsers.parse('the chained equity of run "{run_id}" is {values}'))
def _chained(ectx: dict[str, Any], run_id: str, values: str) -> None:
    got = [p.equity_chained for p in _points_of(ectx, run_id)]
    assert got == pytest.approx(_floats(values)), got


@then(parsers.parse('the raw equity of run "{run_id}" is still {values}'))
def _raw(ectx: dict[str, Any], run_id: str, values: str) -> None:
    got = [p.equity_raw for p in _points_of(ectx, run_id)]
    assert got == pytest.approx(_floats(values)), got


@then(parsers.parse('the drawdown percent of run "{run_id}" is {values}'))
def _drawdown(ectx: dict[str, Any], run_id: str, values: str) -> None:
    got = [p.drawdown_pct for p in _points_of(ectx, run_id)]
    assert got == pytest.approx(_floats(values)), got


@then(
    parsers.parse(
        'the curve summary for "{strategy}" is first {first:g}, last {last:g}, net {net:g} '
        "percent, max drawdown {max_dd:g} percent"
    )
)
def _curve_summary(
    ectx: dict[str, Any], strategy: str, first: float, last: float, net: float, max_dd: float
) -> None:
    consolidation: Consolidation = ectx["consolidation"]
    summary = next(s for s in consolidation.summaries if s.strategy == strategy)
    assert summary.first_equity == pytest.approx(first)
    assert summary.last_equity == pytest.approx(last)
    assert summary.net_pct == pytest.approx(net)
    assert summary.max_drawdown_pct == pytest.approx(max_dd)


@then("the consolidated CSV rows are")
def _csv_rows_are(ectx: dict[str, Any], datatable: list[list[str]]) -> None:
    header, *rows = datatable
    got = _csv_rows(ectx)
    assert list(got[0]) == header
    assert len(got) == len(rows)
    for expected, actual in zip(rows, got, strict=True):
        cells = dict(zip(header, expected, strict=True))
        assert actual["strategy"] == cells["strategy"] and actual["run_id"] == cells["run_id"]
        assert actual["time"] == cells["time"]
        for column in ("equity_raw", "equity_chained", "drawdown_pct"):
            assert float(actual[column]) == pytest.approx(float(cells[column])), (column, actual)


@then(
    parsers.parse(
        "the consolidated CSV has {count:d} data rows covering the strategies {names}"
    )
)
def _csv_count(ectx: dict[str, Any], count: int, names: str) -> None:
    rows = _csv_rows(ectx)
    assert len(rows) == count
    assert sorted({r["strategy"] for r in rows}) == sorted(n.strip() for n in names.split(","))


@then("the consolidated PNG is written")
def _png_written(ectx: dict[str, Any]) -> None:
    path: Path = ectx["paths"].chart
    assert path.name == "equity-consolidated.png"
    assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert not path.with_name(f".{path.name}.tmp").exists()


@then(parsers.parse('the chart title names the window "{window}"'))
def _title(ectx: dict[str, Any], window: str) -> None:
    assert chart_title(ectx["consolidation"]).endswith(window)


@then(parsers.parse('the summary line for "{strategy}" is "{line}"'))
def _summary_line(ectx: dict[str, Any], strategy: str, line: str) -> None:
    consolidation: Consolidation = ectx["consolidation"]
    summary = next(s for s in consolidation.summaries if s.strategy == strategy)
    assert summary_line(summary) == line


@then(parsers.parse('the failure names all of "{first}", "{second}" and "{third}"'))
def _failure_names_three(ectx: dict[str, Any], first: str, second: str, third: str) -> None:
    for text in (first, second, third):
        assert text in ectx["error"], ectx["error"]


@then(parsers.parse('the failure names both "{first}" and "{second}"'))
def _failure_names_two(ectx: dict[str, Any], first: str, second: str) -> None:
    assert first in ectx["error"] and second in ectx["error"], ectx["error"]


@then(parsers.parse('the failure names "{text}"'))
def _failure_names(ectx: dict[str, Any], text: str) -> None:
    assert text in ectx["error"], ectx["error"]


@then(parsers.parse('the failure names the run directory of "{run_id}" and "{text}"'))
def _failure_names_run_dir(ectx: dict[str, Any], run_id: str, text: str) -> None:
    assert str(ectx["runs"][run_id]) in ectx["error"] and text in ectx["error"], ectx["error"]


@then(parsers.parse("the command exits with code {code:d}"))
def _cli_exit(ectx: dict[str, Any], code: int) -> None:
    assert ectx["cli"].exit_code == code, ectx["cli"].output


@then(parsers.parse('the output directory contains "{first}" and "{second}"'))
def _out_contains(ectx: dict[str, Any], first: str, second: str) -> None:
    out: Path = ectx["out"]
    assert (out / first).stat().st_size > 0 and (out / second).stat().st_size > 0


@then(parsers.parse('the output prints "{text}"'))
def _output_prints(ectx: dict[str, Any], text: str) -> None:
    assert text in ectx["cli"].output, ectx["cli"].output


@then("the output prints both artifact paths")
def _output_paths(ectx: dict[str, Any]) -> None:
    out: Path = ectx["out"]
    for name in ("equity-consolidated.csv", "equity-consolidated.png"):
        assert str(out / name) in ectx["cli"].output, ectx["cli"].output
