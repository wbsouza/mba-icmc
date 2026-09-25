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

from algo_analyze._trades import trade_returns
from algo_analyze.ablation import AblationRow, build_ablation_table
from algo_analyze.config import AnalyzeConfig, load_analyze_config
from algo_analyze.deflated import deflated_sharpe
from algo_analyze.figures import (
    ablation_bars_figure,
    drawdown_curve_figure,
    equity_curve_figure,
)
from algo_analyze.significance import DEFAULT_ALPHA, MCPResult, mcp_test

app = typer.Typer(
    name="algo-analyze",
    help="Metrics, deflated Sharpe, significance, ablation and figures from run artifacts.",
    no_args_is_help=True,
    add_completion=False,
)

# Plausibility band from docs/experiments.md §7.1: a deflated Sharpe above this, after
# costs, sits above the FinDPO anchor and the literature's plausible range — investigate
# (leakage, cost model, look-ahead) before reporting it, don't just cite it.
_DEFLATED_SHARPE_INVESTIGATE_ABOVE = 2.0

_DEFAULT_MCP_PERMUTATIONS = 1000
_DEFAULT_MCP_SEED = 42

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
    trials: int = typer.Option(
        1, "--trials", help="Number of independent strategy trials searched (for deflation)."
    ),
) -> None:
    """Print headline metrics plus the deflated Sharpe ratio for one run.

    Deflation assumes a normal return distribution (skew 0, kurtosis 3) unless the run
    has fewer than two closed trades, in which case the headline Sharpe is reported
    undeflated with an explicit caveat rather than failing — empirical skew/kurtosis
    estimation from the trade series is a later refinement (see SPEC.md open items).
    """
    from algo_backtest.metrics import metrics_from_artifact  # type: ignore[import-untyped]

    config = _configured("analyze")
    run_dir = config.data_root / "runs" / run
    try:
        headline = metrics_from_artifact(run_dir / "metrics.json")
        returns = trade_returns(run_dir)
    except (FileNotFoundError, ValueError) as exc:
        _fail(exc)

    result: dict[str, object] = {
        **headline.as_dict(),
        "n_trades": len(returns),
        "n_trials": trials,
    }
    flags: list[str] = []
    if len(returns) < 2:
        result["deflated_sharpe"] = None
        result["note"] = "fewer than 2 closed trades; deflated Sharpe not computed"
    else:
        try:
            deflated = deflated_sharpe(
                observed_sharpe=headline.sharpe, n_returns=len(returns), n_trials=trials
            )
        except ValueError as exc:
            _fail(exc)
        result["deflated_sharpe"] = deflated
        if deflated > _DEFLATED_SHARPE_INVESTIGATE_ABOVE:
            flags.append(
                f"deflated Sharpe {deflated:.4f} > {_DEFLATED_SHARPE_INVESTIGATE_ABOVE}: "
                "investigate before reporting (docs/experiments.md §7.1)"
            )
    result["flags"] = flags
    typer.echo(json.dumps(result, indent=2, sort_keys=True))


@app.command()
def significance(
    runs: list[str] = _SIGNIFICANCE_RUNS_OPTION,
    permutations: int = typer.Option(
        _DEFAULT_MCP_PERMUTATIONS, "--permutations", help="Number of Monte-Carlo permutations."
    ),
    seed: int = typer.Option(_DEFAULT_MCP_SEED, "--seed", help="Fixed permutation seed."),
) -> None:
    """Run the Monte-Carlo Permutation Test between two runs' trade-return samples."""
    if len(runs) != 2:
        _fail(ValueError(f"--runs requires exactly two run identifiers, got {len(runs)}: {runs}"))

    config = _configured("analyze")
    run_a, run_b = runs
    try:
        returns_a = trade_returns(config.data_root / "runs" / run_a)
        returns_b = trade_returns(config.data_root / "runs" / run_b)
        result = mcp_test(returns_a, returns_b, n_permutations=permutations, seed=seed)
    except (FileNotFoundError, ValueError) as exc:
        _fail(exc)

    typer.echo(json.dumps(_mcp_result_dict(result, run_a, run_b, seed), indent=2, sort_keys=True))


@app.command()
def ablation(
    runs: list[str] = _ABLATION_RUNS_OPTION,
    baseline: str = typer.Option(
        "", "--baseline", help="Baseline run identifier (default: the first --runs value)."
    ),
    figure: bool = typer.Option(
        False, "--figure", help="Also render an ablation bar-chart PDF."
    ),
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


def _mcp_result_dict(result: MCPResult, run_a: str, run_b: str, seed: int) -> dict[str, object]:
    """Convert an MCP result to a JSON-serializable dict, recording the run pair + seed."""
    return {
        "run_a": run_a,
        "run_b": run_b,
        "p_value": result.p_value,
        "reject_null": result.reject_null,
        "alpha": DEFAULT_ALPHA,
        "observed_difference": result.observed_difference,
        "n_permutations": result.n_permutations,
        "seed": seed,
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
