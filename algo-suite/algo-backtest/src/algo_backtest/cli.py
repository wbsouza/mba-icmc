"""CLI for algo-backtest."""

from __future__ import annotations

from pathlib import Path

import structlog
import typer
from algo_core.logging import configure_logging, run_with_logging

app = typer.Typer(
    name="algo-backtest",
    help="Materialize lean-data, run the meta-learner + deterministic filter chain on LEAN.",
    no_args_is_help=True,
    add_completion=False,
)


# Module-level Option singleton: a list-typed param default can't be an inline call (ruff
# B008 — mutable param type), so the typer.Option lives here and is referenced below.
_PARAM_OPTION = typer.Option(
    None, "--param", help="Strategy parameter key=value, repeatable (e.g. --param fast=3)."
)
_STRATEGIES_DIR_OPTION = typer.Option(
    None,
    "--strategies-dir",
    help="Directory of extra strategies/<name>/config.yaml files (a variant there may "
    "`extends:` a bundled strategy); the bundled strategies stay available.",
)
_STATEMENT_OUT_OPTION = typer.Option(
    None, "--out", help="Directory for statement.md + equity.png (default: the run directory)."
)
_MODEL_OPTION = typer.Option(
    None,
    "--model",
    help="F7 model JSON to use instead of the strategy's bundled one (baseline/hybrid "
    "only); the algorithm logs its SHA-256.",
)


def _parse_params(items: list[str]) -> dict[str, str]:
    """Parse repeated --param key=value into a dict (fail fast on a malformed item)."""
    params: dict[str, str] = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise ValueError(f"--param must be key=value, got {item!r}")
        params[key] = value
    return params


def _fresh_results_dir(data_root: Path, label: str) -> Path:
    """A fresh, unique results dir under runs/<label>/ so a run never reads stale files."""
    from datetime import UTC, datetime
    from time import monotonic_ns

    stamp = f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{monotonic_ns():x}"
    results_dir = data_root / "runs" / label / stamp
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


@app.callback()
def _root() -> None:
    """Tool entry point; subcommands are listed below."""


@app.command()
def version() -> None:
    """Print the installed version."""
    from importlib.metadata import version as pkg_version

    typer.echo(pkg_version("algo-backtest"))


@app.command()
def materialize(
    symbol: str = typer.Option(..., "--symbol", help="Instrument symbol, e.g. EURUSD."),
    year: int = typer.Option(..., "--year", help="Year of the canonical month to materialize."),
    month: int = typer.Option(..., "--month", min=1, max=12, help="Month (1-12)."),
) -> None:
    """Materialize one month of canonical Parquet into the durable lean-data store."""
    from algo_core.instrument import build_instrument

    from algo_backtest.config import load_backtest_config
    from algo_backtest.materialize import materialize_month

    log = structlog.get_logger("backtest")
    config = load_backtest_config()
    for line in config.provenance:
        log.info("config", provenance=line)

    instrument = build_instrument(symbol)
    result = materialize_month(config.data_root, instrument, year, month, config.oanda_data_tz)
    typer.echo(
        f"{result.status}: {len(result.written)} day(s) written, "
        f"{result.skipped_days} skipped (tz={config.oanda_data_tz})"
    )


@app.command(name="lean-smoke")
def lean_smoke(
    timeout: int = typer.Option(
        600, "--timeout", envvar="LEAN_RUN_TIMEOUT", help="Seconds to wait for the run."
    ),
) -> None:
    """Run the bundled smoke-trade algorithm against materialized EUR/USD lean-data.

    Proves the run path end to end (materialized lean-data -> LEAN -> /Results -> one
    closed trade). Requires EUR/USD already materialized under the configured data root
    (run `materialize` first). Exits non-zero if the run fails or no trade closed.
    """
    from algo_core.instrument import build_instrument
    from algo_core.layout import lean_data_dir_for

    from algo_backtest.config import load_backtest_config
    from algo_backtest.lean_runner import run_lean
    from algo_backtest.results import parse_results

    log = structlog.get_logger("backtest")
    config = load_backtest_config()
    for line in config.provenance:
        log.info("config", provenance=line)

    eurusd = build_instrument("EURUSD")
    algo_dir = Path(__file__).parent / "algos" / "smoke_trade"
    symbol_dir = lean_data_dir_for(config.data_root, eurusd, "minute")
    if not any(symbol_dir.glob("*_quote.zip")):
        typer.echo(
            f"no lean-data for EURUSD under {symbol_dir}; run "
            f"`algo-backtest materialize --symbol EURUSD ...` first",
            err=True,
        )
        raise typer.Exit(2)

    results_dir = _fresh_results_dir(config.data_root, "lean-smoke")
    run = run_lean(
        algo_dir, results_dir, data_mounts={"forex/oanda/minute/eurusd": symbol_dir},
        timeout=timeout,
    )
    result = parse_results(results_dir, success=run.exit_code == 0)
    typer.echo(
        f"lean-smoke: success={result.success} closed_trades={result.closed_trades} "
        f"results={result.raw_results_path}"
    )
    if not result.success or result.closed_trades < 1:
        raise typer.Exit(1)


def _print_strategy_parameters(strategy: str, strategies_dir: Path | None) -> None:
    """Execution bootstrap: print every resolved strategy parameter and the config.yaml
    (or default) it came from, before any data check or container start, so a run is
    auditable from its console output alone. Code-registered strategies have none."""
    from algo_backtest.run import resolve_strategy
    from algo_backtest.strategies import explain_lines, load_strategy_chain_config

    if resolve_strategy(strategy, strategies_root=strategies_dir).model_file is None:
        return
    for line in explain_lines(load_strategy_chain_config(strategy, root=strategies_dir)):
        typer.echo(f"strategy[{strategy}] {line}")


@app.command()
def run(
    strategy: str = typer.Option("baseline-ma", "--strategy", help="Strategy name."),
    symbol: str = typer.Option("EURUSD", "--symbol", help="Instrument symbol."),
    from_: str = typer.Option(..., "--from", help="Backtest start date, YYYY-MM-DD."),
    to: str = typer.Option(..., "--to", help="Backtest end date, YYYY-MM-DD."),
    param: list[str] | None = _PARAM_OPTION,
    timeout: int = typer.Option(
        600, "--timeout", envvar="LEAN_RUN_TIMEOUT", help="Seconds to wait for the run."
    ),
    model: Path | None = _MODEL_OPTION,
    strategies_dir: Path | None = _STRATEGIES_DIR_OPTION,
) -> None:
    """Run a single strategy over a window and report success + closed-trade count.

    Parameters are strategy-specific, passed as repeated `--param key=value` and validated
    by the strategy (baseline-ma: fast/slow/size/cash; baseline-meanrev: window/band/size/cash;
    the config.yaml chain strategies cash only — F6's trade plan sizes each order; every
    strategy takes cash, the account's starting deposit). For multi-strategy comparison use
    `experiment run`.
    """
    import json as _json
    from datetime import datetime

    from algo_core.instrument import build_instrument

    from algo_backtest.artifacts import RunManifest, write_run_artifacts
    from algo_backtest.chain.filters.f4_news_context import news_build_command
    from algo_backtest.config import load_backtest_config
    from algo_backtest.metrics import metrics_from_results
    from algo_backtest.run import (
        lean_data_covers,
        news_coverage_errors,
        run_strategy,
        validate_run_inputs,
    )

    try:
        start = datetime.strptime(from_, "%Y-%m-%d").date()
        end = datetime.strptime(to, "%Y-%m-%d").date()
    except ValueError:
        typer.echo("--from/--to must be dates in YYYY-MM-DD form", err=True)
        raise typer.Exit(2) from None
    try:
        params = _parse_params(param or [])
        validate_run_inputs(strategy, params, start, end, model, strategies_root=strategies_dir)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc

    log = structlog.get_logger("backtest")
    config = load_backtest_config()
    for line in config.provenance:
        log.info("config", provenance=line)

    _print_strategy_parameters(strategy, strategies_dir)

    instrument = build_instrument(symbol)
    if not lean_data_covers(config.data_root, instrument, start, end):
        typer.echo(
            f"no lean-data for {symbol} covering {start}..{end}; run "
            f"`algo-backtest materialize --symbol {symbol} ...` for that window first",
            err=True,
        )
        raise typer.Exit(2)

    news_errors = news_coverage_errors(
        strategy, config.data_root, symbol, start, end, strategies_root=strategies_dir
    )
    if news_errors:
        typer.echo(
            f"GDELT event features cannot serve {strategy} over {start}..{end}: "
            f"{'; '.join(news_errors)}; build them first: `{news_build_command(start, end)}`",
            err=True,
        )
        raise typer.Exit(2)

    results_dir = _fresh_results_dir(config.data_root, strategy)
    result = run_strategy(
        strategy, data_root=config.data_root, instrument=instrument, start=start, end=end,
        params=params, results_dir=results_dir, timeout=timeout,
        broker_adapter=config.broker_adapter, model=model, strategies_root=strategies_dir,
    )
    typer.echo(
        f"run[{strategy}]: success={result.success} closed_trades={result.closed_trades} "
        f"results={result.raw_results_path}"
    )
    # A flat strategy (no crossover in the window) is a valid result, not an error;
    # only a failed engine run is non-zero.
    if not result.success:
        if result.error:
            typer.echo(f"error: {result.error}", err=True)
        raise typer.Exit(1)

    # Parse LEAN's (large) result JSON once; derive both the ledger and the metrics from
    # it (the sweep is performance-critical — no second read). E1: persist artifacts;
    # E2: report the four headline metrics.
    results_doc = _json.loads(result.raw_results_path.read_text())
    metrics = metrics_from_results(results_doc, source=result.raw_results_path)
    manifest = RunManifest(
        strategy=strategy, symbol=symbol, start=start.isoformat(), end=end.isoformat(),
        params=params, success=result.success, closed_trades=result.closed_trades,
        broker_adapter=config.broker_adapter,
    )
    closed_trades = results_doc["totalPerformance"]["closedTrades"]
    write_run_artifacts(results_dir, manifest, closed_trades, metrics)
    typer.echo(
        f"metrics: total_return={metrics.total_return} sharpe={metrics.sharpe} "
        f"max_drawdown={metrics.max_drawdown} hit_rate={metrics.hit_rate}"
    )
    # Story 12 item H: every simulation ends with a broker-style statement + equity chart
    # built from the artifacts just written (regenerable later via `statement --run`).
    _emit_statement(results_dir, None)


def _emit_statement(run_dir: Path, out_dir: Path | None) -> None:
    """Write statement.md + equity.png for `run_dir`; print the A/C summary and both paths."""
    from algo_backtest.statement import (
        build_statement,
        load_run_artifacts,
        summary_lines,
        write_statement_files,
    )

    statement = build_statement(load_run_artifacts(run_dir))
    paths = write_statement_files(statement, out_dir if out_dir is not None else run_dir)
    for line in summary_lines(statement):
        typer.echo(f"statement: {line}")
    typer.echo(f"statement: {paths.statement}")
    typer.echo(f"equity chart: {paths.chart}")


@app.command(name="explain-strategy")
def explain_strategy(
    name: str = typer.Argument(..., help="Strategy name (bundled, or under --strategies-dir)."),
    strategies_dir: Path | None = _STRATEGIES_DIR_OPTION,
) -> None:
    """Print every resolved parameter of a strategy and the config.yaml that set it.

    One line per parameter, `key = value  # <source>`; the source is the file in the
    `extends:` chain that set the value, or `default` for a value the loader filled in.
    The same map is written next to every run as `strategy-provenance.json`.
    """
    from algo_backtest.run import resolve_strategy
    from algo_backtest.strategies import explain_lines, load_strategy_chain_config

    try:
        spec = resolve_strategy(name, strategies_root=strategies_dir)
        if spec.model_file is None:
            raise ValueError(f"{name!r} is a code-registered strategy without a config.yaml")
        config = load_strategy_chain_config(name, root=strategies_dir)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    for line in explain_lines(config):
        typer.echo(line)


@app.command()
def metrics(
    run_dir: str = typer.Option(..., "--run", help="A finished run's results directory."),
) -> None:
    """Print the four Chapter-4 metrics for a finished run.

    Prefers the persisted metrics.json artifact (written by `run`); falls back to
    extracting them from LEAN's result JSON if the run predates metrics.json.
    """
    from algo_backtest.metrics import extract_metrics, metrics_from_artifact
    from algo_backtest.results import find_result_json

    metrics_json = Path(run_dir) / "metrics.json"
    try:
        if metrics_json.is_file():
            m = metrics_from_artifact(metrics_json)
        else:
            m = extract_metrics(find_result_json(Path(run_dir)))
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(
        f"metrics: total_return={m.total_return} sharpe={m.sharpe} "
        f"max_drawdown={m.max_drawdown} hit_rate={m.hit_rate}"
    )


@app.command()
def statement(
    run_dir: str = typer.Option(..., "--run", help="A finished run's results directory."),
    out: Path | None = _STATEMENT_OUT_OPTION,
) -> None:
    """Regenerate the broker-style statement and equity chart for a finished run.

    Reads run.json, trades.json, LEAN's result JSON and its order-events sibling (plus
    strategy-config.json, strategy-provenance.json and trade-plans.json when present) and
    writes statement.md + equity.png; prints the A/C summary. Exits 2 when a required
    artifact is missing or malformed, naming the file.
    """
    try:
        _emit_statement(Path(run_dir), out)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc


experiment_app = typer.Typer(
    name="experiment",
    help="Run reproducible backtest experiments (the Chapter-4 experiment contract).",
    no_args_is_help=True,
)
app.add_typer(experiment_app)


@experiment_app.command("run")
def experiment_run(
    spec: str = typer.Option(..., "--spec", help="Path to an experiment spec YAML."),
    timeout: int = typer.Option(
        600, "--timeout", envvar="LEAN_RUN_TIMEOUT", help="Seconds to wait per run."
    ),
) -> None:
    """Run every run in an experiment spec; write per-run dirs + a manifest."""
    from algo_backtest.config import load_backtest_config
    from algo_backtest.experiment import load_experiment, run_experiment

    spec_path = Path(spec)
    if not spec_path.is_file():
        typer.echo(f"experiment spec not found: {spec_path}", err=True)
        raise typer.Exit(2)

    log = structlog.get_logger("backtest")
    config = load_backtest_config()
    for line in config.provenance:
        log.info("config", provenance=line)

    try:
        experiment = load_experiment(spec_path)
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    try:
        result = run_experiment(
            experiment, data_root=config.data_root, timeout=timeout,
            broker_adapter=config.broker_adapter,
        )
    except ValueError as exc:  # invalid run / window not materialized
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    except RuntimeError as exc:  # a run's engine execution failed
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc

    typer.echo(
        f"experiment[{experiment.name}]: {len(result.outcomes)} run(s) "
        f"-> {result.manifest_path}"
    )


def main() -> None:
    """Console-script entry point (see [project.scripts])."""
    configure_logging()
    run_with_logging(app, logger_name="backtest")


if __name__ == "__main__":
    main()
