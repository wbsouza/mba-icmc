"""CLI for algo-analyze.

Wires the library modules into the exact command surface `docs/experiments.md` §2/§3
specifies: `summary`, `metrics`, `significance`, `ablation`, `figures`, plus
`equity-curves` (story 12: the consolidated multi-run equity overlay) and `results-db
build` (every finished run directory into one SQLite file for `algo-viewer`). Each command
resolves the data root via the shared config convention and reads run artifacts under
`<data_root>/runs/<run-id>/` — except `equity-curves`, whose `--run` values are results
directories given explicitly — and fails fast with an actionable message on malformed
or missing input rather than a raw traceback.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn

import structlog
import typer
from algo_core.logging import configure_logging, run_with_logging

from algo_analyze.ablation import AblationRow, build_ablation_table
from algo_analyze.config import AnalyzeConfig, load_analyze_config
from algo_analyze.equity import summary_line, write_consolidated
from algo_analyze.figures import (
    ablation_bars_figure,
    drawdown_curve_figure,
    equity_curve_figure,
)
from algo_analyze.reports import metrics_report, migration_inventory, significance_report
from algo_analyze.resultsdb import BuildRequest, RunsRoot, build_database

app = typer.Typer(
    name="algo-analyze",
    help="Metrics, deflated Sharpe, significance, ablation and figures from run artifacts.",
    no_args_is_help=True,
    add_completion=False,
)

# Module-level Option singletons: a list-typed param default can't be an inline call (ruff
# B008 — mutable param type), so the typer.Option lives here and is referenced below.
_SIGNIFICANCE_RUNS_OPTION = typer.Option(
    ..., "--runs", help="Exactly two run identifiers to compare (baseline, challenger)."
)
_ABLATION_RUNS_OPTION = typer.Option(
    ..., "--runs", help="Run identifiers to compare, in the order given (repeatable)."
)
_EQUITY_RUNS_OPTION = typer.Option(
    ..., "--run",
    help="A finished run's results directory holding run.json + equity.csv (repeatable).",
)
_EQUITY_LABELS_OPTION = typer.Option(
    None, "--label",
    help="strategy=Display label for the legend, the CSV and the summary (repeatable).",
)
_EQUITY_OUT_OPTION = typer.Option(
    ..., "--out", help="Directory for equity-consolidated.{csv,png,html}."
)
_RESULTS_ROOTS_OPTION = typer.Option(
    ..., "--runs-root",
    help="[LABEL=]DIR holding <strategy>/<stamp>/ run directories (repeatable).",
)
_RESULTS_OUT_OPTION = typer.Option(..., "--out", help="The SQLite file to build/update.")
_BARS_ROOT_OPTION = typer.Option(
    None, "--bars-root",
    help="Data root with parquet/forex/<SYMBOL>/m1/ partitions; enables entry_bars.",
)

results_db_app = typer.Typer(
    name="results-db", help="Build the SQLite results database the viewer opens.",
    no_args_is_help=True,
)
app.add_typer(results_db_app, name="results-db")


@app.callback()
def _root() -> None:
    """Tool entry point; subcommands are listed below."""


@app.command()
def version() -> None:
    """Print the installed version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("algo-analyze"))


@app.command()
def summary(
    out: str = typer.Option(
        "", "--out", help="CSV output path (default: <data_root>/analysis/summary.csv)."
    ),
) -> None:
    """Aggregate every successful experiment into one deterministic Chapter-4 CSV."""
    from algo_analyze.summary import (
        discover_experiment_manifests,
        load_summary_rows,
        write_summary_csv,
    )

    config = _configured("analyze")
    out_path = Path(out) if out else config.data_root / "analysis" / "summary.csv"
    try:
        manifests = discover_experiment_manifests(config.data_root)
        rows = load_summary_rows(manifests)
    except ValueError as exc:
        _fail(exc)

    write_summary_csv(rows, out_path)
    typer.echo(f"summary: {len(rows)} run(s) from {len(manifests)} experiment(s) -> {out_path}")


@app.command()
def metrics(
    run: str = typer.Option(..., "--run", help="Run identifier under <data_root>/runs/."),
    selection: str = typer.Option("", "--selection", help="Explicit selection-history JSON."),
) -> None:
    """Print schema-v2 descriptive metrics and DSR probability or unavailable reason."""
    config = _configured("analyze")
    try:
        result = metrics_report(
            config.data_root / "runs" / run, Path(selection) if selection else None
        )
    except (FileNotFoundError, ValueError) as exc:
        _fail(exc)
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


_BLOCK_LENGTHS = typer.Option(
    ..., "--block-length", help="Primary then sensitivity lengths; repeat."
)


@app.command()
def significance(
    runs: list[str] = _SIGNIFICANCE_RUNS_OPTION,
    block_length: list[int] = _BLOCK_LENGTHS,
    block_rule: str = typer.Option(..., "--block-rule", help="Prior rule/development source."),
    resamples: int = typer.Option(999, "--resamples", help="Stationary bootstrap draws, >=100."),
    seed: int = typer.Option(42, "--seed", help="Nonnegative deterministic seed."),
) -> None:
    """Compare paired daily portfolio means using a null-centered stationary bootstrap."""
    if len(runs) != 2:
        _fail(ValueError(f"--runs requires exactly two run identifiers, got {len(runs)}: {runs}"))
    config = _configured("analyze")
    try:
        result = significance_report(
            config.data_root,
            runs[0],
            runs[1],
            block_lengths=block_length,
            n_resamples=resamples,
            seed=seed,
            block_rule=block_rule,
        )
    except (FileNotFoundError, ValueError) as exc:
        _fail(exc)
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command("inference-inventory")
def inference_inventory() -> None:
    """List legacy runs and missing prerequisites without modifying historical artifacts."""
    # Per-run failures are classified inside migration_inventory (status: invalid); an
    # exception escaping here is a programming error and belongs to the logging boundary.
    config = _configured("analyze")
    typer.echo(json.dumps(migration_inventory(config.data_root), indent=2, sort_keys=True))


@app.command()
def ablation(
    runs: list[str] = _ABLATION_RUNS_OPTION,
    baseline: str = typer.Option(
        "", "--baseline", help="Baseline run identifier (default: the first --runs value)."
    ),
    figure: bool = typer.Option(False, "--figure", help="Also render an ablation bar-chart PDF."),
    out: str = typer.Option(
        "", "--out", help="Figure output path (default: <data_root>/analysis/ablation.pdf)."
    ),
) -> None:
    """Compare completed runs against a baseline and print the contribution table."""
    if not runs:
        _fail(ValueError("--runs requires at least one run identifier"))

    config = _configured("analyze")
    baseline_id = baseline or runs[0]
    run_dirs = [config.data_root / "runs" / run_id for run_id in runs]
    try:
        rows = build_ablation_table(run_dirs, baseline=baseline_id)
    except (FileNotFoundError, ValueError) as exc:
        _fail(exc)

    typer.echo(json.dumps([_ablation_row_dict(row) for row in rows], indent=2, sort_keys=True))
    if figure:
        out_path = Path(out) if out else config.data_root / "analysis" / "ablation.pdf"
        ablation_bars_figure(rows, out_path)
        typer.echo(f"figure: {out_path}")


@app.command()
def figures(
    run: str = typer.Option(..., "--run", help="Run identifier under <data_root>/runs/."),
    out: str = typer.Option(
        "", "--out", help="Output directory (default: <data_root>/runs/<run>/figures/)."
    ),
) -> None:
    """Render the equity-curve and drawdown-curve PDFs for one run."""
    config = _configured("analyze")
    run_dir = config.data_root / "runs" / run
    out_dir = Path(out) if out else run_dir / "figures"
    try:
        equity_path = equity_curve_figure(run_dir, out_dir / "equity.pdf")
        drawdown_path = drawdown_curve_figure(run_dir, out_dir / "drawdown.pdf")
    except (FileNotFoundError, ValueError) as exc:
        _fail(exc)

    typer.echo(f"figures: {equity_path}, {drawdown_path}")


@app.command("equity-curves")
def equity_curves(
    run: list[Path] = _EQUITY_RUNS_OPTION,
    label: list[str] | None = _EQUITY_LABELS_OPTION,
    out: Path = _EQUITY_OUT_OPTION,
) -> None:
    """Overlay several runs' equity curves on one time axis, one chained line per strategy.

    Runs are grouped by the strategy run.json names; consecutive windows of a strategy are
    re-based so each starts where the previous one ended (equity_raw * previous_end /
    this_start), so a fresh deposit per month does not show as a reset. Writes the
    long-format CSV, the PNG and a self-contained HTML comparison dashboard, prints one
    summary line per strategy. Exits 2 naming the
    run directory and the `algo-backtest statement --run` command when equity.csv is
    missing.
    """
    try:
        consolidation, paths = write_consolidated(run, label or [], out)
    except (FileNotFoundError, ValueError) as exc:
        _fail(exc)
    for summary in consolidation.summaries:
        typer.echo(f"equity-curves: {summary_line(summary)}")
    typer.echo(f"equity-curves: {paths.csv}")
    typer.echo(f"equity-curves: {paths.chart}")
    typer.echo(f"equity-curves: {paths.html}")


@results_db_app.command("build")
def results_db_build(
    runs_root: list[str] = _RESULTS_ROOTS_OPTION,
    out: Path = _RESULTS_OUT_OPTION,
    bars_root: Path | None = _BARS_ROOT_OPTION,
    bars_before: int = typer.Option(30, "--bars-before", help="Bars kept before each entry."),
    bars_after: int = typer.Option(30, "--bars-after", help="Bars kept after each entry."),
) -> None:
    """Ingest every finished run under each --runs-root into one SQLite file (upsert by run id).

    A run directory without run.json is still in progress: it is skipped and counted.
    A finished directory with a missing or malformed artifact stops the build naming the
    file. With --bars-root, the ±N bars around every entry are aggregated from the M1
    bid/ask mid into the run's bar size (entry_bars table).
    """
    try:
        request = BuildRequest(
            roots=[RunsRoot.parse(text) for text in runs_root], out=out, bars_root=bars_root,
            bars_before=bars_before, bars_after=bars_after,
        )
        report = build_database(request)
    except (FileNotFoundError, ValueError) as exc:
        _fail(exc)
    typer.echo(f"results-db: {len(report.ingested)} run(s) ingested -> {report.out}")
    if report.skipped:
        typer.echo(f"results-db: skipped {len(report.skipped)} unfinished run director"
                   f"{'y' if len(report.skipped) == 1 else 'ies'} (no run.json)")


def _configured(logger_name: str) -> AnalyzeConfig:
    """Resolve config and log its provenance, shared by every data-reading command."""
    log = structlog.get_logger(logger_name)
    config = load_analyze_config()
    for line in config.provenance:
        log.info("config", provenance=line)
    return config


def _ablation_row_dict(row: AblationRow) -> dict[str, object]:
    """Convert an ablation row to a JSON-serializable dict."""
    return {
        "run_id": row.run_id,
        "strategy": row.strategy,
        "symbol": row.symbol,
        "start": row.start,
        "end": row.end,
        "total_return": row.total_return,
        "sharpe": row.sharpe,
        "max_drawdown": row.max_drawdown,
        "hit_rate": row.hit_rate,
        "delta_total_return": row.delta_total_return,
    }


def _fail(exc: Exception) -> NoReturn:
    """Print an actionable error and exit non-zero (never a raw traceback)."""
    typer.echo(f"error: {exc}", err=True)
    raise typer.Exit(2) from exc


def main() -> None:
    """Console-script entry point (see [project.scripts])."""
    configure_logging()
    run_with_logging(app, logger_name="analyze")


if __name__ == "__main__":
    main()
