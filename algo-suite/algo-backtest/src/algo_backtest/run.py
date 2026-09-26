"""Run a strategy on materialized lean-data via LEAN — narrow orchestration.

Wires the price-only baseline strategies to the proven run path: validate inputs, run the
bundled algorithm in the pinned LEAN container against materialized lean-data, and parse
the result. A small strategy registry (not a plugin framework — a dict of entries) maps
each strategy to its bundled algorithm and its parameter validator, so a second strategy is
added without touching the run path.

Each strategy carries its own parameters (baseline-ma: fast/slow/size; baseline-meanrev:
window/band/size), validated by that strategy and passed to its algorithm verbatim. These
are all **price-only** strategies; the news/sentiment hybrid is later work, gated on
algo-score — nothing here claims an AI signal.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from algo_core.instrument import Instrument
from algo_core.layout import lean_data_dir_for

import algo_backtest
from algo_backtest.lean_runner import run_lean
from algo_backtest.results import RunResult, parse_results

Params = Mapping[str, str]


def _int_param(params: Params, name: str, strategy: str) -> int:
    """A required integer parameter (fail fast on absence / non-integer)."""
    raw = params.get(name)
    if raw is None:
        raise ValueError(f"{strategy} requires the {name!r} parameter")
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{strategy} {name!r} must be an integer, got {raw!r}") from exc


def _float_param(params: Params, name: str, strategy: str) -> float:
    """A required float parameter (fail fast on absence / non-numeric)."""
    raw = params.get(name)
    if raw is None:
        raise ValueError(f"{strategy} requires the {name!r} parameter")
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{strategy} {name!r} must be a number, got {raw!r}") from exc


def _check_keys(params: Params, expected: set[str], strategy: str) -> None:
    """Reject a params block whose keys are not exactly the strategy's (closed schema)."""
    extra = set(params) - expected
    missing = expected - set(params)
    if extra or missing:
        raise ValueError(
            f"{strategy} params must be exactly {sorted(expected)} "
            f"(missing={sorted(missing)}, unknown={sorted(extra)})"
        )


def _validate_size(params: Params, strategy: str) -> None:
    """The shared long-only, no-leverage sizing constraint."""
    size = _float_param(params, "size", strategy)
    if not 0 < size <= 1:
        raise ValueError(
            f"size ({size}) must be in range (0, 1] — {strategy} is long-only with no leverage"
        )


def _validate_baseline_ma(params: Params) -> None:
    """baseline-ma params: fast >= 1, fast < slow, size in (0, 1]."""
    _check_keys(params, {"fast", "slow", "size"}, "baseline-ma")
    fast = _int_param(params, "fast", "baseline-ma")
    slow = _int_param(params, "slow", "baseline-ma")
    _validate_size(params, "baseline-ma")
    if fast < 1:
        raise ValueError(f"fast period ({fast}) must be a positive integer")
    if fast >= slow:
        raise ValueError(f"fast period ({fast}) must be below the slow period ({slow})")


def _validate_baseline_meanrev(params: Params) -> None:
    """baseline-meanrev params: window >= 2, band > 0, size in (0, 1]."""
    _check_keys(params, {"window", "band", "size"}, "baseline-meanrev")
    window = _int_param(params, "window", "baseline-meanrev")
    band = _float_param(params, "band", "baseline-meanrev")
    _validate_size(params, "baseline-meanrev")
    if window < 2:
        raise ValueError(f"window ({window}) must be at least 2")
    if band <= 0:
        raise ValueError(f"band ({band}) must be positive")


def _validate_buyhold(params: Params) -> None:
    """buyhold params: size in (0, 1] only (docs/experiments.md #0, Spec 04h)."""
    _check_keys(params, {"size"}, "buyhold")
    _validate_size(params, "buyhold")


def _validate_random(params: Params) -> None:
    """random params: size in (0, 1], seed any integer (docs/experiments.md #0, Spec 04h)."""
    _check_keys(params, {"size", "seed"}, "random")
    _validate_size(params, "random")
    _int_param(params, "seed", "random")


def _validate_perfect_foresight(params: Params) -> None:
    """perfect_foresight params: size in (0, 1] only (docs/experiments.md #0, Spec 04h)."""
    _check_keys(params, {"size"}, "perfect_foresight")
    _validate_size(params, "perfect_foresight")


@dataclass(frozen=True)
class StrategySpec:
    """A registered strategy: its bundled algorithm dir + its parameter validator."""

    algo_dir: str
    validate: Callable[[Params], None]


# The price-only strategies. Adding one is a registry entry + a bundled algorithm, no new
# run path. (The news/sentiment hybrid is not here — it is gated on algo-score.)
#
# `buyhold`/`random`/`perfect_foresight` (Spec 04h, docs/experiments.md #0) are the
# engine-sanity-check strategies: known-answer algorithms that validate the backtester
# itself before any F1-F7 number is trusted. `baseline`/`hybrid` (the config.yaml-driven
# F1-F7 filter chain, `algo_backtest/strategies.py`) are **not yet registered here** — see
# docs/technical-debt.md's Spec 04h entry: the filter-chain-to-LEAN-native-indicator wiring
# (F1-F3), the persisted meta-learner artifact load, and the news Parquet read all need to
# happen *inside* the pinned LEAN container's `initialize()`/`on_data()`, which is real
# remaining work this pass did not complete or verify.
STRATEGIES: dict[str, StrategySpec] = {
    "baseline-ma": StrategySpec("baseline_ma", _validate_baseline_ma),
    "baseline-meanrev": StrategySpec("baseline_meanrev", _validate_baseline_meanrev),
    "buyhold": StrategySpec("experiment_zero/buyhold", _validate_buyhold),
    "random": StrategySpec("experiment_zero/random", _validate_random),
    "perfect_foresight": StrategySpec(
        "experiment_zero/perfect_foresight", _validate_perfect_foresight
    ),
}


def validate_run_inputs(strategy: str, params: Params, start: date, end: date) -> None:
    """Validate a run's inputs, raising ValueError with remediation (fail fast).

    Raises:
        ValueError: unknown strategy, a from-date after the to-date, or strategy-specific
            parameter violations (wrong keys, non-numeric, out-of-range).
    """
    if strategy not in STRATEGIES:
        raise ValueError(
            f"unknown strategy {strategy!r}; known strategies: {sorted(STRATEGIES)}"
        )
    if start > end:
        raise ValueError(f"from date ({start}) must not be after the to date ({end})")
    STRATEGIES[strategy].validate(params)


def lean_data_covers(data_root: Path, instrument: Instrument, start: date, end: date) -> bool:
    """Whether any materialized minute day-zip falls within the [start, end] window.

    Lightweight (one directory listing, filename dates only — no content scan): proves
    the requested window has *some* data, so a stale month no longer satisfies a request
    for an uncovered window.
    """
    directory = lean_data_dir_for(data_root, instrument, "minute")
    if not directory.is_dir():
        return False
    for path in directory.glob("*_quote.zip"):
        try:
            day = datetime.strptime(path.name[:8], "%Y%m%d").date()
        except ValueError:
            continue
        if start <= day <= end:
            return True
    return False


def run_strategy(
    strategy: str,
    *,
    data_root: Path,
    instrument: Instrument,
    start: date,
    end: date,
    params: Params,
    results_dir: Path,
    timeout: int,
    broker_adapter: str,
) -> RunResult:
    """Run the named strategy's bundled algorithm over a window and parse its result.

    Mounts the instrument's materialized minute lean-data and passes the window plus the
    strategy's own parameters to the algorithm as backtest parameters. `strategy` must be a
    key of STRATEGIES (callers validate via `validate_run_inputs`). `broker_adapter` is the
    config-resolved brokerage-adapter name (Spec 04a) the algorithm applies via
    `ExecutionAlgorithm.init_execution` before the first bar.
    """
    algo_dir = Path(algo_backtest.__file__).parent / "algos" / STRATEGIES[strategy].algo_dir
    symbol_dir = lean_data_dir_for(data_root, instrument, "minute")
    subpath = symbol_dir.relative_to(data_root / "lean-data").as_posix()
    parameters = {
        "symbol": instrument.symbol,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "broker_adapter": broker_adapter,
        **params,
    }
    run = run_lean(
        algo_dir, results_dir, data_mounts={subpath: symbol_dir},
        parameters=parameters, timeout=timeout,
    )
    return parse_results(results_dir, success=run.exit_code == 0)
