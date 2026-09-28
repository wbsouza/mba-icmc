"""Run a strategy on materialized lean-data via LEAN — narrow orchestration.

Wires the price-only baseline strategies to the proven run path: validate inputs, run the
bundled algorithm in the pinned LEAN container against materialized lean-data, and parse
the result. A small strategy registry (not a plugin framework — a dict of entries) maps
each strategy to its bundled algorithm and its parameter validator, so a second strategy is
added without touching the run path.

Each strategy carries its own parameters (baseline-ma: fast/slow/size/cash;
baseline-meanrev: window/band/size/cash; buyhold/perfect_foresight: size/cash; random:
size/seed/cash/entry_probability/exit_probability/long_probability; the config.yaml chain
strategies baseline/baseline-dsha/hybrid: cash only — F6's trade plan sizes every order,
story 12), validated by that strategy and passed to its algorithm verbatim. `cash` is the
account's starting deposit and is common to every strategy (story 12, TD-65), so a chain
strategy and an engine control can be compared from the same deposit.
`baseline`/`hybrid` additionally drive the real F1-F7 filter chain; `hybrid` (Spec 04h)
adds F4/news to `baseline`'s price-only chain, so it alone needs a second data mount —
`StrategySpec.needs_news_data` marks that in the registry instead of special-casing the
strategy name here.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from functools import partial
from pathlib import Path

from algo_core.atomicio import write_text_atomic
from algo_core.instrument import Instrument
from algo_core.layout import lean_data_dir_for

import algo_backtest
from algo_backtest.chain.filters.f4_news_context import news_coverage_problems
from algo_backtest.chain.filters.f7_meta_learner import F7Config
from algo_backtest.chain.filters.f7_model_io import (
    load_families,
    load_provenance,
    require_families,
)
from algo_backtest.chain.price_features import (
    PriceFeatureConfig,
    parse_price_features_config,
    price_features_mapping,
)
from algo_backtest.container_paths import NEWS_DATA_ROOT, NEWS_SUBPATH
from algo_backtest.lean_runner import run_lean
from algo_backtest.perception.tick_activity import activity_provenance
from algo_backtest.results import RunResult, parse_results
from algo_backtest.strategies import (
    StrategyChainConfig,
    load_strategy_chain_config,
    resolved_yaml,
    strategy_exists,
)
from algo_backtest.strategies import strategies_root as bundled_strategies_root

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
    """baseline-ma params: fast >= 1, fast < slow, size in (0, 1], cash > 0."""
    _check_keys(params, {"fast", "slow", "size", "cash"}, "baseline-ma")
    fast = _int_param(params, "fast", "baseline-ma")
    slow = _int_param(params, "slow", "baseline-ma")
    _validate_size(params, "baseline-ma")
    _validate_cash(params, "baseline-ma")
    if fast < 1:
        raise ValueError(f"fast period ({fast}) must be a positive integer")
    if fast >= slow:
        raise ValueError(f"fast period ({fast}) must be below the slow period ({slow})")


def _validate_baseline_meanrev(params: Params) -> None:
    """baseline-meanrev params: window >= 2, band > 0, size in (0, 1], cash > 0."""
    _check_keys(params, {"window", "band", "size", "cash"}, "baseline-meanrev")
    window = _int_param(params, "window", "baseline-meanrev")
    band = _float_param(params, "band", "baseline-meanrev")
    _validate_size(params, "baseline-meanrev")
    _validate_cash(params, "baseline-meanrev")
    if window < 2:
        raise ValueError(f"window ({window}) must be at least 2")
    if band <= 0:
        raise ValueError(f"band ({band}) must be positive")


def _validate_cash(params: Params, strategy: str) -> None:
    """Every strategy's starting deposit: the account's initial cash, strictly positive."""
    cash = _float_param(params, "cash", strategy)
    if cash <= 0:
        raise ValueError(
            f"cash ({cash}) must be positive — the account's starting deposit for {strategy}, "
            "e.g. --param cash=10000"
        )


def _validate_chain_params(params: Params, strategy: str) -> None:
    """The config.yaml-driven chain strategies share one closed param set: cash only.

    Position size is not a run parameter: the executor sizes every order from F6's trade
    plan (`capital_mgmt.risk_per_trade` and the stop distance, story 12 item D).
    """
    _check_keys(params, {"cash"}, strategy)
    _validate_cash(params, strategy)


def _validate_buyhold(params: Params) -> None:
    """buyhold params: size in (0, 1], cash > 0 (docs/experiments.md #0, Spec 04h)."""
    _check_keys(params, {"size", "cash"}, "buyhold")
    _validate_size(params, "buyhold")
    _validate_cash(params, "buyhold")


def _validate_probability(
    params: Params, name: str, strategy: str, *, zero_allowed: bool
) -> None:
    """A per-bar probability parameter: in (0, 1], or [0, 1] when zero is a valid split."""
    value = _float_param(params, name, strategy)
    low_ok = value >= 0 if zero_allowed else value > 0
    if not (low_ok and value <= 1):
        bounds = "[0, 1]" if zero_allowed else "(0, 1]"
        raise ValueError(
            f"{name} ({value}) must be in range {bounds} — {strategy}'s per-bar probability, "
            f"e.g. --param {name}=0.5"
        )


def _validate_random(params: Params) -> None:
    """random params (docs/experiments.md #0): size in (0, 1], seed any integer, cash > 0,
    entry/exit probabilities in (0, 1], long_probability in [0, 1] (0.5 = unbiased coin).

    Every behaviour parameter of the random control is external (story 12): the per-bar
    chance of entering while flat, of exiting while invested, and the BUY share of entries.
    """
    _check_keys(
        params,
        {"size", "seed", "cash", "entry_probability", "exit_probability", "long_probability"},
        "random",
    )
    _validate_size(params, "random")
    _int_param(params, "seed", "random")
    _validate_cash(params, "random")
    _validate_probability(params, "entry_probability", "random", zero_allowed=False)
    _validate_probability(params, "exit_probability", "random", zero_allowed=False)
    _validate_probability(params, "long_probability", "random", zero_allowed=True)


def _validate_perfect_foresight(params: Params) -> None:
    """perfect_foresight params: size in (0, 1], cash > 0 (docs/experiments.md #0, Spec 04h)."""
    _check_keys(params, {"size", "cash"}, "perfect_foresight")
    _validate_size(params, "perfect_foresight")
    _validate_cash(params, "perfect_foresight")


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
# docs/stories/done/2026-09-26-04h-algo-backtest-hybrid-integration/progress.md): the
# config.yaml-driven filter chain on the shared `engine/chain_algorithm.py`. `baseline`
# runs F1+F2+F3+F5+F6+F7 (no F4/news); `hybrid` adds F4/news on top of the identical
# chain (`strategies/hybrid/config.yaml`'s `extends: baseline`). Known simplifications:
# The bundled configurations keep F3 detection disabled; Story 13 enables TA-Lib only
# for explicitly configured, freshly trained variants. F5/F6 use the resolved risk and
# execution plan (Story 12), and the bundled F7 models come from the
# walk-forward split recorded in each model's provenance (2015-02..07 in-sample,
# 2015-08..2016-01 held out). `hybrid`'s F4 sentiment half stays best-effort/ABSTAIN
# pending TD-48 (its GDELT event-intensity veto is real). Wiring proof, not a Chapter-4
# methodology result.
_F7_MODEL_FILE = "f7_meta_learner.json"
_RESOLVED_STRATEGY_FILE = "strategy.yaml"

# The code-registered strategies: the legacy price-only baselines and the engine
# controls. The config.yaml chain strategies (baseline, baseline-dsha, hybrid and any
# YAML variant, bundled or in an external --strategies-dir) are NOT listed here: since
# 2026-09-27 (story 09) `resolve_strategy` derives their spec from the YAML itself, so a
# new strategy is a new config.yaml, never a code change.
STRATEGIES: dict[str, StrategySpec] = {
    "baseline-ma": StrategySpec("baseline_ma", _validate_baseline_ma),
    "baseline-meanrev": StrategySpec("baseline_meanrev", _validate_baseline_meanrev),
    "buyhold": StrategySpec("experiment_zero/buyhold", _validate_buyhold),
    "random": StrategySpec("experiment_zero/random", _validate_random),
    "perfect_foresight": StrategySpec(
        "experiment_zero/perfect_foresight", _validate_perfect_foresight
    ),
}


def resolve_strategy(strategy: str, *, strategies_root: Path | None = None) -> StrategySpec:
    """The spec for `strategy`: a registry entry, or one derived from its config.yaml.

    A chain strategy's YAML decides everything the run path needs: the LEAN algorithm
    that hosts it (`algos/hybrid` when `f4_news_context` is listed, else `algos/baseline`),
    whether the news Parquet is mounted, and that it takes the `cash` param alone.
    `strategies_root` is an external directory searched before the bundled one.

    Raises:
        ValueError: no registry entry and no config.yaml anywhere it looked, or the
            config.yaml itself is invalid (`load_strategy_chain_config`).
    """
    if strategy in STRATEGIES:
        return STRATEGIES[strategy]
    if not strategy_exists(strategy, root=strategies_root):
        looked = [str(root) for root in _strategy_roots(strategies_root)]
        available = sorted({*STRATEGIES, *_yaml_strategy_names(strategies_root)})
        raise ValueError(
            f"unknown strategy {strategy!r}; no registry entry and no config.yaml under "
            f"{looked} — available: {available}; add strategies/{strategy}/config.yaml "
            f"(or pass --strategies-dir) to run a new YAML variant"
        )
    config = load_strategy_chain_config(strategy, root=strategies_root)
    news = "f4_news_context" in config.filters
    return StrategySpec(
        algo_dir="hybrid" if news else "baseline",
        validate=partial(_validate_chain_params, strategy=strategy),
        needs_news_data=news,
        model_file=_F7_MODEL_FILE,
    )


def _strategy_roots(strategies_root: Path | None) -> list[Path]:
    """The directories a strategy name is looked up in: the external one first, then bundled."""
    roots = [strategies_root] if strategies_root is not None else []
    roots.append(bundled_strategies_root())
    return roots


def _yaml_strategy_names(strategies_root: Path | None) -> list[str]:
    """Every strategy with a config.yaml in the external (if any) and bundled directories."""
    return [
        child.name
        for root in _strategy_roots(strategies_root)
        if root.is_dir()
        for child in sorted(root.iterdir())
        if (child / "config.yaml").is_file()
    ]


def validate_run_inputs(
    strategy: str,
    params: Params,
    start: date,
    end: date,
    model: Path | None = None,
    *,
    strategies_root: Path | None = None,
) -> None:
    """Validate a run's inputs, raising ValueError with remediation (fail fast).

    Raises:
        ValueError: unknown strategy, a from-date after the to-date, strategy-specific
            parameter violations (wrong keys, non-numeric, out-of-range), or a `model`
            override for a strategy without an F7 model / pointing at no file.
    """
    spec = resolve_strategy(strategy, strategies_root=strategies_root)
    if start > end:
        raise ValueError(f"from date ({start}) must not be after the to date ({end})")
    spec.validate(params)
    _validate_model(strategy, model, spec, strategies_root)


def _validate_model(
    strategy: str, model: Path | None, spec: StrategySpec, strategies_root: Path | None
) -> None:
    """The F7 model a run would load must exist and match the strategy's families.

    Checks the `--model` override, or the strategy's bundled model when none is given,
    so a mismatch fails on the host before any container starts.
    """
    if spec.model_file is None:
        if model is not None:
            raise ValueError(
                f"--model only applies to the config.yaml chain strategies, not {strategy!r}"
            )
        return
    path = model if model is not None else _algos_root() / spec.algo_dir / spec.model_file
    if not path.is_file():
        raise ValueError(f"F7 model {path} is not a file")
    config = load_strategy_chain_config(strategy, root=strategies_root)
    require_families(load_families(path), config.meta_learner_families, where=str(path))
    _require_feature_parity(path, strategy, config)


def _require_feature_parity(path: Path, strategy: str, config: StrategyChainConfig) -> None:
    """The model must have been trained on the strategy's price_features and label horizon.

    A model's provenance records the `strategy_config` it was fitted under; a model from
    before the `price_features` section existed was fitted on the documented defaults, so
    an absent key compares as the defaults rather than being skipped.

    Raises:
        ValueError: naming every differing period, or the differing label horizon.
    """
    provenance = load_provenance(path)
    from algo_backtest.signal_contract import require_signal_contract

    require_signal_contract(provenance, config)
    _require_same_price_features(
        path, strategy, _trained_price_features(provenance, path), config.price_features
    )
    _require_same_horizon(path, strategy, provenance, config.f7)


def _trained_price_features(provenance: Mapping[str, object], path: Path) -> PriceFeatureConfig:
    """The price_features a model was fitted under; a provenance without the section (or
    without a mapping `strategy_config` at all) means the documented defaults."""
    trained_config = provenance.get("strategy_config", {})
    trained_raw = (
        trained_config.get("price_features", {}) if isinstance(trained_config, dict) else {}
    )
    return parse_price_features_config(trained_raw, strategy=f"model {path.name}")


def _differing_price_features(
    trained: PriceFeatureConfig, declared: PriceFeatureConfig
) -> list[str]:
    """The price_features keys whose trained and declared values differ, sorted."""
    return sorted(
        key for key, value in price_features_mapping(declared).items()
        if getattr(trained, key) != value
    )


def _require_same_price_features(
    path: Path, strategy: str, trained: PriceFeatureConfig, declared: PriceFeatureConfig
) -> None:
    """Fail fast when the model's price_features differ from the strategy's.

    Raises:
        ValueError: naming every differing period on both sides.
    """
    differing = _differing_price_features(trained, declared)
    if differing:
        raise ValueError(
            f"F7 model {path} was trained with price_features "
            f"{ {k: getattr(trained, k) for k in differing} } but strategy {strategy!r} declares "
            f"{ {k: getattr(declared, k) for k in differing} } — retrain the model with "
            "scripts/train_*_meta_learner.py or align the strategy's price_features section"
        )


def _require_same_horizon(
    path: Path, strategy: str, provenance: Mapping[str, object], f7: F7Config | None
) -> None:
    """Fail fast when the model's label horizon differs from the strategy's F7 config
    (a strategy without F7 has no horizon to compare).

    Raises:
        ValueError: naming both horizons.
    """
    horizon = provenance.get("horizon_minutes")
    if f7 is not None and horizon != f7.label_horizon_minutes:
        raise ValueError(
            f"F7 model {path} was trained with a {horizon}-minute label horizon but strategy "
            f"{strategy!r} declares meta_learner.label_horizon_minutes="
            f"{f7.label_horizon_minutes} — retrain the model or align the strategy"
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
    strategy: str,
    data_root: Path,
    symbol: str,
    start: date,
    end: date,
    *,
    strategies_root: Path | None = None,
) -> list[str]:
    """Why the event features cannot serve a news-driven run (always empty otherwise).

    Checked on the host before any container starts (see
    `f4_news_context.news_coverage_problems`), so a coverage gap — including the final
    bar's `end + 1` 00:00 decision — is a remediation-rich CLI error rather than a
    failure buried in the LEAN container log.
    """
    if not resolve_strategy(strategy, strategies_root=strategies_root).needs_news_data:
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
    strategies_root: Path | None = None,
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
    spec = resolve_strategy(strategy, strategies_root=strategies_root)
    algo_dir = _algos_root() / spec.algo_dir
    symbol_dir = lean_data_dir_for(data_root, instrument, "minute")
    subpath = symbol_dir.relative_to(data_root / "lean-data").as_posix()
    data_mounts = {subpath: symbol_dir}
    parameters = {
        "symbol": instrument.symbol,
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "broker_adapter": broker_adapter,
        "chain_config": strategy,
        **params,
    }
    if spec.needs_news_data:
        data_mounts.update(_news_mounts(data_root))
        parameters["news_data_root"] = str(NEWS_DATA_ROOT)
    algo_files: dict[str, Path] = {}
    activity_inputs: dict[str, str] | None = None
    if model is not None and spec.model_file:
        algo_files[spec.model_file] = model
    with tempfile.TemporaryDirectory(prefix="lean-strategy-") as scratch:
        if spec.model_file:  # a chain strategy: ship its resolved YAML next to main.py
            config = load_strategy_chain_config(strategy, root=strategies_root)
            if config.volume_strength is not None:
                price_root = data_root / "parquet" / instrument.security_type
                if not price_root.is_dir():
                    raise ValueError(
                        "volume filter requires canonical prices Parquet; materialize prices"
                    )
                data_mounts[f"activity/parquet/{instrument.security_type}"] = price_root
                parameters["activity_data_root"] = "/Lean/Data/activity"
                activity_inputs = activity_provenance(data_root, instrument, start, end)
                write_text_atomic(
                    results_dir / "activity-inputs.json",
                    json.dumps({"schema_version": 1, "source": "quote_tick_count",
                                "files": activity_inputs}, indent=2, sort_keys=True) + "\n",
                )
            resolved = Path(scratch) / _RESOLVED_STRATEGY_FILE
            resolved.write_text(resolved_yaml(config))
            algo_files[_RESOLVED_STRATEGY_FILE] = resolved
            # Where each parameter came from (which config.yaml in the extends chain, or
            # a default) — only the host knows the chain, so it is written here, next
            # to the strategy-config.json the container writes.
            write_text_atomic(
                results_dir / "strategy-provenance.json",
                json.dumps(dict(config.provenance), indent=2, sort_keys=True) + "\n",
            )
        run = run_lean(
            algo_dir, results_dir, data_mounts=data_mounts,
            parameters=parameters, timeout=timeout, algo_files=algo_files,
        )
    if (activity_inputs is not None
            and activity_provenance(data_root, instrument, start, end) != activity_inputs):
        raise ValueError("canonical tick activity changed during execution; discard this run")
    return parse_results(results_dir, success=run.exit_code == 0)
