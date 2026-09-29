"""Render all eight real H4 cells, reusing the archived trading-visualization layout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import render_intermediate_figures as previous
from algo_analyze._style import plt

EVIDENCE = Path(__file__).resolve().parent
SNAPSHOT = EVIDENCE / "h4-snapshot-20260928T011114Z.json"
APPENDIX = "h4-parameters-20260928T011114Z.md"


def make_figure(runs: list[dict[str, Any]], title: str, dark: bool = True) -> Any:
    """Keep raw samples and 2:1 panels; replace historical labels with H4 identities."""
    figure = previous.make_figure(runs, title, dark)
    for label, run in zip(figure.legends[0].get_texts(), runs, strict=True):
        config = run["files"]["strategy-config.json"]["value"]
        metrics = run["files"]["metrics.json"]["value"]
        count = run["files"]["run.json"]["value"]["closed_trades"]
        volume = "on" if "volume_strength" in config["filters"] else "off"
        label.set_text(f"{run['reference']} F3={config['pattern']['detector']}, volume={volume}\n"
                       f"{metrics['total_return']:+.2%}, {count} closed trades; F7=0.55/0.45")
        label.set_url(f"../{APPENDIX}#{run['reference'].lower()}")
    figure.texts[-1].set_text(
        "Snapshot 2026-09-28 01:11 UTC / September 2015 H4 swing proxies / all four cells shown\n"
        "Coincident curves are retained. H labels link every filter and model identity; "
        "sample drawdown is not engine intraday maximum."
    )
    return figure


def main() -> None:
    """Export unique H4 figures and fingerprints without touching the predecessor archive."""
    runs = json.loads(SNAPSHOT.read_text())["runs"]
    outputs = {}
    for family, group in (("baseline-v1", runs[:4]), ("hybrid-v2", runs[4:])):
        for dark, suffix in ((True, "dark.png"), (False, "print.pdf")):
            figure = make_figure(group, f"H4 {family} / September 2015", dark)
            path = EVIDENCE / "figures" / f"h4-{family}-20260928T011114Z-{suffix}"
            if path.exists():
                raise FileExistsError(f"Preserve existing figure {path}; use a new snapshot name")
            figure.savefig(path, dpi=150, facecolor=figure.get_facecolor(), bbox_inches="tight")
            plt.close(figure)
            outputs[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    record = {"snapshot_sha256": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
              "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "reused_generator_sha256": hashlib.sha256(
                  (EVIDENCE / "render_intermediate_figures.py").read_bytes()).hexdigest(),
              "outputs": outputs}
    with (EVIDENCE / "h4-figure-provenance-20260928T011114Z.json").open("x") as handle:
        json.dump(record, handle, indent=2)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
