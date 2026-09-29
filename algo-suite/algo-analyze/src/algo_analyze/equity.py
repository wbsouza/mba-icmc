"""Consolidated equity curves: several finished runs on one time axis.

`algo-analyze equity-curves --run DIR... --out DIR` reads, per run directory, `run.json`
(strategy, window) and the `equity.csv` that `algo-backtest statement --run` writes next
to `equity.png` (`time`, `equity`, `drawdown_pct`, one row per LEAN equity sample), and
produces a robustness-testing overlay: **one line per strategy**, with the consecutive
windows of the same strategy chained into one continuous curve.

Chaining (re-basing)
--------------------
Each backtest window starts from a fresh deposit (`--param cash=10000`), so plotting
three monthly runs of `baseline` verbatim would show two artificial resets to 10,000.
Runs of one strategy are sorted by window start and every later window is **re-based** so
it starts where the previous window ended:

    equity_chained = equity_raw * previous_window_chained_end / this_window_raw_start

The factor compounds along the chain (November is re-based onto the re-based October),
which equals the account one would have had by carrying the balance forward instead of
redepositing. Nothing is fabricated: the un-chained `equity_raw` is kept in every row of
the long-format CSV, and `drawdown_pct` is the percent below the running peak **of the
chained curve** (so a loss straddling a month boundary is one drawdown, not two). Windows
of the same strategy must not overlap (fail fast); different strategies may cover the
same dates and simply share the axis.

Outputs (in `--out`): `equity-consolidated.csv` (long format: strategy, run_id, time,
equity_raw, equity_chained, drawdown_pct), `equity-consolidated.png` (one chained line
per strategy, dashed starting-deposit reference, dotted window boundaries, legend, date
axis, title with the covered window) and `equity-consolidated.html` (the self-contained
comparison dashboard, see `equity_dashboard.py`). One summary line per strategy
(first/last equity, chained net %, max drawdown %) is printed by the CLI.

Trades and win rate (dashboard KPIs) come from each run's `trades.json` (LEAN's closed
trades, `isWin` per trade) when present, else the trade count from `run.json`'s
`closed_trades`; whatever is absent is reported as unavailable, never estimated.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, cast

from algo_backtest.statement import EQUITY_CSV_COLUMNS, EQUITY_CSV_FILE, drawdowns, money
from algo_core.atomicio import write_text_atomic

from algo_analyze._style import plt, thesis_style

RUN_FILE = "run.json"
TRADES_FILE = "trades.json"
CONSOLIDATED_CSV_FILE = "equity-consolidated.csv"
CONSOLIDATED_CHART_FILE = "equity-consolidated.png"
CONSOLIDATED_HTML_FILE = "equity-consolidated.html"
CONSOLIDATED_COLUMNS: tuple[str, ...] = (
    "strategy", "run_id", "time", "equity_raw", "equity_chained", "drawdown_pct",
)
STATEMENT_COMMAND = "algo-backtest statement --run"
# Presentation only — no arithmetic depends on these.
CHART_DPI = 150
CHART_SIZE = (10.0, 5.5)
BOUNDARY = "#999999"  # dotted marker where a later window was chained onto the previous one


@dataclass(frozen=True)
class RunEquity:
    """One finished run: identity, window (inclusive dates) and its raw equity samples."""

    run_dir: Path
    run_id: str
    strategy: str
    start: date
    end: date
    samples: tuple[tuple[datetime, float], ...]
    trades: int | None
    wins: int | None


@dataclass(frozen=True)
class CurvePoint:
    """One long-format row: a sample of one run, raw and re-based onto its strategy's chain."""

    strategy: str
    run_id: str
    time: datetime
    equity_raw: float
    equity_chained: float
    drawdown_pct: float


@dataclass(frozen=True)
class CurveSummary:
    """The summary of a strategy's chained curve (trades/win rate `None` = not recorded)."""

    strategy: str
    runs: int
    first_equity: float
    last_equity: float
    net_pct: float
    max_drawdown_pct: float
    trades: int | None
    win_rate_pct: float | None


@dataclass(frozen=True)
class RunRow:
    """One run that fed a curve: window, raw end equity and its chained end equity."""

    strategy: str
    run_id: str
    start: date
    end: date
    raw_end: float
    chained_end: float


@dataclass(frozen=True)
class Consolidation:
    """Every chained point, one summary per strategy, the runs, and the covered window."""

    points: tuple[CurvePoint, ...]
    summaries: tuple[CurveSummary, ...]
    runs: tuple[RunRow, ...]
    start: date
    end: date


@dataclass(frozen=True)
class ConsolidatedPaths:
    """Where the long-format CSV, the chart and the HTML dashboard were written."""

    csv: Path
    chart: Path
    html: Path


# --- loading ---------------------------------------------------------------------------


def _read_run_manifest(run_dir: Path) -> dict[str, Any]:
    """Parse `run.json`, failing fast with the path when it is absent or not a JSON object."""
    path = run_dir / RUN_FILE
    if not path.is_file():
        raise FileNotFoundError(
            f"{run_dir} has no {RUN_FILE}; every --run must be a finished results directory "
            "(runs/<strategy>/<stamp>/) written by `algo-backtest run`"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"{path} is not valid JSON ({exc}); re-run the backtest") from exc
    if not isinstance(document, dict):
        raise ValueError(f"{path} must be a JSON object, got {type(document).__name__}")
    return document


def _manifest_date(document: Mapping[str, Any], key: str, path: Path) -> date:
    """`run.json`'s `start`/`end` as a date, naming the file and key on any problem."""
    try:
        return date.fromisoformat(str(document[key]))
    except KeyError as exc:
        raise ValueError(f"{path} lacks the {key!r} key; re-run the backtest") from exc
    except ValueError as exc:
        raise ValueError(f"{path} key {key!r} is not a YYYY-MM-DD date ({exc})") from exc


def _equity_csv_path(run_dir: Path) -> Path:
    """The run's `equity.csv`, failing fast with the command that creates it when absent."""
    path = run_dir / EQUITY_CSV_FILE
    if not path.is_file():
        raise FileNotFoundError(
            f"{run_dir} has no {EQUITY_CSV_FILE}; regenerate the run's statement artifacts "
            f"with `{STATEMENT_COMMAND} {run_dir}` (writes statement.md, equity.png and "
            f"{EQUITY_CSV_FILE})"
        )
    return path


def _parse_sample(row: Sequence[str], path: Path, line: int) -> tuple[datetime, float]:
    """One `equity.csv` data row -> (aware UTC time, equity)."""
    try:
        return datetime.fromisoformat(row[0]), float(row[1])
    except (IndexError, ValueError) as exc:
        raise ValueError(
            f"{path} line {line} is not `time,equity,drawdown_pct` ({row!r}: {exc}); "
            f"regenerate it with `{STATEMENT_COMMAND} {path.parent}`"
        ) from exc


def read_equity_csv(run_dir: Path) -> tuple[tuple[datetime, float], ...]:
    """The (time, equity) samples of a run's `equity.csv`.

    Raises:
        FileNotFoundError: the file is absent (the message names the statement command).
        ValueError: the header is not `time,equity,drawdown_pct`, a row is malformed, or
            the file holds no samples.
    """
    path = _equity_csv_path(run_dir)
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    header = rows[0] if rows else []
    if tuple(header) != EQUITY_CSV_COLUMNS:
        raise ValueError(
            f"{path} header is {','.join(header)!r}, expected {','.join(EQUITY_CSV_COLUMNS)}; "
            f"regenerate it with `{STATEMENT_COMMAND} {run_dir}`"
        )
    samples = tuple(_parse_sample(row, path, n) for n, row in enumerate(rows[1:], start=2))
    if not samples:
        raise ValueError(
            f"{path} has no equity samples; the backtest may not have run — re-run it, then "
            f"`{STATEMENT_COMMAND} {run_dir}`"
        )
    return samples


def _trade_counts(run_dir: Path, manifest: Mapping[str, Any]) -> tuple[int | None, int | None]:
    """(closed trades, winning trades) from `trades.json`, else the manifest's count and
    no win count, else (None, None) — absent data is reported, never estimated."""
    path = run_dir / TRADES_FILE
    if not path.is_file():
        count = manifest.get("closed_trades")
        return (count if isinstance(count, int) and not isinstance(count, bool) else None, None)
    try:
        trades = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ValueError(f"{path} is not valid JSON ({exc}); re-run the backtest") from exc
    if not isinstance(trades, list) or not all(isinstance(t, dict) for t in trades):
        raise ValueError(f"{path} must be a JSON list of closed trades; re-run the backtest")
    return len(trades), sum(1 for trade in trades if trade.get("isWin") is True)


def load_run_equity(run_dir: Path) -> RunEquity:
    """Read one run directory's manifest, equity series and trade counts."""
    manifest = _read_run_manifest(run_dir)
    path = run_dir / RUN_FILE
    if "strategy" not in manifest:
        raise ValueError(f"{path} lacks the 'strategy' key; re-run the backtest")
    trades, wins = _trade_counts(run_dir, manifest)
    return RunEquity(
        run_dir=run_dir, run_id=run_dir.name, strategy=str(manifest["strategy"]),
        start=_manifest_date(manifest, "start", path), end=_manifest_date(manifest, "end", path),
        samples=read_equity_csv(run_dir), trades=trades, wins=wins,
    )


def parse_labels(labels: Sequence[str]) -> dict[str, str]:
    """`strategy=Label` pairs -> mapping; a pair without both halves is rejected."""
    out: dict[str, str] = {}
    for text in labels:
        key, sep, value = text.partition("=")
        if not sep or not key or not value:
            raise ValueError(f"--label {text!r} is not of the form strategy=Label")
        out[key] = value
    return out


# --- chaining --------------------------------------------------------------------------


def group_by_strategy(runs: Sequence[RunEquity]) -> dict[str, list[RunEquity]]:
    """Runs by strategy name (keys sorted), each list sorted by window start.

    Raises:
        ValueError: two runs of one strategy have overlapping windows (they cannot be
            chained into one curve).
    """
    groups: dict[str, list[RunEquity]] = {}
    for run in sorted(runs, key=lambda r: (r.strategy, r.start, r.run_id)):
        groups.setdefault(run.strategy, []).append(run)
    for strategy, group in groups.items():
        for previous, current in zip(group, group[1:], strict=False):
            if current.start <= previous.end:
                raise ValueError(
                    f"strategy {strategy!r}: run {current.run_id} ({current.start} .. "
                    f"{current.end}) overlaps run {previous.run_id} ({previous.start} .. "
                    f"{previous.end}); chaining needs consecutive windows — pass "
                    "non-overlapping windows, or give the variant its own strategy name"
                )
    return groups


def rebase_factor(previous_end: float, this_start: float, run_id: str) -> float:
    """previous_end / this_start: scales a window so it starts where the last one ended."""
    if this_start <= 0:
        raise ValueError(
            f"run {run_id} starts at equity {this_start}; a window must start with positive "
            "equity to be re-based onto the previous one"
        )
    return previous_end / this_start


def _chained_values(runs: Sequence[RunEquity]) -> list[list[float]]:
    """Per run, the re-based equity values (the first run is never re-based)."""
    chained: list[list[float]] = []
    previous_end: float | None = None
    for run in runs:
        raw = [value for _, value in run.samples]
        if previous_end is None:
            values = raw
        else:
            factor = rebase_factor(previous_end, raw[0], run.run_id)
            values = [value * factor for value in raw]
        chained.append(values)
        previous_end = values[-1]
    return chained


def chain_strategy(label: str, runs: Sequence[RunEquity]) -> list[CurvePoint]:
    """The long-format points of one strategy's runs, chained and with chain drawdowns."""
    chained = _chained_values(runs)
    dd = iter(drawdowns([value for values in chained for value in values]))
    return [
        CurvePoint(
            strategy=label, run_id=run.run_id, time=moment, equity_raw=raw,
            equity_chained=value, drawdown_pct=next(dd),
        )
        for run, values in zip(runs, chained, strict=True)
        for (moment, raw), value in zip(run.samples, values, strict=True)
    ]


def _pooled_trades(runs: Sequence[RunEquity]) -> tuple[int | None, float | None]:
    """Trades summed and win rate % pooled over the runs; `None` as soon as one run lacks
    the datum (a partial pool would misstate the strategy)."""
    trades = [run.trades for run in runs]
    wins = [run.wins for run in runs]
    total = sum(t for t in trades if t is not None) if None not in trades else None
    if total is None or None in wins or total == 0:
        return total, None
    return total, sum(w for w in wins if w is not None) / total * 100.0


def summarize(label: str, points: Sequence[CurvePoint], runs: Sequence[RunEquity]) -> CurveSummary:
    """First/last chained equity, chained net %, max drawdown %, pooled trades of one strategy."""
    first, last = points[0].equity_chained, points[-1].equity_chained
    trades, win_rate = _pooled_trades(runs)
    return CurveSummary(
        strategy=label, runs=len(runs), first_equity=first, last_equity=last,
        net_pct=(last / first - 1.0) * 100.0,
        max_drawdown_pct=max(point.drawdown_pct for point in points),
        trades=trades, win_rate_pct=win_rate,
    )


def _run_rows(label: str, runs: Sequence[RunEquity], points: Sequence[CurvePoint]) -> list[RunRow]:
    """The dashboard's runs-table rows of one strategy (raw and chained end equity)."""
    last_by_run = {point.run_id: point.equity_chained for point in points}
    return [
        RunRow(
            strategy=label, run_id=run.run_id, start=run.start, end=run.end,
            raw_end=run.samples[-1][1], chained_end=last_by_run[run.run_id],
        )
        for run in runs
    ]


def _check_labels(labels: Mapping[str, str], strategies: Sequence[str]) -> None:
    """A --label must name a strategy some --run reports (a typo would silently do nothing)."""
    unknown = sorted(set(labels) - set(strategies))
    if unknown:
        raise ValueError(
            f"--label names strateg{'y' if len(unknown) == 1 else 'ies'} {unknown} but no "
            f"--run reports {'it' if len(unknown) == 1 else 'them'} (strategies given: "
            f"{sorted(strategies)})"
        )


def consolidate(runs: Sequence[RunEquity], labels: Mapping[str, str]) -> Consolidation:
    """Group, sort and chain every run; pure (see the module docstring for the rule)."""
    if not runs:
        raise ValueError("at least one --run directory is required")
    groups = group_by_strategy(runs)
    _check_labels(labels, list(groups))
    points: list[CurvePoint] = []
    summaries: list[CurveSummary] = []
    rows: list[RunRow] = []
    for strategy, group in groups.items():
        label = labels.get(strategy, strategy)
        chained = chain_strategy(label, group)
        points.extend(chained)
        summaries.append(summarize(label, chained, group))
        rows.extend(_run_rows(label, group, chained))
    return Consolidation(
        points=tuple(points), summaries=tuple(summaries), runs=tuple(rows),
        start=min(run.start for run in runs), end=max(run.end for run in runs),
    )


# --- rendering -------------------------------------------------------------------------


def render_consolidated_csv(points: Sequence[CurvePoint]) -> str:
    """`equity-consolidated.csv` text: header then one long-format row per sample."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CONSOLIDATED_COLUMNS)
    writer.writerows(
        (p.strategy, p.run_id, p.time.isoformat(), p.equity_raw, p.equity_chained, p.drawdown_pct)
        for p in points
    )
    return buffer.getvalue()


def chart_title(consolidation: Consolidation) -> str:
    """The chart title: what is drawn and the window it covers."""
    return (
        f"Consolidated equity (chained per strategy) / {consolidation.start} .. "
        f"{consolidation.end}"
    )


def summary_line(summary: CurveSummary) -> str:
    """One console line per strategy: first/last equity, chained net %, max drawdown %."""
    return (
        f"{summary.strategy}: first {money(summary.first_equity)} -> last "
        f"{money(summary.last_equity)}, net {summary.net_pct:+.2f}%, max drawdown "
        f"{summary.max_drawdown_pct:.2f}%, {summary.runs} run(s)"
    )


def _window_boundaries(points: Sequence[CurvePoint]) -> list[datetime]:
    """The first sample time of every run after the first one of its strategy."""
    boundaries: list[datetime] = []
    seen: dict[str, str] = {}
    for point in points:
        if seen.setdefault(point.strategy, point.run_id) != point.run_id:
            seen[point.strategy] = point.run_id
            boundaries.append(point.time)
    return boundaries


def render_consolidated_chart(consolidation: Consolidation, out: Path) -> Path:
    """One chained line per strategy on a shared date axis, PNG, written atomically."""
    with thesis_style():
        fig, ax = plt.subplots(figsize=CHART_SIZE)
        for summary in consolidation.summaries:
            mine = [p for p in consolidation.points if p.strategy == summary.strategy]
            # matplotlib converts aware datetimes natively; its stubs only type numbers.
            ax.plot(cast(Any, [p.time for p in mine]), [p.equity_chained for p in mine],
                    linewidth=1.4, label=f"{summary.strategy} ({summary.net_pct:+.2f}%)")
        for deposit in sorted({s.first_equity for s in consolidation.summaries}):
            ax.axhline(deposit, color="#666666", linewidth=0.8, linestyle="--",
                       label=f"Starting deposit {money(deposit)}")
        for boundary in _window_boundaries(consolidation.points):
            ax.axvline(cast(Any, boundary), color=BOUNDARY, linewidth=0.8, linestyle=":")
        ax.set_ylabel("Equity (account currency)")
        ax.set_xlabel("Date (UTC)")
        ax.set_title(chart_title(consolidation))
        ax.legend(loc="best")
        fig.autofmt_xdate()
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(f".{out.name}.tmp")
        try:
            fig.savefig(tmp, dpi=CHART_DPI, format="png")
        finally:
            plt.close(fig)
        tmp.replace(out)
    return out


def write_consolidated(
    run_dirs: Sequence[Path], labels: Sequence[str], out_dir: Path
) -> tuple[Consolidation, ConsolidatedPaths]:
    """Load every run, consolidate, and write the CSV + PNG + HTML dashboard into `out_dir`.

    Raises what `load_run_equity`/`consolidate` raise (FileNotFoundError, ValueError).
    """
    from algo_analyze.equity_dashboard import render_dashboard

    parsed = parse_labels(labels)
    consolidation = consolidate([load_run_equity(d) for d in run_dirs], parsed)
    csv_path = out_dir / CONSOLIDATED_CSV_FILE
    write_text_atomic(csv_path, render_consolidated_csv(consolidation.points))
    chart = render_consolidated_chart(consolidation, out_dir / CONSOLIDATED_CHART_FILE)
    html_path = out_dir / CONSOLIDATED_HTML_FILE
    write_text_atomic(html_path, render_dashboard(consolidation))
    return consolidation, ConsolidatedPaths(csv=csv_path, chart=chart, html=html_path)
