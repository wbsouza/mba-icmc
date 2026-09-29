"""`equity-consolidated.html`: a self-contained dark dashboard comparing the strategies.

Pure rendering of a `Consolidation` (see `equity.py`) into one HTML document with inline
CSS and inline SVG only — no external scripts, stylesheets, fonts or images — so it opens
from `file://` and can be attached to a report as is. Layout, top to bottom:

1. a KPI card per strategy: start equity, end equity, chained net %, max drawdown %,
   trades and win rate (pooled from the runs' `trades.json` / `run.json`; `n/a` when a
   run did not record them — never estimated);
2. ONE full-width SVG chart: the chained curve of every strategy in a distinct colour
   (legend), a gradient fill under the best-performing line only, a dashed
   starting-deposit reference, y gridlines and month labels on the x axis;
3. a table of the runs that fed each curve: strategy, run id, window, raw end equity,
   chained end equity.

`svg_polyline()` is the one coordinate mapper — every curve and the fill polygon go
through it, so the geometry is testable with three points and known answers.
"""

from __future__ import annotations

import html
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from algo_backtest.statement import money

from algo_analyze.equity import Consolidation, CurvePoint, CurveSummary, RunRow

# Presentation only — the chart box in CSS pixels and the strategy palette.
CHART_WIDTH = 1100
CHART_HEIGHT = 380
MARGIN_LEFT = 80
MARGIN_RIGHT = 24
MARGIN_TOP = 20
MARGIN_BOTTOM = 44
Y_TICKS = 5
Y_PADDING = 0.03  # fraction of the equity span kept clear above and below the curves
PALETTE: tuple[str, ...] = (
    "#4cc9f0", "#f72585", "#ffd166", "#06d6a0", "#b388ff", "#ff9e64", "#80ed99", "#f9c74f",
)
UNAVAILABLE = "n/a"

_STYLE = """
:root { color-scheme: dark; }
body { margin: 0; padding: 24px; background: #0f1117; color: #e6e6e6;
       font: 14px/1.45 -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
h1 { margin: 0 0 4px; font-size: 22px; font-weight: 600; }
.sub { color: #9aa0ad; margin: 0 0 20px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 14px; margin-bottom: 22px; }
.kpi { background: #171a23; border: 1px solid #262a36; border-radius: 10px; padding: 14px 16px;
       border-top: 4px solid var(--c); }
.kpi h2 { margin: 0 0 10px; font-size: 16px; font-weight: 600; color: var(--c); }
.kpi dl { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 0; }
.kpi .m { display: flex; flex-direction: column; gap: 2px; }
.kpi dt { color: #9aa0ad; font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
.kpi dd { margin: 0; font-size: 17px; font-variant-numeric: tabular-nums; }
.pos { color: #06d6a0; } .neg { color: #f72585; }
.panel { background: #171a23; border: 1px solid #262a36; border-radius: 10px; padding: 16px;
         margin-bottom: 22px; }
.legend { list-style: none; display: flex; flex-wrap: wrap; gap: 8px 18px; margin: 0 0 8px;
          padding: 0; }
.legend-item::before { content: ""; display: inline-block; width: 22px; height: 3px;
                       background: var(--c); vertical-align: middle; margin-right: 8px; }
svg { width: 100%; height: auto; display: block; }
.grid { stroke: #262a36; stroke-width: 1; }
.tick { fill: #9aa0ad; font-size: 11px; }
.month { fill: #9aa0ad; font-size: 11px; text-anchor: middle; }
.deposit { stroke: #9aa0ad; stroke-width: 1; stroke-dasharray: 6 5; }
.curve { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #262a36; }
th { color: #9aa0ad; font-weight: 500; font-size: 12px; text-transform: uppercase; }
td.num, th.num { text-align: right; }
"""


def svg_polyline(
    points: Sequence[tuple[float, float]], width: float, height: float,
    x_range: tuple[float, float], y_range: tuple[float, float],
) -> str:
    """Map data points into a `width` x `height` pixel box as an SVG `points` attribute.

    x grows to the right, y grows UP (SVG's y axis is flipped for the caller); values
    are formatted with one decimal. Both ranges must span a non-zero interval.
    """
    x0, x1 = x_range
    y0, y1 = y_range
    if x1 == x0:
        raise ValueError(f"x_range must span a non-zero interval, got {x_range}")
    if y1 == y0:
        raise ValueError(f"y_range must span a non-zero interval, got {y_range}")
    return " ".join(
        f"{(x - x0) / (x1 - x0) * width:.1f},{(y1 - y) / (y1 - y0) * height:.1f}"
        for x, y in points
    )


def _x_range(points: Sequence[CurvePoint]) -> tuple[float, float]:
    """The time axis in Unix seconds (a single instant is widened by one day)."""
    stamps = [point.time.timestamp() for point in points]
    low, high = min(stamps), max(stamps)
    return (low, high if high > low else low + 86400.0)


def _y_range(points: Sequence[CurvePoint]) -> tuple[float, float]:
    """The equity axis, padded so no curve touches the box edge (flat data gets ±1 %)."""
    values = [point.equity_chained for point in points]
    low, high = min(values), max(values)
    pad = (high - low) * Y_PADDING if high > low else abs(high) * 0.01 or 1.0
    return (low - pad, high + pad)


def month_starts(start: date, end: date) -> list[date]:
    """The first day of every month from `start`'s month through `end`'s month."""
    months: list[date] = []
    cursor = start.replace(day=1)
    while cursor <= end:
        months.append(cursor)
        cursor = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
    return months


def month_label(day: date) -> str:
    """`Sep 2015` for the month of `day`."""
    return day.strftime("%b %Y")


def _pct(value: float) -> str:
    """A signed percentage wrapped in a positive/negative colour class."""
    css = "pos" if value >= 0 else "neg"
    return f'<span class="{css}">{value:+.2f}%</span>'


def _kpi_card(summary: CurveSummary, colour: str) -> str:
    """One KPI card: six metrics of a strategy's chained curve."""
    trades = str(summary.trades) if summary.trades is not None else UNAVAILABLE
    win_rate = (
        f"{summary.win_rate_pct:.2f}%" if summary.win_rate_pct is not None else UNAVAILABLE
    )
    name = html.escape(summary.strategy)
    metrics = (
        ("Start equity", "start", money(summary.first_equity)),
        ("End equity", "end", money(summary.last_equity)),
        ("Net (chained)", "net", _pct(summary.net_pct)),
        ("Max drawdown", "max_drawdown", f"{summary.max_drawdown_pct:.2f}%"),
        ("Trades", "trades", trades),
        ("Win rate", "win_rate", win_rate),
    )
    cells = "".join(
        f'<div class="m"><dt>{label}</dt><dd data-kpi="{key}">{value}</dd></div>'
        for label, key, value in metrics
    )
    return (
        f'<section class="kpi" data-strategy="{name}" style="--c:{colour}">'
        f"<h2>{name}</h2><dl>{cells}</dl></section>"
    )


def _legend(summaries: Sequence[CurveSummary], colours: dict[str, str]) -> str:
    """One legend entry per strategy, coloured like its curve."""
    items = "".join(
        f'<li class="legend-item" data-strategy="{html.escape(s.strategy)}" '
        f'style="--c:{colours[s.strategy]}">{html.escape(s.strategy)} ({s.net_pct:+.2f}%)</li>'
        for s in summaries
    )
    return f'<ul class="legend">{items}</ul>'


class _Box:
    """The plot area's pixel geometry and data ranges (one per chart)."""

    def __init__(self, points: Sequence[CurvePoint]) -> None:
        """Derive the axes from every point of the consolidation."""
        self.width = CHART_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
        self.height = CHART_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
        self.x_range = _x_range(points)
        self.y_range = _y_range(points)

    def polyline(self, points: Sequence[tuple[float, float]]) -> str:
        """Data -> pixel `points` attribute through the shared mapper."""
        return svg_polyline(points, self.width, self.height, self.x_range, self.y_range)

    def x(self, value: float) -> float:
        """Pixel x of a Unix-seconds value."""
        x0, x1 = self.x_range
        return (value - x0) / (x1 - x0) * self.width

    def y(self, value: float) -> float:
        """Pixel y (downwards) of an equity value."""
        y0, y1 = self.y_range
        return (y1 - value) / (y1 - y0) * self.height


def _y_gridlines(box: _Box) -> str:
    """Horizontal gridlines with money tick labels."""
    y0, y1 = box.y_range
    parts: list[str] = []
    for i in range(Y_TICKS + 1):
        value = y0 + (y1 - y0) * i / Y_TICKS
        y = box.y(value)
        parts.append(f'<line class="grid" x1="0" y1="{y:.1f}" x2="{box.width}" y2="{y:.1f}"/>')
        parts.append(f'<text class="tick" x="-10" y="{y + 4:.1f}" text-anchor="end">'
                     f"{money(value)}</text>")
    return "".join(parts)


def _month_axis(box: _Box, start: date, end: date) -> str:
    """Month labels along the x axis (a month starting before the data sits at the edge)."""
    x0, _ = box.x_range
    parts: list[str] = []
    for month in month_starts(start, end):
        stamp = max(datetime(month.year, month.month, 1, tzinfo=UTC).timestamp(), x0)
        x = box.x(stamp)
        parts.append(f'<line class="grid" x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{box.height}"/>')
        parts.append(f'<text class="month" x="{x:.1f}" y="{box.height + 28}">'
                     f"{month_label(month)}</text>")
    return "".join(parts)


def _deposit_lines(box: _Box, summaries: Sequence[CurveSummary]) -> str:
    """A dashed reference at every distinct starting deposit."""
    parts: list[str] = []
    for deposit in sorted({s.first_equity for s in summaries}):
        y = box.y(deposit)
        parts.append(f'<line class="deposit" x1="0" y1="{y:.1f}" x2="{box.width}" y2="{y:.1f}"/>')
        parts.append(f'<text class="tick" x="{box.width - 4}" y="{y - 5:.1f}" text-anchor="end">'
                     f"Starting deposit {money(deposit)}</text>")
    return "".join(parts)


def _curves(box: _Box, consolidation: Consolidation, colours: dict[str, str]) -> str:
    """Every strategy's chained polyline, plus a gradient fill under the best performer."""
    best = max(consolidation.summaries, key=lambda s: s.net_pct).strategy
    parts: list[str] = []
    for summary in consolidation.summaries:
        mine = [(p.time.timestamp(), p.equity_chained) for p in consolidation.points
                if p.strategy == summary.strategy]
        attr = box.polyline(mine)
        name = html.escape(summary.strategy)
        if summary.strategy == best:
            first_x, last_x = box.x(mine[0][0]), box.x(mine[-1][0])
            parts.append(
                f'<polygon class="fill" data-strategy="{name}" fill="url(#best-fill)" '
                f'points="{first_x:.1f},{box.height} {attr} {last_x:.1f},{box.height}"/>'
            )
        parts.append(f'<polyline class="curve" data-strategy="{name}" '
                     f'stroke="{colours[summary.strategy]}" points="{attr}"/>')
    return "".join(parts)


def render_chart(consolidation: Consolidation, colours: dict[str, str]) -> str:
    """The one full-width SVG chart of the dashboard."""
    box = _Box(consolidation.points)
    best_colour = colours[max(consolidation.summaries, key=lambda s: s.net_pct).strategy]
    return (
        f'<svg viewBox="0 0 {CHART_WIDTH} {CHART_HEIGHT}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="Consolidated equity curves">'
        f'<defs><linearGradient id="best-fill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{best_colour}" stop-opacity="0.35"/>'
        f'<stop offset="100%" stop-color="{best_colour}" stop-opacity="0"/>'
        f"</linearGradient></defs>"
        f'<g transform="translate({MARGIN_LEFT},{MARGIN_TOP})">'
        f"{_y_gridlines(box)}{_month_axis(box, consolidation.start, consolidation.end)}"
        f"{_deposit_lines(box, consolidation.summaries)}{_curves(box, consolidation, colours)}"
        f"</g></svg>"
    )


def _runs_table(rows: Sequence[RunRow]) -> str:
    """The runs that fed each curve, with raw and chained end equity."""
    body = "".join(
        f'<tr data-run="{html.escape(r.run_id)}"><td>{html.escape(r.strategy)}</td>'
        f"<td>{html.escape(r.run_id)}</td><td>{r.start} .. {r.end}</td>"
        f'<td class="num">{money(r.raw_end)}</td><td class="num">{money(r.chained_end)}</td></tr>'
        for r in rows
    )
    return (
        "<table><thead><tr><th>Strategy</th><th>Run</th><th>Window</th>"
        '<th class="num">Raw end equity</th><th class="num">Chained end equity</th></tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


def strategy_colours(summaries: Sequence[CurveSummary]) -> dict[str, str]:
    """A distinct palette colour per strategy, in summary order (cycling past the palette)."""
    return {s.strategy: PALETTE[i % len(PALETTE)] for i, s in enumerate(summaries)}


def render_dashboard(consolidation: Consolidation) -> str:
    """The complete self-contained HTML document (inline CSS + inline SVG, nothing external)."""
    colours = strategy_colours(consolidation.summaries)
    cards = "".join(_kpi_card(s, colours[s.strategy]) for s in consolidation.summaries)
    window = f"{consolidation.start} .. {consolidation.end}"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Equity curves {html.escape(window)}</title><style>{_STYLE}</style></head><body>"
        f"<h1>Consolidated equity curves</h1>"
        f'<p class="sub">{html.escape(window)} · one line per strategy; consecutive windows of '
        "a strategy are chained (each later window re-based to start where the previous one "
        "ended). Trades and win rate are pooled from the runs' ledgers; n/a = not recorded.</p>"
        f'<div class="kpis">{cards}</div>'
        f'<div class="panel">{_legend(consolidation.summaries, colours)}'
        f"{render_chart(consolidation, colours)}</div>"
        f'<div class="panel">{_runs_table(consolidation.runs)}</div>'
        "</body></html>\n"
    )

