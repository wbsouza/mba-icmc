"""Steps for confluence_momentum.feature — the F1 momentum context variant (story 21, T2).

The momentum scenarios feed a `MomentumHistory` directly (the T13 integration lane later
feeds it from the closed-bar clock); the CC-20 scenarios apply the original
`F1TrendFilter` to prove it is untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import yaml
from algo_backtest.chain.filters.f1_trend import (
    F1MomentumContextFilter,
    F1TrendFilter,
    MomentumContextConfig,
    MomentumHistory,
    momentum_context_mapping,
    parse_momentum_context_config,
)
from algo_backtest.chain.model import ExecutionState, FilterResult, Recommendation
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_momentum.feature")


@dataclass
class _MomentumCtx:
    """Per-scenario context: the config, the history under test, the result or error."""

    config: MomentumContextConfig | None = None
    history: MomentumHistory | None = None
    features: dict[str, object] = field(default_factory=dict)
    result: FilterResult | None = None
    error: Exception | None = None
    section: dict[str, Any] = field(default_factory=dict)
    parsed_config: MomentumContextConfig | None = None
    parse_error: Exception | None = None


@pytest.fixture
def momentum_ctx() -> _MomentumCtx:
    """A fresh per-scenario momentum context."""
    return _MomentumCtx()


def _history(momentum_ctx: _MomentumCtx) -> MomentumHistory:
    """The scenario's history, which a Given must have created."""
    assert momentum_ctx.history is not None
    return momentum_ctx.history


def _result(momentum_ctx: _MomentumCtx) -> FilterResult:
    """The applied result, failing loudly if the filter raised instead (a push rejected
    earlier in the scenario is a captured, expected error, so it is not checked here)."""
    assert momentum_ctx.result is not None, f"no result; captured error: {momentum_ctx.error}"
    return momentum_ctx.result


@given(parsers.parse("a momentum context with lookback_bars {lookback:d}"))
def _momentum_context(momentum_ctx: _MomentumCtx, lookback: int) -> None:
    momentum_ctx.config = parse_momentum_context_config(
        {"lookback_bars": lookback}, strategy="scenario"
    )
    momentum_ctx.history = MomentumHistory(lookback_bars=lookback)


@given(
    parsers.parse(
        "the momentum history is fed {count:d} closes every {clock:d} minutes from "
        "2016-03-01T00:00:00Z, the first {first:g}, the last {last:g} and every other close "
        "{middle:g}"
    )
)
def _fed_series(
    momentum_ctx: _MomentumCtx, count: int, clock: int, first: float, last: float, middle: float
) -> None:
    """`count` closes on a `clock`-minute grid: first, then middles, then last."""
    start = datetime(2016, 3, 1, tzinfo=UTC)
    for index in range(count):
        close = first if index == 0 else last if index == count - 1 else middle
        _history(momentum_ctx).push(start + timedelta(minutes=clock * index), close)


@given("the momentum history is fed these closes:")
def _fed_table(momentum_ctx: _MomentumCtx, datatable: list[list[str]]) -> None:
    header, *rows = datatable
    assert header == ["close_time", "close"], header
    for close_time, close in rows:
        _history(momentum_ctx).push(datetime.fromisoformat(close_time), float(close))


@given("the momentum history is fed no closes")
def _fed_nothing(momentum_ctx: _MomentumCtx) -> None:
    assert _history(momentum_ctx).sample_count == 0


@given(
    parsers.parse(
        "the bar's features carry trend_direction {trend_direction:g}, trend_strength "
        "{trend_strength:g} and higher_tf_trend_direction {higher:g}"
    )
)
def _bar_features(
    momentum_ctx: _MomentumCtx, trend_direction: float, trend_strength: float, higher: float
) -> None:
    momentum_ctx.features = {
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
        "higher_tf_trend_direction": higher,
    }


def _apply(momentum_ctx: _MomentumCtx, at: datetime) -> None:
    """Apply the momentum filter built from the scenario's config and history."""
    assert momentum_ctx.config is not None
    momentum_filter = F1MomentumContextFilter(
        config=momentum_ctx.config, history=_history(momentum_ctx)
    )
    state = ExecutionState(timestamp=at, pair="EURUSD", features=dict(momentum_ctx.features))
    momentum_ctx.result = momentum_filter.apply(state)


@when("the momentum context filter is applied at the last close")
def _apply_at_last(momentum_ctx: _MomentumCtx) -> None:
    last = _history(momentum_ctx).last_close_time
    assert last is not None, "the history is empty; the scenario must name a time"
    _apply(momentum_ctx, last)


@when(parsers.parse("the momentum context filter is applied at {at:S}"))
def _apply_at(momentum_ctx: _MomentumCtx, at: str) -> None:
    _apply(momentum_ctx, datetime.fromisoformat(at))


@when(
    parsers.parse(
        'the momentum history is pushed close_time "{close_time}" with close {close} and fails'
    )
)
def _push_fails(momentum_ctx: _MomentumCtx, close_time: str, close: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _history(momentum_ctx).push(datetime.fromisoformat(close_time), float(close))
    momentum_ctx.error = exc_info.value


@when(
    parsers.parse(
        'the momentum history is pushed a naive close_time "{close_time}" with close {close:g} '
        "and fails"
    )
)
def _push_naive_fails(momentum_ctx: _MomentumCtx, close_time: str, close: float) -> None:
    naive = datetime.fromisoformat(close_time)
    assert naive.tzinfo is None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _history(momentum_ctx).push(naive, close)
    momentum_ctx.error = exc_info.value


@when(parsers.parse("a momentum history with lookback_bars {lookback:S} is built and fails"))
def _build_history_fails(momentum_ctx: _MomentumCtx, lookback: str) -> None:
    """The cell is flow-style YAML, so `480.0` and `true` keep their types."""
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        MomentumHistory(lookback_bars=yaml.safe_load(lookback))
    momentum_ctx.error = exc_info.value


@when(
    parsers.parse(
        "the momentum context filter is built on a history with lookback_bars {lookback:d} "
        "and fails"
    )
)
def _build_filter_fails(momentum_ctx: _MomentumCtx, lookback: int) -> None:
    assert momentum_ctx.config is not None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        F1MomentumContextFilter(
            config=momentum_ctx.config, history=MomentumHistory(lookback_bars=lookback)
        )
    momentum_ctx.error = exc_info.value


@then(parsers.parse('the momentum vote is "{vote}" with no veto'))
def _vote(momentum_ctx: _MomentumCtx, vote: str) -> None:
    result = _result(momentum_ctx)
    assert result.recommendation == Recommendation(vote), result.reason
    assert result.veto is False


@then(parsers.parse('the momentum filter_name is "{name}"'))
def _filter_name(momentum_ctx: _MomentumCtx, name: str) -> None:
    assert _result(momentum_ctx).filter_name == name


@then(parsers.parse('the momentum reason mentions "{fragment}"'))
def _reason_mentions(momentum_ctx: _MomentumCtx, fragment: str) -> None:
    assert fragment in _result(momentum_ctx).reason, _result(momentum_ctx).reason


@then(parsers.parse('the momentum reason does not mention "{fragment}"'))
def _reason_omits(momentum_ctx: _MomentumCtx, fragment: str) -> None:
    assert fragment not in _result(momentum_ctx).reason, _result(momentum_ctx).reason


@then(parsers.parse('the momentum result enriches "{key}" with value {value:g}'))
def _enriches(momentum_ctx: _MomentumCtx, key: str, value: float) -> None:
    assert _result(momentum_ctx).enrichment[key] == pytest.approx(value)


@then(parsers.parse('the momentum result does not enrich "{key}"'))
def _does_not_enrich(momentum_ctx: _MomentumCtx, key: str) -> None:
    assert key not in _result(momentum_ctx).enrichment


@then(parsers.parse('the momentum metadata "{key}" is "{value}"'))
def _metadata_str(momentum_ctx: _MomentumCtx, key: str, value: str) -> None:
    assert _result(momentum_ctx).metadata[key] == value


@then(parsers.parse('the momentum metadata "{key}" is {value:d}'))
def _metadata_int(momentum_ctx: _MomentumCtx, key: str, value: int) -> None:
    assert _result(momentum_ctx).metadata[key] == value


@then(parsers.parse('the momentum failure names "{fragment}"'))
def _failure_names(momentum_ctx: _MomentumCtx, fragment: str) -> None:
    assert momentum_ctx.error is not None, "expected a failure but none was raised"
    assert fragment in str(momentum_ctx.error), str(momentum_ctx.error)


# --- Rule: momentum_context.lookback_bars comes from config.yaml ---


@given(parsers.parse("a momentum_context section with lookback_bars {lookback:S}"))
def _section(momentum_ctx: _MomentumCtx, lookback: str) -> None:
    """The cell is flow-style YAML, so `"480"`, `true`, `null` and `480.5` keep their types."""
    momentum_ctx.section = {"lookback_bars": yaml.safe_load(lookback)}


@given(
    parsers.parse(
        'a momentum_context section with lookback_bars {lookback:d} and an extra key "{key}" '
        "of {value}"
    )
)
def _section_extra(momentum_ctx: _MomentumCtx, lookback: int, key: str, value: str) -> None:
    momentum_ctx.section = {"lookback_bars": lookback, key: yaml.safe_load(value)}


@given(parsers.parse('a momentum_context section missing "{key}"'))
def _section_missing(momentum_ctx: _MomentumCtx, key: str) -> None:
    momentum_ctx.section = {k: v for k, v in {"lookback_bars": 480}.items() if k != key}


@when(parsers.parse('the momentum-context config is parsed for strategy "{strategy}"'))
def _parse(momentum_ctx: _MomentumCtx, strategy: str) -> None:
    momentum_ctx.parsed_config = parse_momentum_context_config(
        momentum_ctx.section, strategy=strategy
    )


@when(parsers.parse('parsing the momentum-context config for strategy "{strategy}" fails'))
def _parse_fails(momentum_ctx: _MomentumCtx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_momentum_context_config(momentum_ctx.section, strategy=strategy)
    momentum_ctx.parse_error = exc_info.value


@then(parsers.parse("the parsed momentum-context config has lookback_bars {lookback:d}"))
def _parsed(momentum_ctx: _MomentumCtx, lookback: int) -> None:
    assert momentum_ctx.parsed_config == MomentumContextConfig(lookback_bars=lookback)


@then(parsers.parse("the momentum-context mapping records lookback_bars {lookback:d}"))
def _mapping(momentum_ctx: _MomentumCtx, lookback: int) -> None:
    assert momentum_ctx.parsed_config is not None
    assert momentum_context_mapping(momentum_ctx.parsed_config) == {"lookback_bars": lookback}


@then(parsers.parse('the momentum-context config failure names "{fragment}"'))
def _parse_failure_names(momentum_ctx: _MomentumCtx, fragment: str) -> None:
    assert momentum_ctx.parse_error is not None
    assert fragment in str(momentum_ctx.parse_error), str(momentum_ctx.parse_error)


# --- Rule: the original F1 trend filter is untouched (CC-20) ---


@given(
    parsers.parse(
        "trend_direction {trend_direction:g}, trend_strength {trend_strength:g} and "
        "higher_tf_trend_direction {higher:g}"
    )
)
def _trend_features(
    momentum_ctx: _MomentumCtx, trend_direction: float, trend_strength: float, higher: float
) -> None:
    momentum_ctx.features = {
        "trend_direction": trend_direction,
        "trend_strength": trend_strength,
        "higher_tf_trend_direction": higher,
    }


@given(parsers.parse('a state missing "{key}"'))
def _state_missing(momentum_ctx: _MomentumCtx, key: str) -> None:
    momentum_ctx.features = {
        "trend_direction": 0.5,
        "trend_strength": 20.0,
        "higher_tf_trend_direction": 0.5,
    }
    del momentum_ctx.features[key]


@when("the original F1 trend filter is applied")
def _apply_original(momentum_ctx: _MomentumCtx) -> None:
    state = ExecutionState(
        timestamp=datetime(2016, 3, 1, tzinfo=UTC),
        pair="EURUSD",
        features=dict(momentum_ctx.features),
    )
    try:
        momentum_ctx.result = F1TrendFilter().apply(state)
    except ValueError as exc:
        momentum_ctx.error = exc


@then(parsers.parse('the original F1 recommends "{recommendation}" with veto {veto}'))
def _original_recommends(momentum_ctx: _MomentumCtx, recommendation: str, veto: str) -> None:
    result = _result(momentum_ctx)
    assert result.recommendation == Recommendation(recommendation)
    assert result.veto is yaml.safe_load(veto)


@then(parsers.parse('the original F1 enriches "{key}" with value {value}'))
def _original_enriches(momentum_ctx: _MomentumCtx, key: str, value: str) -> None:
    """`absent` asserts the key is not enriched at all (the veto result carries none)."""
    enrichment = _result(momentum_ctx).enrichment
    if value == "absent":
        assert key not in enrichment
    else:
        assert enrichment[key] == pytest.approx(float(value))


@then(parsers.parse('the original F1 raises an error naming "{name}"'))
def _original_raises(momentum_ctx: _MomentumCtx, name: str) -> None:
    assert isinstance(momentum_ctx.error, ValueError)
    assert name in str(momentum_ctx.error)
