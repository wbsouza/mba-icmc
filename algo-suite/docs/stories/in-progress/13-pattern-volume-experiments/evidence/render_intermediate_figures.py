"""Plot frozen, completed Story 13 predecessor evidence without changing source runs.

Adapted layout/styling guidance (not empirical claims):
https://github.com/agiprolabs/claude-trading-skills/blob/main/skills/trading-visualization/SKILL.md
Reuse the repository's equity reader, drawdown calculation, and thesis style.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from algo_analyze._style import plt, thesis_style
from algo_analyze.equity import read_equity_csv
from algo_backtest.statement import drawdowns
from matplotlib import dates as mdates
from matplotlib import ticker

EVIDENCE = Path(__file__).resolve().parent
SNAPSHOT = EVIDENCE / "snapshot-20260928T003601Z.json"
APPENDIX = "per-run-parameters-20260928T003601Z.md"
GROUPS = {
    "execution-september": ("Execution model / September 2015", ("R08", "R13")),
    "execution-october": ("Execution model / October 2015", ("R09", "R14")),
    "a05-sweep-september": ("A05 exploratory sweep / September 2015", ("R01", "R03", "R04", "R05")),
    "spockfx-sweep-september": (
        "SpockFX-derived M1 sweep / September 2015", ("R15", "R16", "R17", "R18")
    ),
}
COLORS = ("#4488ff", "#ffaa00", "#cc77ff", "#00cccc")
PRINT_COLORS = ("#1763a6", "#ad5c00", "#7d399f", "#007c7c")
LINE_STYLES = ("-", "--", "-.", ":")


def verify_artifact(artifact: dict[str, Any]) -> Path:
    """Reject missing or changed inputs before reading their financial content."""
    if artifact["status"] != "present":
        raise ValueError(f"Missing archived artifact: {artifact['path']}; exclude this run")
    path = Path(artifact["path"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["sha256"]:
        raise ValueError(f"Source hash mismatch: {path}; collect a new evidence snapshot")
    return path


def load_completed(run: dict[str, Any]) -> tuple[tuple[Any, float], ...]:
    """Load unchanged real equity only after a successful final manifest is verified."""
    manifest = run["files"]["run.json"]
    if run["status"] != "successful" or manifest.get("value", {}).get("success") is not True:
        raise ValueError(f"Incomplete run {run['reference']}; no completed result may be plotted")
    for name in ("run.json", "metrics.json", "strategy-config.json", "equity.csv"):
        verify_artifact(run["files"][name])
    samples = read_equity_csv(Path(manifest["path"]).parent)
    if any(not math.isfinite(value) or value <= 0 for _, value in samples):
        raise ValueError(f"Invalid equity in {run['reference']}; inspect the original artifact")
    if any(a[0] >= b[0] for a, b in zip(samples, samples[1:], strict=False)):
        raise ValueError(f"Unordered equity in {run['reference']}; inspect the original artifact")
    return samples


def parameter_label(run: dict[str, Any]) -> str:
    """Join a curve's run identity and archived F6/F7 settings without defaults."""
    config = run["files"]["strategy-config.json"]["value"]
    capital, meta = config["capital_mgmt"], config["meta_learner"]
    manifest, metrics = run["files"]["run.json"]["value"], run["files"]["metrics.json"]["value"]
    name = manifest["strategy"].removeprefix("spockfx-")
    return (
        f"{run['reference']} {name} / {metrics['total_return']:+.2%} / "
        f"{manifest['closed_trades']} trades\n"
        f"F6 risk={capital['risk_per_trade']:.0%}, {capital['stop_distance_source']}; "
        f"F7 gate={'on' if meta['regime_gate'] else 'off'}, "
        f"{meta['theta_high']}/{meta['theta_low']}"
    )


def draw_series(axes: Any, run: dict[str, Any], index: int, dark: bool) -> None:
    """Render raw samples and their negative peak-relative drawdown without chaining."""
    samples = load_completed(run)
    times, values = zip(*samples, strict=True)
    color = (COLORS if dark else PRINT_COLORS)[index]
    axes[0].plot(times, values, color=color, linestyle=LINE_STYLES[index],
                 linewidth=1.4, label=parameter_label(run))
    underwater = [-value for value in drawdowns(values)]
    axes[1].plot(times, underwater, color=color, linestyle=LINE_STYLES[index], linewidth=1)
    axes[1].fill_between(times, underwater, 0, color=color, alpha=0.08)


def style_axes(axes: Any, dark: bool) -> None:
    """Apply readable shared-axis formatting to equity and underwater panels."""
    background, foreground = ("#1a1a2e", "#e0e0e0") if dark else ("white", "#222222")
    for axis in axes:
        axis.set_facecolor(background)
        axis.tick_params(colors=foreground, labelsize=10)
        axis.yaxis.label.set_color(foreground)
        axis.xaxis.label.set_color(foreground)
        axis.grid(True, color="#777777", alpha=0.25, linestyle="--")
    axes[0].set_ylabel("Equity (account currency)", fontsize=12)
    axes[0].yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    axes[1].set_ylabel("Drawdown (%)", fontsize=12)
    axes[1].set_xlabel("Date (UTC) / observed equity samples", fontsize=12)
    # Matplotlib's DateFormatter constructor lacks a typed external signature.
    formatter = mdates.DateFormatter("%d %b")  # type: ignore[no-untyped-call]
    axes[1].xaxis.set_major_formatter(formatter)
    axes[1].axhline(0, color=foreground, linewidth=0.6)
    axes[1].set_ylim(top=2)


def make_figure(runs: list[dict[str, Any]], title: str, dark: bool = True) -> Any:
    """Build a 2:1 figure with traceable labels; caller owns saving and closing it."""
    with thesis_style():
        figure, axes = plt.subplots(2, 1, figsize=(14, 9), sharex=True,
                                    gridspec_kw={"height_ratios": [2, 1], "hspace": 0.08})
        foreground = "#e0e0e0" if dark else "#222222"
        figure.patch.set_facecolor("#1a1a2e" if dark else "white")
        for index, run in enumerate(runs):
            draw_series(axes, run, index, dark)
        style_axes(axes, dark)
        figure.suptitle(title + " / exploratory snapshot", fontsize=16, color=foreground)
        legend = figure.legend(*axes[0].get_legend_handles_labels(), loc="upper center",
                               bbox_to_anchor=(0.5, 0.94), ncol=2, fontsize=10, frameon=False)
        for label, run in zip(legend.get_texts(), runs, strict=True):
            label.set_color(foreground)
            label.set_url(f"../{APPENDIX}#{run['reference'].lower()}")
        figure.subplots_adjust(top=0.73 if len(runs) > 2 else 0.81, bottom=0.12)
        figure.text(0.125, 0.035, "Snapshot 2026-09-28 00:36 UTC / each run starts separately; "
                    "no monthly chaining\nR labels join the full F1-F7 parameter appendix. "
                    "Drawdown uses observed samples; returns in legend come from metrics.json.",
                    fontsize=10, color=foreground)
    return figure


def main() -> None:
    """Export fixed completed-run groups; sources are read-only and hash-checked."""
    snapshot = json.loads(SNAPSHOT.read_text())
    by_reference = {run["reference"]: run for run in snapshot["runs"]}
    output = EVIDENCE / "figures"
    output.mkdir(exist_ok=True)
    for name, (title, references) in GROUPS.items():
        runs = [by_reference[reference] for reference in references]
        for dark, suffix in ((True, "dark.png"), (False, "print.pdf")):
            figure = make_figure(runs, title, dark)
            destination = output / f"{name}-{suffix}"
            figure.savefig(destination, dpi=150, facecolor=figure.get_facecolor(),
                           edgecolor="none", bbox_inches="tight")
            plt.close(figure)
            print(destination)


if __name__ == "__main__":
    main()
