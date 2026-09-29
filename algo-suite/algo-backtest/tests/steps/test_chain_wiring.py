"""Steps for chain_wiring.feature — the LEAN-free half of the chain-driven algorithms."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

import pytest
from algo_backtest.chain.filters.f4_news_context import F4NewsContextFilter, NewsContextIndex
from algo_backtest.chain.filters.f5_risk_guard import RiskGuardFilter
from algo_backtest.chain.filters.f6_capital_mgmt import CapitalMgmtConfig, CapitalMgmtFilter
from algo_backtest.chain.filters.f7_meta_learner import (
    F7MetaLearnerFilter,
    FeatureFamily,
    TrainedMetaLearner,
    TrainingRow,
    train_meta_learner,
    walk_forward_split,
)
from algo_backtest.chain.model import (
    ChainOutcome,
    ExecutionState,
    Filter,
    FilterChain,
    FilterResult,
)
from algo_backtest.chain.terminal import F7TerminalDecision, LastFilterTerminalDecision
from algo_backtest.chain.wiring import (
    AccountSnapshot,
    PnlWindows,
    account_features,
    build_filters,
    pip_size_from_price_variation,
    price_features,
    terminal_decision,
)
from algo_backtest.rules.risk_guard import RiskGuardCaps
from algo_backtest.strategies import StrategyChainConfig, load_strategy_chain_config
from algo_core.instrument import build_instrument
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/chain_wiring.feature")

# F7MetaLearnerFilter only stores the model at construction; predict() is never called.
_UNUSED_MODEL = cast(TrainedMetaLearner, object())
_EMPTY_NEWS = NewsContextIndex(
    event_intensity={}, sentiment_polarity={}, sentiment_source_present=False
)


@dataclass
class _WiringCtx:
    """Per-scenario fixture context."""

    features: dict[str, object] = field(default_factory=dict)
    account: AccountSnapshot | None = None
    windows: PnlWindows = field(default_factory=PnlWindows)
    fractions: tuple[float, float] = (0.0, 0.0)
    filters: list[Filter] = field(default_factory=list)
    error: ValueError | None = None
    f5_result: FilterResult | None = None
    pip_size: float | None = None
    root: Path = Path()
    config: StrategyChainConfig | None = None
    model: TrainedMetaLearner | None = None
    outcome: ChainOutcome | None = None
    terminal: object | None = None


@pytest.fixture
def wiring_ctx(tmp_path: Path) -> _WiringCtx:
    """A fresh per-scenario context; `root` hosts any inline strategy config.yaml."""
    return _WiringCtx(root=tmp_path)


def _account(invested: bool, value: float, holdings: float, unrealized: float) -> AccountSnapshot:
    """An AccountSnapshot with the fields these scenarios don't vary held fixed."""
    return AccountSnapshot(
        invested=invested, portfolio_value=value, unrealized_profit=unrealized,
        holdings_value=holdings, cash=value, margin_remaining=value,
        daily_pnl_fraction=0.0, weekly_pnl_fraction=0.0,
    )


@when(
    parsers.parse(
        "price features are built for price {price:g}, fast EMA {fast:g}, "
        "slow EMA {slow:g}, HTF EMA {htf:g}"
    )
)
def _price_features(
    wiring_ctx: _WiringCtx, price: float, fast: float, slow: float, htf: float
) -> None:
    wiring_ctx.features = price_features(
        price=price, ema_fast=fast, ema_slow=slow, ema_htf=htf, rsi=50.0, macd_hist=0.0
    )


@when(
    parsers.parse(
        "price features are built for price {price:g}, fast EMA {fast:g}, "
        "slow EMA {slow:g}, HTF EMA {htf:g} with atr_pips {atr_pips:g}"
    )
)
def _price_features_with_atr(
    wiring_ctx: _WiringCtx, price: float, fast: float, slow: float, htf: float, atr_pips: float
) -> None:
    wiring_ctx.features = price_features(
        price=price, ema_fast=fast, ema_slow=slow, ema_htf=htf, rsi=50.0, macd_hist=0.0,
        atr_pips=atr_pips,
    )


@when(
    parsers.parse(
        "price features are built for price {price:g}, fast EMA {fast:g}, "
        "slow EMA {slow:g}, HTF EMA {htf:g} with swing_low_pips {low:g} and "
        "swing_high_pips {high:g}"
    )
)
def _price_features_with_swings(
    wiring_ctx: _WiringCtx, price: float, fast: float, slow: float, htf: float, low: float,
    high: float,
) -> None:
    wiring_ctx.features = price_features(
        price=price, ema_fast=fast, ema_slow=slow, ema_htf=htf, rsi=50.0, macd_hist=0.0,
        swing_low_pips=low, swing_high_pips=high,
    )


@when(parsers.parse("the pip size is derived from a minimum price variation of {variation:g}"))
def _pip_size(wiring_ctx: _WiringCtx, variation: float) -> None:
    wiring_ctx.pip_size = pip_size_from_price_variation(variation)


@when(
    parsers.parse(
        "deriving the pip size from a minimum price variation of {variation:g} fails"
    )
)
def _pip_size_fails(wiring_ctx: _WiringCtx, variation: float) -> None:
    with pytest.raises(ValueError) as excinfo:
        pip_size_from_price_variation(variation)
    wiring_ctx.error = excinfo.value


@then(parsers.parse("the pip size is {pip:g}"))
def _pip_is(wiring_ctx: _WiringCtx, pip: float) -> None:
    assert wiring_ctx.pip_size == pytest.approx(pip, rel=1e-12)


@then(parsers.parse('it equals the unit_size of instrument "{symbol}"'))
def _pip_matches_instrument(wiring_ctx: _WiringCtx, symbol: str) -> None:
    assert wiring_ctx.pip_size == pytest.approx(build_instrument(symbol).unit_size, rel=1e-12)


@given(
    parsers.parse(
        "an invested account worth {value:g} holding {holdings:g} with unrealized profit "
        "{unrealized:g}"
    )
)
def _invested_account(
    wiring_ctx: _WiringCtx, value: float, holdings: float, unrealized: float
) -> None:
    wiring_ctx.account = _account(True, value, holdings, unrealized)


@given(parsers.parse("a flat account worth {value:g}"))
def _flat_account(wiring_ctx: _WiringCtx, value: float) -> None:
    wiring_ctx.account = _account(False, value, 0.0, 0.0)


@given(
    parsers.parse(
        "a flat account worth {value:g} with cash {cash:g}, margin remaining {margin:g}, "
        "daily PnL fraction {daily:g} and weekly PnL fraction {weekly:g}"
    )
)
def _flat_account_readings(
    wiring_ctx: _WiringCtx, value: float, cash: float, margin: float, daily: float, weekly: float
) -> None:
    """A flat account whose every LEAN reading is distinct, so each contract key is checkable."""
    wiring_ctx.account = AccountSnapshot(
        invested=False, portfolio_value=value, unrealized_profit=0.0, holdings_value=0.0,
        cash=cash, margin_remaining=margin, daily_pnl_fraction=daily, weekly_pnl_fraction=weekly,
    )


@when(
    parsers.parse(
        "account features are built at price {price:g} with the real baseline capital_mgmt section"
    )
)
def _account_features_real(wiring_ctx: _WiringCtx, price: float) -> None:
    assert wiring_ctx.account is not None
    economics = load_strategy_chain_config("baseline").capital_mgmt
    assert economics is not None
    wiring_ctx.features = account_features(wiring_ctx.account, price, economics)


@when(
    parsers.parse(
        "account features are built at price {price:g} with capital_mgmt "
        "pip_value_per_lot {pip:g}, lot_notional_units {lot:g}, assumed_leverage {lev:g}"
    )
)
def _account_features_custom(
    wiring_ctx: _WiringCtx, price: float, pip: float, lot: float, lev: float
) -> None:
    """Only the per-lot economics reach the features; the stop distance is F6's own
    (`CapitalMgmtConfig.stop_loss_pips`), so the config's value here is immaterial."""
    assert wiring_ctx.account is not None
    economics = CapitalMgmtConfig(
        risk_per_trade=0.03, stop_loss_pips=20.0, pip_value_per_lot=pip,
        lot_notional_units=lot, assumed_leverage=lev,
    )
    wiring_ctx.features = account_features(wiring_ctx.account, price, economics)


@when(parsers.parse("account features are built at price {price:g} without a capital_mgmt section"))
def _account_features_without_f6(wiring_ctx: _WiringCtx, price: float) -> None:
    assert wiring_ctx.account is not None
    wiring_ctx.features = account_features(wiring_ctx.account, price, None)


@then(parsers.parse('the features carry none of "{names}"'))
def _features_absent(wiring_ctx: _WiringCtx, names: str) -> None:
    present = [n.strip() for n in names.split(",") if n.strip() in wiring_ctx.features]
    assert not present, f"unexpected sizing inputs present: {present}"


@then(parsers.parse('feature "{name}" is {value:g}'))
def _feature_is(wiring_ctx: _WiringCtx, name: str, value: float) -> None:
    assert wiring_ctx.features[name] == pytest.approx(value)


@then(parsers.parse('feature "{name}" is missing'))
def _feature_missing(wiring_ctx: _WiringCtx, name: str) -> None:
    assert name in wiring_ctx.features and wiring_ctx.features[name] is None


@given(parsers.parse('PnL windows anchored at equity {equity:g} on "{ts}"'))
def _anchor(wiring_ctx: _WiringCtx, equity: float, ts: str) -> None:
    wiring_ctx.windows.update(datetime.fromisoformat(ts), equity)


@when(parsers.parse('equity {equity:g} is observed on "{ts}"'))
def _observe(wiring_ctx: _WiringCtx, equity: float, ts: str) -> None:
    wiring_ctx.fractions = wiring_ctx.windows.update(datetime.fromisoformat(ts), equity)


@then(
    parsers.parse(
        "the daily PnL fraction is {daily:g} and the weekly PnL fraction is {weekly:g}"
    )
)
def _fractions(wiring_ctx: _WiringCtx, daily: float, weekly: float) -> None:
    assert wiring_ctx.fractions == pytest.approx((daily, weekly))


def _build(
    wiring_ctx: _WiringCtx, config: StrategyChainConfig, news: NewsContextIndex | None
) -> None:
    """Build filters, capturing a fail-fast ValueError for the Then step."""
    try:
        wiring_ctx.filters = build_filters(config, meta_learner=_UNUSED_MODEL, news_index=news)
    except ValueError as exc:
        wiring_ctx.error = exc


@when("the hybrid config's filters are built with a news index")
def _hybrid_with_news(wiring_ctx: _WiringCtx) -> None:
    _build(wiring_ctx, load_strategy_chain_config("hybrid"), _EMPTY_NEWS)


@when("the hybrid config's filters are built without a news index")
def _hybrid_without_news(wiring_ctx: _WiringCtx) -> None:
    _build(wiring_ctx, load_strategy_chain_config("hybrid"), None)


@when(parsers.parse('filters "{names}" are built'))
def _named_filters(wiring_ctx: _WiringCtx, names: str) -> None:
    """A hand-built config whose filter list bypasses the YAML loader's section checks."""
    config = StrategyChainConfig(
        name="handbuilt", filters=tuple(name.strip() for name in names.split(",")),
        meta_learner_families=(), extends=None, raw={},
    )
    _build(wiring_ctx, config, None)


@when(parsers.parse('filters "{names}" are built with an empty news index'))
def _named_filters_with_news(wiring_ctx: _WiringCtx, names: str) -> None:
    """Like the hand-built config above, but with a news index so F4 reaches its section check."""
    config = StrategyChainConfig(
        name="handbuilt", filters=tuple(name.strip() for name in names.split(",")),
        meta_learner_families=(), extends=None, raw={},
    )
    _build(wiring_ctx, config, _EMPTY_NEWS)


def _built(wiring_ctx: _WiringCtx, kind: type[Filter]) -> Filter:
    """The single built filter of `kind`, failing loudly if it is absent."""
    matches = [f for f in wiring_ctx.filters if isinstance(f, kind)]
    assert len(matches) == 1, f"expected exactly one {kind.__name__}, got {matches}"
    return matches[0]


@then("the built F7 filter carries the hybrid config's thresholds and regime gate")
def _f7_carries_config(wiring_ctx: _WiringCtx) -> None:
    built = _built(wiring_ctx, F7MetaLearnerFilter)
    assert isinstance(built, F7MetaLearnerFilter)
    assert built.config == load_strategy_chain_config("hybrid").f7


@then("the built F5 filter carries the hybrid config's risk-guard caps")
def _f5_carries_config(wiring_ctx: _WiringCtx) -> None:
    built = _built(wiring_ctx, RiskGuardFilter)
    assert isinstance(built, RiskGuardFilter)
    assert built.caps == load_strategy_chain_config("hybrid").risk_guard


@then("the built F6 filter carries the hybrid config's capital_mgmt section and execution spread")
def _f6_carries_config(wiring_ctx: _WiringCtx) -> None:
    built = _built(wiring_ctx, CapitalMgmtFilter)
    assert isinstance(built, CapitalMgmtFilter)
    config = load_strategy_chain_config("hybrid")
    assert config.capital_mgmt is not None
    assert built.config == config.capital_mgmt
    assert built.spread_pips == config.execution.spread_pips
    assert built.broker_stop_level_pips == config.execution.broker_stop_level_pips


@then("the built F4 filter carries the hybrid config's news-context thresholds")
def _f4_carries_config(wiring_ctx: _WiringCtx) -> None:
    built = _built(wiring_ctx, F4NewsContextFilter)
    assert isinstance(built, F4NewsContextFilter)
    assert built.config == load_strategy_chain_config("hybrid").news_context


@then(parsers.parse('the chain\'s filters are "{names}"'))
def _chain_filters(wiring_ctx: _WiringCtx, names: str) -> None:
    assert wiring_ctx.error is None, wiring_ctx.error
    expected = [name.strip() for name in names.split(",")]
    built = [type(f).__module__.rsplit(".", 1)[-1] for f in wiring_ctx.filters]
    assert built == expected


@then(parsers.parse('building fails naming "{fragment}"'))
def _fails(wiring_ctx: _WiringCtx, fragment: str) -> None:
    assert wiring_ctx.error is not None
    assert fragment in str(wiring_ctx.error)


@when("F5 evaluates the account under the real baseline risk_guard caps")
def _f5_real_caps(wiring_ctx: _WiringCtx) -> None:
    assert wiring_ctx.account is not None
    config = load_strategy_chain_config("baseline")
    assert config.risk_guard is not None
    state = ExecutionState(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        pair="EURUSD",
        features=account_features(wiring_ctx.account, 1.1, config.capital_mgmt),
    )
    wiring_ctx.f5_result = RiskGuardFilter(caps=config.risk_guard).apply(state)


@then("F5 does not veto")
def _f5_no_veto(wiring_ctx: _WiringCtx) -> None:
    assert wiring_ctx.f5_result is not None
    assert not wiring_ctx.f5_result.veto, wiring_ctx.f5_result.reason


@when(parsers.parse("risk-guard caps are built with daily_drawdown_limit {limit:g}"))
def _positive_limit(wiring_ctx: _WiringCtx, limit: float) -> None:
    try:
        RiskGuardCaps(
            portfolio_at_risk_cap=None, daily_drawdown_limit=limit, weekly_drawdown_limit=None,
            max_concurrent_trades_per_account=None, max_leverage=None,
        )
    except ValueError as exc:
        wiring_ctx.error = exc


# The decision minute every news-only scenario keys F4's lookup on.
_DECISION_MINUTE = datetime(2020, 2, 3, 9, 0, tzinfo=UTC)


@given(
    parsers.parse(
        'an external strategy "{name}" loaded through the production loader from its config.yaml:'
    )
)
def _inline_strategy(wiring_ctx: _WiringCtx, name: str, docstring: str) -> None:
    """Write the scenario's YAML as `<root>/<name>/config.yaml` and resolve it exactly as
    `--strategies-dir` would (its `extends: baseline` reaches the bundled base)."""
    directory = wiring_ctx.root / name
    directory.mkdir()
    (directory / "config.yaml").write_text(docstring)
    wiring_ctx.config = load_strategy_chain_config(name, root=wiring_ctx.root)


@given(
    parsers.parse(
        "a news-only meta-learner trained on {n:d} synthetic rows labelled up when "
        "news_event_intensity is positive"
    )
)
def _news_only_model(wiring_ctx: _WiringCtx, n: int) -> None:
    """Rows carry the NEWS family's feature alone (sentiment missing, as live pending TD-48),
    spread over 28 days so the walk-forward split has three non-empty spans."""
    rng = random.Random(7)
    rows = []
    for i in range(n):
        intensity = rng.uniform(-0.45, 0.45)
        day = min(28, (i * 28 // n) + 1)
        rows.append(
            TrainingRow(
                timestamp=datetime(2020, 1, day, tzinfo=UTC),
                features={"news_event_intensity": intensity},
                label=1 if intensity > 0 else 0,
            )
        )
    split = walk_forward_split(
        rows, train_end=date(2020, 1, 20), validation_end=date(2020, 1, 25),
        test_end=date(2020, 1, 28),
    )
    wiring_ctx.model = train_meta_learner([FeatureFamily.NEWS], split)


@when(
    parsers.parse(
        "the loaded strategy's filters are built with a news index reading {intensity:g} at "
        "the decision minute"
    )
)
def _build_loaded(wiring_ctx: _WiringCtx, intensity: float) -> None:
    assert wiring_ctx.config is not None and wiring_ctx.model is not None
    index = NewsContextIndex(
        event_intensity={_DECISION_MINUTE: intensity}, sentiment_polarity={},
        sentiment_source_present=False,
    )
    wiring_ctx.filters = build_filters(
        wiring_ctx.config, meta_learner=wiring_ctx.model, news_index=index
    )


@then(parsers.parse('the built F7 filter\'s model was trained on the families "{families}"'))
def _f7_model_families(wiring_ctx: _WiringCtx, families: str) -> None:
    built = _built(wiring_ctx, F7MetaLearnerFilter)
    assert isinstance(built, F7MetaLearnerFilter)
    assert [f.value for f in built.meta_learner.families] == [
        f.strip() for f in families.split(",")
    ]


@then("the loaded strategy has no F1, F2 or F3 section and declares no pattern family")
def _no_price_filter_sections(wiring_ctx: _WiringCtx) -> None:
    config = wiring_ctx.config
    assert config is not None
    assert config.indicator is None and config.pattern is None
    assert "indicator" not in config.raw and "pattern" not in config.raw
    assert FeatureFamily.PATTERN.value not in config.meta_learner_families


@then(
    parsers.parse(
        "running the chain on a flat {equity:g} account at price {price:g} with {swing:g}-pip "
        "swing distances and no price feature decides {decision}"
    )
)
def _run_news_only_chain(
    wiring_ctx: _WiringCtx, equity: float, price: float, swing: float, decision: str
) -> None:
    """The features are what the engine supplies without F1–F3: the account readings and
    the swing/ATR distances its price-feature computation always produces — none of the
    trend, indicator or pattern keys. F4 enriches news_event_intensity in flight."""
    assert wiring_ctx.config is not None
    account = AccountSnapshot(
        invested=False, portfolio_value=equity, unrealized_profit=0.0, holdings_value=0.0,
        cash=equity, margin_remaining=equity, daily_pnl_fraction=0.0, weekly_pnl_fraction=0.0,
    )
    features: dict[str, object] = {
        **account_features(account, price, wiring_ctx.config.capital_mgmt),
        "swing_low_pips": swing, "swing_high_pips": swing,
    }
    assert not {"trend_direction", "rsi", "macd_hist", "candlestick_pattern"} & set(features)
    chain = FilterChain(filters=wiring_ctx.filters, terminal=F7TerminalDecision())
    wiring_ctx.outcome = chain.run(
        ExecutionState(timestamp=_DECISION_MINUTE, pair="EURUSD", features=features)
    )
    assert wiring_ctx.outcome.decision.value == decision, wiring_ctx.outcome.state.filter_results


@then(
    parsers.parse(
        "F4's result carries news_event_intensity {intensity:g} and the decision came through "
        "{last_filter}"
    )
)
def _news_only_audit(wiring_ctx: _WiringCtx, intensity: float, last_filter: str) -> None:
    assert wiring_ctx.outcome is not None
    results = wiring_ctx.outcome.state.filter_results
    assert results[0].filter_name == "f4_news_context"
    assert results[0].enrichment["news_event_intensity"] == pytest.approx(intensity)
    assert results[-1].filter_name == last_filter


@when(
    parsers.parse(
        'the terminal rule is selected for a hand-built config with filters "{names}" and '
        "terminal_filter {terminal}"
    )
)
def _select_terminal(wiring_ctx: _WiringCtx, names: str, terminal: str) -> None:
    """`none` = no terminal_filter; otherwise the quoted filter name."""
    config = StrategyChainConfig(
        name="handbuilt", filters=tuple(n.strip() for n in names.split(",")),
        meta_learner_families=(), extends=None, raw={},
        terminal_filter=None if terminal == "none" else terminal.strip('"'),
    )
    try:
        wiring_ctx.terminal = terminal_decision(config)
    except ValueError as exc:
        wiring_ctx.error = exc


@then(parsers.parse("the selected terminal rule is {rule}"))
def _selected_terminal(wiring_ctx: _WiringCtx, rule: str) -> None:
    assert wiring_ctx.error is None, wiring_ctx.error
    if rule == "F7TerminalDecision":
        assert isinstance(wiring_ctx.terminal, F7TerminalDecision)
        return
    prefix = "LastFilterTerminalDecision for "
    assert rule.startswith(prefix), rule
    assert wiring_ctx.terminal == LastFilterTerminalDecision(rule[len(prefix):].strip('"'))


@when(parsers.parse('filters "{names}" are built without a meta-learner model'))
def _named_filters_without_model(wiring_ctx: _WiringCtx, names: str) -> None:
    config = StrategyChainConfig(
        name="handbuilt", filters=tuple(name.strip() for name in names.split(",")),
        meta_learner_families=(), extends=None, raw={},
    )
    try:
        wiring_ctx.filters = build_filters(config, meta_learner=None, news_index=None)
    except ValueError as exc:
        wiring_ctx.error = exc
