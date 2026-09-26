"""Run a strategy on materialized lean-data via LEAN — narrow orchestration.

Wires the price-only baseline strategies to the proven run path: validate inputs, run the
bundled algorithm in the pinned LEAN container against materialized lean-data, and parse
the result. A small strategy registry (not a plugin framework — a dict of entries) maps
each strategy to its bundled algorithm and its parameter validator, so a second strategy is
added without touching the run path.

Each strategy carries its own parameters (baseline-ma: fast/slow/size; baseline-meanrev:
window/band/size), validated by that strategy and passed to its algorithm verbatim.
`baseline`/`hybrid` additionally drive the real F1-F7 filter chain; `hybrid` (Spec 04h)
adds F4/news to `baseline`'s price-only chain, so it alone needs a second data mount —
`StrategySpec.needs_news_data` marks that in the registry instead of special-casing the
strategy name here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from algo_core.instrument import Instrument
from algo_core.layout import lean_data_dir_for

import algo_backtest
from algo_backtest.chain.filters.f4_news_context import news_coverage_problems
from algo_backtest.chain.filters.f7_model_io import load_families, require_families
from algo_backtest.container_paths import NEWS_DATA_ROOT, NEWS_SUBPATH
from algo_backtest.lean_runner import run_lean
from algo_backtest.results import RunResult, parse_results
from algo_backtest.strategies import load_strategy_chain_config

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


def _validate_baseline(params: Params) -> None:
    """baseline params: size in (0, 1] only (the F1+F2+F3+F5+F6+F7 config.yaml chain)."""
    _check_keys(params, {"size"}, "baseline")
    _validate_size(params, "baseline")


def _validate_hybrid(params: Params) -> None:
    """hybrid params: size in (0, 1] only (baseline's chain + F4/news, config.yaml `extends`)."""
    _check_keys(params, {"size"}, "hybrid")
    _validate_size(params, "hybrid")


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
    """A registered strategy: its bundled algorithm dir + its parameter validator.

    `needs_news_data`: whether `run_strategy` must also mount the real Spec 03
    (`algo-score`) news/event Parquet tree into the container — true only for
    `hybrid` (Spec 04h), whose algorithm reads it via F4NewsContextFilter.

    `model_file`: the F7 model filename the bundled algorithm loads, for strategies that
    run the meta-learner — the file a run's `--model` override replaces.
    """

    algo_dir: str
    validate: Callable[[Params], None]
    needs_news_data: bool = False
    model_file: str | None = None


# Adding a strategy is a registry entry + a bundled algorithm, no new run path.
#
# `buyhold`/`random`/`perfect_foresight` (Spec 04h, docs/experiments.md #0) are the
# engine-sanity-check strategies: known-answer algorithms that validate the backtester
# itself before any F1-F7 number is trusted.
#
# `baseline`/`hybrid` (2026-09-26, SMOKE TEST -- see technical-debt.md TD-51 and
# docs/stories/planned/04h-.../progress.md): the config.yaml-driven filter chain wired
# into a real LEAN algorithm. `baseline` runs F1+F2+F3+F5+F6+F7 (no F4/news); `hybrid`
# adds F4/news on top of the identical chain (`strategies/hybrid/config.yaml`'s
# `extends: baseline`). Both share the same known simplifications: F3's candlestick
# pattern is never populated (no real detector), F5/F6's account-risk features use
# fixed placeholder economics (no real ATR/margin model), and F7's meta-learner is
# trained on whatever short window its own `scripts/train_*_meta_learner.py` was
# pointed at -- not a statistically meaningful model. `hybrid` additionally inherits
# F4's own documented gap (real GDELT event-intensity veto, best-effort/ABSTAIN
# sentiment pending TD-48). These prove the chain wiring and order-execution join
# point work end to end against the real container; neither is a methodology result.
_F7_MODEL_FILE = "f7_meta_learner.json"

STRATEGIES: dict[str, StrategySpec] = {
    "baseline-ma": StrategySpec("baseline_ma", _validate_baseline_ma),
    "baseline-meanrev": StrategySpec("baseline_meanrev", _validate_baseline_meanrev),
    "baseline": StrategySpec("baseline", _validate_baseline, model_file=_F7_MODEL_FILE),
    "hybrid": StrategySpec(
        "hybrid", _validate_hybrid, needs_news_data=True, model_file=_F7_MODEL_FILE
    ),
    "buyhold": StrategySpec("experiment_zero/buyhold", _validate_buyhold),
    "random": StrategySpec("experiment_zero/random", _validate_random),
    "perfect_foresight": StrategySpec(
        "experiment_zero/perfect_foresight", _validate_perfect_foresight
    ),
}


def validate_run_inputs(
    strategy: str, params: Params, start: date, end: date, model: Path | None = None
) -> None:
    """Validate a run's inputs, raising ValueError with remediation (fail fast).

    Raises:
        ValueError: unknown strategy, a from-date after the to-date, strategy-specific
            parameter violations (wrong keys, non-numeric, out-of-range), or a `model`
            override for a strategy without an F7 model / pointing at no file.
    """
    if strategy not in STRATEGIES:
        raise ValueError(
            f"unknown strategy {strategy!r}; known strategies: {sorted(STRATEGIES)}"
        )
    if start > end:
        raise ValueError(f"from date ({start}) must not be after the to date ({end})")
    STRATEGIES[strategy].validate(params)
    _validate_model(strategy, model)


def _validate_model(strategy: str, model: Path | None) -> None:
    """The F7 model a run would load must exist and match the strategy's families.

    Checks the `--model` override, or the strategy's bundled model when none is given,
    so a mismatch fails on the host before any container starts.
    """
    spec = STRATEGIES[strategy]
    if spec.model_file is None:
        if model is not None:
            with_model = sorted(name for name, s in STRATEGIES.items() if s.model_file)
            raise ValueError(f"--model only applies to F7-driven strategies {with_model}")
        return
    path = model if model is not None else _algos_root() / spec.algo_dir / spec.model_file
    if not path.is_file():
        raise ValueError(f"F7 model {path} is not a file")
    require_families(
        load_families(path),
        load_strategy_chain_config(strategy).meta_learner_families,
        where=str(path),
    )


def _algos_root() -> Path:
    """The bundled algorithms directory inside the installed package."""
    return Path(algo_backtest.__file__).parent / "algos"


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


def news_coverage_errors(
    strategy: str, data_root: Path, symbol: str, start: date, end: date
) -> list[str]:
    """Why the event features cannot serve a news-driven run (always empty otherwise).

    Checked on the host before any container starts (see
    `f4_news_context.news_coverage_problems`), so a coverage gap — including the final
    bar's `end + 1` 00:00 decision — is a remediation-rich CLI error rather than a
    failure buried in the LEAN container log.
    """
    if not STRATEGIES[strategy].needs_news_data:
        return []
    return news_coverage_problems(data_root, symbol, start, end)


def _news_mounts(data_root: Path) -> dict[str, Path]:
    """Only the Spec 03 subtrees F4 reads — event features, plus sentiment when present.

    Mounted beneath `NEWS_SUBPATH` with the host's own `parquet/...` layout preserved, so
    `algo_score`'s path builders resolve unchanged against `NEWS_DATA_ROOT`. The
    sentiment tree is optional (TD-48); a bind mount of a missing host dir would make
    Docker create it, so it is only mounted when it exists.
    """
    mounts = {
        f"{NEWS_SUBPATH}/parquet/events/_features": data_root / "parquet" / "events" / "_features"
    }
    sentiment = data_root / "parquet" / "sentiment"
    if sentiment.is_dir():
        mounts[f"{NEWS_SUBPATH}/parquet/sentiment"] = sentiment
    return mounts


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
    model: Path | None = None,
) -> RunResult:
    """Run the named strategy's bundled algorithm over a window and parse its result.

    Mounts the instrument's materialized minute lean-data and passes the window plus the
    strategy's own parameters to the algorithm as backtest parameters. `strategy` must be a
    key of STRATEGIES (callers validate via `validate_run_inputs`). `broker_adapter` is the
    config-resolved brokerage-adapter name (Spec 04a) the algorithm applies via
    `ExecutionAlgorithm.init_execution` before the first bar. When the strategy's
    `needs_news_data` is set (Spec 04h's `hybrid`), the real Spec 03 (`algo-score`)
    event-feature (and, when present, sentiment) Parquet is additionally mounted
    read-only under the container's `NEWS_DATA_ROOT` (see `_news_mounts`), passed to the
    algorithm as its `news_data_root` parameter. `model` (validated by
    `validate_run_inputs`) replaces the strategy's bundled F7 model for this run only.
    """
    spec = STRATEGIES[strategy]
    algo_dir = _algos_root() / spec.algo_dir
    symbol_dir = lean_data_dir_for(data_root, instrument, "minute")
    subpath = symbol_dir.relative_to(data_root / "lean-data").as_posix()
    data_mounts = {subpath: symbol_dir}
    parameters = {
        "symbol": instrument.symbol,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "broker_adapter": broker_adapter,
        **params,
    }
    if spec.needs_news_data:
        data_mounts.update(_news_mounts(data_root))
        parameters["news_data_root"] = str(NEWS_DATA_ROOT)
    algo_files = {spec.model_file: model} if model is not None and spec.model_file else {}
    run = run_lean(
        algo_dir, results_dir, data_mounts=data_mounts,
        parameters=parameters, timeout=timeout, algo_files=algo_files,
    )
    return parse_results(results_dir, success=run.exit_code == 0)
