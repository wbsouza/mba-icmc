"""Self-contained HTML performance dashboard (`report.html`) for one finished run.

The broker "Account Performance" page as the presentation of a simulation: a dark
trading-dashboard theme, six account KPI cards (the same numbers as the statement's A/C
Summary), a full-width SVG equity curve, six performance KPI cards, and CSS-only tabs
(Equity, Drawdown, Monthly Returns, Trade History, Parameters). Everything is inline —
CSS and SVG in the document, no script, no external font, no CDN — so the file opens
from `file://` offline and archives with the run.

All figures derive from the `Statement` built by `algo_backtest.statement` (itself a pure
derivation of the run directory's artifacts); the only constants here are presentation
(colours, sizes, labels). Monthly returns chain each month from the previous month's
last equity sample (the first month starts at the first sample) so the months compound
to the run's return. Profit factor is gross profit / gross loss over the closed trades
and is "n/a" when no trade lost.
"""

from __future__ import annotations

import html
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from algo_backtest.statement import (
    CLOSED_COLUMNS,
    ClosedTransaction,
    Statement,
    drawdowns,
    format_time,
    money,
    transaction_cells,
)

REPORT_FILE = "report.html"
TAB_LABELS = ("Equity", "Drawdown", "Monthly Returns", "Trade History", "Parameters")
# Presentation only.
CHART_WIDTH = 1000
CHART_HEIGHT = 320
CHART_MARGINS = {"left": 76, "right": 16, "top": 16, "bottom": 36}
Y_TICKS = 5
_LEVERAGE_KEY = "capital_mgmt.assumed_leverage"
_COLORS = {
    "bg": "#0f1419", "card": "#1a2029", "border": "#2b3240", "text": "#e6edf3",
    "muted": "#8b949e", "up": "#3fb950", "down": "#f85149", "accent": "#58a6ff",
    "grid": "#2b3240",
}


@dataclass(frozen=True)
class Kpi:
    """One dashboard card: a label, the headline value, an optional note and a tone."""

    label: str
    value: str
    note: str = ""
    tone: str = "neutral"


@dataclass(frozen=True)
class MonthlyReturn:
    """One row of the Monthly Returns tab."""

    month: str
    start_equity: float
    end_equity: float
    return_pct: float
    trades: int


# --- pure helpers ----------------------------------------------------------------------


def svg_equity_path(
    points: Sequence[tuple[float, float]], width: float, height: float, *,
    y_range: tuple[float, float] | None = None,
) -> str:
    """An SVG `M … L …` path mapping x linearly onto [0, width] and y onto [height, 0].

    Coordinates carry one decimal. A flat series (or a single point) sits on the
    vertical midline; a single point sits at x = 0. `y_range` pins the vertical scale
    (so a reference line drawn with the same scale lines up); by default it is the
    series' own min/max. Empty input gives an empty path.
    """
    if not points:
        return ""
    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    x_min, x_span = min(xs), max(xs) - min(xs)
    y_min, y_max = y_range if y_range is not None else (min(ys), max(ys))
    y_span = y_max - y_min

    def sx(x: float) -> float:
        return (x - x_min) / x_span * width if x_span else 0.0

    def sy(y: float) -> float:
        return height - (y - y_min) / y_span * height if y_span else height / 2

    return "M" + " L".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in points)


def profit_factor(transactions: Sequence[ClosedTransaction]) -> float | None:
    """Gross profit / gross loss over the closed trades; `None` when nothing was lost."""
    gross_profit = sum(t.profit for t in transactions if t.profit > 0)
    gross_loss = -sum(t.profit for t in transactions if t.profit < 0)
    return gross_profit / gross_loss if gross_loss > 0 else None


def monthly_returns(
    equity: Sequence[tuple[datetime, float]], transactions: Sequence[ClosedTransaction]
) -> list[MonthlyReturn]:
    """Month by month: start = previous month's last sample (first sample for the first
    month), end = the month's last sample, return = end / start − 1, trades = closed
    trades whose close time falls in the month."""
    last_by_month: dict[str, float] = {}
    for moment, value in equity:
        last_by_month[moment.astimezone(UTC).strftime("%Y-%m")] = value
    closes = [t.close_time.astimezone(UTC).strftime("%Y-%m") for t in transactions]
    rows: list[MonthlyReturn] = []
    start = equity[0][1] if equity else 0.0
    for month, end in last_by_month.items():
        if start <= 0:
            raise ValueError(f"equity must be positive to define a monthly return, got {start}")
        pct = (end / start - 1.0) * 100.0
        rows.append(MonthlyReturn(month, start, end, pct, closes.count(month)))
        start = end
    return rows


def leverage_label(statement: Statement) -> str:
    """`1:<n>` from `capital_mgmt.assumed_leverage`, or "n/a" when the run recorded none."""
    for parameter in statement.parameters:
        if parameter.key == _LEVERAGE_KEY:
            value = Decimal(parameter.value).normalize()
            return f"1:{value:f}"
    return "n/a"


def _tone(value: float) -> str:
    """Green above zero, red below, neutral at zero."""
    return "up" if value > 0 else "down" if value < 0 else "neutral"


def _pct(value: float, signed: bool = True) -> str:
    """A percentage to two decimals, signed by default."""
    return f"{value:+.2f}%" if signed else f"{value:.2f}%"


def net_return_pct(statement: Statement) -> float:
    """Equity over the starting deposit, in percent (the same figures as the A/C block)."""
    s = statement.summary
    if s.previous_balance <= 0:
        raise ValueError(f"starting deposit must be positive, got {s.previous_balance}")
    return (s.equity - s.previous_balance) / s.previous_balance * 100.0


def account_kpis(statement: Statement) -> list[Kpi]:
    """The first card row: the A/C Summary figures as cards."""
    s = statement.summary
    net = net_return_pct(statement)
    margin_note = (
        "n/a" if s.margin_requirement is None or s.equity == 0
        else f"{_pct(s.margin_requirement / s.equity * 100.0, signed=False)} of equity"
    )
    return [
        Kpi("Account Balance", money(s.balance)),
        Kpi("Equity", money(s.equity), f"{_pct(net)} since start", _tone(net)),
        Kpi("Floating P/L", money(s.floating_pl), tone=_tone(s.floating_pl)),
        Kpi("Margin Used", _optional(s.margin_requirement), margin_note),
        Kpi("Free Margin", _optional(s.available_margin)),
        Kpi("Leverage", leverage_label(statement)),
    ]


def performance_kpis(statement: Statement) -> list[Kpi]:
    """The second card row: return, drawdown, Sharpe, win rate, trades, profit factor."""
    performance = dict(statement.performance)
    net = net_return_pct(statement)
    max_dd = max(drawdowns([v for _, v in statement.equity]), default=0.0)
    factor = profit_factor(statement.transactions)
    return [
        Kpi("Total Return %", _pct(net), tone=_tone(net)),
        Kpi("Max Drawdown %", _pct(max_dd, signed=False), tone="down"),
        Kpi("Sharpe Ratio", performance["Sharpe ratio"]),
        Kpi("Win Rate", performance["Win rate"]),
        Kpi("Total Trades", str(len(statement.transactions))),
        Kpi("Profit Factor", "n/a" if factor is None else f"{factor:.2f}"),
    ]


def _optional(value: float | None) -> str:
    """Money or "n/a"."""
    return "n/a" if value is None else money(value)


# --- SVG charts ------------------------------------------------------------------------


def _y_of(value: float, y_range: tuple[float, float], height: float) -> float:
    """The same vertical mapping `svg_equity_path` uses, for grid lines and references."""
    y_min, y_max = y_range
    return height - (value - y_min) / (y_max - y_min) * height if y_max > y_min else height / 2


def _month_ticks(points: Sequence[tuple[datetime, float]]) -> Iterator[tuple[float, str]]:
    """(x as timestamp, label) at the first sample of each month."""
    seen: set[str] = set()
    for moment, _ in points:
        key = moment.astimezone(UTC).strftime("%Y-%m")
        if key not in seen:
            seen.add(key)
            yield moment.timestamp(), moment.astimezone(UTC).strftime("%b %Y")


def _chart_svg(
    points: Sequence[tuple[datetime, float]], *, y_range: tuple[float, float],
    tick_label: str, color: str, reference: float | None, gradient_id: str,
) -> str:
    """A full-width area chart: grid, y ticks, month x ticks, gradient fill, reference line.

    `tick_label` is a format spec applied to each y tick value (e.g. ',.0f' or '.2f%').
    """
    m = CHART_MARGINS
    pw, ph = CHART_WIDTH - m["left"] - m["right"], CHART_HEIGHT - m["top"] - m["bottom"]
    xy = [(t.timestamp(), v) for t, v in points]
    line = svg_equity_path(xy, pw, ph, y_range=y_range)
    x_min, x_span = (xy[0][0], xy[-1][0] - xy[0][0]) if xy else (0.0, 0.0)
    parts = [
        f'<svg viewBox="0 0 {CHART_WIDTH} {CHART_HEIGHT}" class="chart" role="img">',
        f'<defs><linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{color}" stop-opacity="0.45"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>',
        f'<g transform="translate({m["left"]},{m["top"]})">',
    ]
    y_min, y_max = y_range
    ticks = Y_TICKS if y_max > y_min else 1
    for i in range(ticks):
        value = y_min + (y_max - y_min) * i / max(ticks - 1, 1)
        y = _y_of(value, y_range, ph)
        label = format(value, tick_label.rstrip("%")) + ("%" if tick_label.endswith("%") else "")
        parts.append(
            f'<line x1="0" y1="{y:.1f}" x2="{pw}" y2="{y:.1f}" class="grid"/>'
            f'<text x="-8" y="{y + 4:.1f}" class="tick" text-anchor="end">'
            f"{html.escape(label)}</text>"
        )
    for x_value, label in _month_ticks(points):
        x = (x_value - x_min) / x_span * pw if x_span else 0.0
        parts.append(
            f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{ph}" class="grid"/>'
            f'<text x="{x:.1f}" y="{ph + 22}" class="tick" text-anchor="middle">{label}</text>'
        )
    if line:
        x_last = line.rsplit(" ", 1)[-1].lstrip("ML").split(",")[0]
        parts.append(f'<path d="{line} L{x_last},{ph} L0.0,{ph} Z" fill="url(#{gradient_id})"/>')
        parts.append(f'<path d="{line}" fill="none" stroke="{color}" stroke-width="1.8"/>')
    if reference is not None and y_min <= reference <= y_max:
        y = _y_of(reference, y_range, ph)
        parts.append(
            f'<line x1="0" y1="{y:.1f}" x2="{pw}" y2="{y:.1f}" class="reference"/>'
        )
    parts.append("</g></svg>")
    return "".join(parts)


def equity_chart_svg(statement: Statement) -> str:
    """The equity curve with the starting deposit as a dashed reference line."""
    values = [v for _, v in statement.equity] + [statement.starting_deposit]
    return _chart_svg(
        statement.equity, y_range=(min(values), max(values)), tick_label=",.0f",
        color=_COLORS["accent"], reference=statement.starting_deposit, gradient_id="equity-fill",
    )


def drawdown_chart_svg(statement: Statement) -> str:
    """Drawdown % from the running peak, drawn downwards from zero."""
    series = drawdowns([v for _, v in statement.equity])
    points = [(t, -d) for (t, _), d in zip(statement.equity, series, strict=True)]
    return _chart_svg(
        points, y_range=(-max(series, default=0.0), 0.0), tick_label=".2f%",
        color=_COLORS["down"], reference=None, gradient_id="drawdown-fill",
    )


# --- HTML ------------------------------------------------------------------------------


def _card(kpi: Kpi) -> str:
    """One KPI card."""
    note = f'<div class="note {kpi.tone}">{html.escape(kpi.note)}</div>' if kpi.note else ""
    return (
        f'<div class="card"><div class="label">{html.escape(kpi.label)}</div>'
        f'<div class="value {kpi.tone}">{html.escape(kpi.value)}</div>{note}</div>'
    )


def _html_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """An HTML table with escaped cells."""
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _monthly_table(statement: Statement) -> str:
    """The Monthly Returns tab."""
    rows = [
        [r.month, money(r.start_equity), money(r.end_equity), _pct(r.return_pct), str(r.trades)]
        for r in monthly_returns(statement.equity, statement.transactions)
    ]
    headers = ["Month", "Start Equity", "End Equity", "Return %", "Trades"]
    return _html_table(headers, rows) if rows else "<p class='empty'>No equity samples</p>"


def _trades_table(statement: Statement) -> str:
    """The Trade History tab: the statement's Closed Transactions columns."""
    rows = [transaction_cells(t, statement.price_decimals) for t in statement.transactions]
    return _html_table(CLOSED_COLUMNS, rows) if rows else "<p class='empty'>No transactions</p>"


def _parameters_table(statement: Statement) -> str:
    """The Parameters tab: every parameter with its provenance."""
    rows = [[p.key, p.value, p.source] for p in statement.parameters]
    return _html_table(["Parameter", "Value", "Source"], rows)


def _tabs(statement: Statement, equity_svg: str) -> str:
    """CSS-only tabs (radio inputs + labels; no script)."""
    panels = {
        "Equity": equity_svg, "Drawdown": drawdown_chart_svg(statement),
        "Monthly Returns": _monthly_table(statement), "Trade History": _trades_table(statement),
        "Parameters": _parameters_table(statement),
    }
    ids = {label: label.lower().replace(" ", "-") for label in TAB_LABELS}
    inputs = "".join(
        f'<input type="radio" name="tab" id="tab-{ids[label]}"{" checked" if i == 0 else ""}>'
        for i, label in enumerate(TAB_LABELS)
    )
    nav = "".join(f'<label for="tab-{ids[label]}">{label}</label>' for label in TAB_LABELS)
    body = "".join(
        f'<div class="panel" id="panel-{ids[label]}">{panels[label]}</div>' for label in TAB_LABELS
    )
    return (
        f'<section class="tabs">{inputs}<nav>{nav}</nav><div class="panels">{body}</div></section>'
    )


def _css() -> str:
    """The inline stylesheet (dark dashboard theme)."""
    c = _COLORS
    tab_rules = "".join(
        f"#tab-{i}:checked~nav label[for=tab-{i}]{{color:{c['text']};border-color:{c['accent']}}}"
        f"#tab-{i}:checked~.panels #panel-{i}{{display:block}}"
        for i in (label.lower().replace(" ", "-") for label in TAB_LABELS)
    )
    return (
        f"body{{margin:0;padding:24px;background:{c['bg']};color:{c['text']};"
        "font:14px/1.45 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,"
        "sans-serif}h1{margin:0;font-size:22px}"
        f".sub{{margin:4px 0 0;color:{c['muted']}}}"
        f".gen{{margin:0;color:{c['muted']};font-size:12px}}"
        ".cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;"
        "margin:20px 0}"
        f".card{{background:{c['card']};border:1px solid {c['border']};border-radius:8px;"
        "padding:14px 16px}"
        f".label{{color:{c['muted']};font-size:12px;text-transform:uppercase;letter-spacing:.04em}}"
        ".value{font-size:22px;font-weight:600;margin-top:4px}.note{font-size:12px;margin-top:2px}"
        f".up{{color:{c['up']}}}.down{{color:{c['down']}}}.neutral{{}}"
        f".chart{{width:100%;height:auto;background:{c['card']};border:1px solid {c['border']};"
        "border-radius:8px}"
        f".grid{{stroke:{c['grid']};stroke-width:1}}.tick{{fill:{c['muted']};font-size:11px}}"
        f".reference{{stroke:{c['muted']};stroke-width:1;stroke-dasharray:6 4}}"
        ".tabs input{display:none}"
        f".tabs nav{{display:flex;gap:4px;border-bottom:1px solid {c['border']};"
        "margin:20px 0 12px}"
        f".tabs nav label{{padding:8px 14px;cursor:pointer;color:{c['muted']};"
        "border-bottom:2px solid transparent}"
        ".panel{display:none}"
        f"table{{width:100%;border-collapse:collapse;background:{c['card']};font-size:13px}}"
        f"th,td{{padding:6px 10px;border-bottom:1px solid {c['border']};text-align:right;"
        "white-space:nowrap}th:first-child,td:first-child{text-align:left}"
        f"th{{color:{c['muted']};font-weight:500}}.empty{{color:{c['muted']}}}"
        + tab_rules
    )


def render_report(statement: Statement, generated: datetime | None = None) -> str:
    """The complete `report.html` document."""
    stamp = (generated or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = f"Account Performance — {statement.strategy} / {statement.symbol}"
    subtitle = (
        f"{statement.strategy} · {statement.symbol} · {statement.start} .. {statement.end} · "
        f"run {statement.run_id} · as of {format_time(statement.period_end)} UTC"
    )
    equity_svg = equity_chart_svg(statement)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{_css()}</style></head><body>"
        f'<header><h1>Account Performance</h1><p class="sub">{html.escape(subtitle)}</p>'
        f'<p class="gen">Generated {stamp}</p></header>'
        f'<section class="cards">{"".join(_card(k) for k in account_kpis(statement))}</section>'
        f"{equity_svg}"
        f'<section class="cards">{"".join(_card(k) for k in performance_kpis(statement))}</section>'
        f"{_tabs(statement, equity_svg)}"
        "</body></html>\n"
    )
