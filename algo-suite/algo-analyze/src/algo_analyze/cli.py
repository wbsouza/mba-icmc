"""CLI for algo-analyze.

Wires the library modules into the exact command surface `docs/experiments.md` §2/§3
specifies: `summary`, `metrics`, `significance`, `ablation`, `figures`. Each command
resolves the data root via the shared config convention, reads run artifacts under
`<data_root>/runs/<run-id>/`, and fails fast with an actionable message on malformed
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
from algo_analyze.figures import (
    ablation_bars_figure,
    drawdown_curve_figure,
    equity_curve_figure,
)
from algo_analyze.reports import metrics_report, migration_inventory, significance_report

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
