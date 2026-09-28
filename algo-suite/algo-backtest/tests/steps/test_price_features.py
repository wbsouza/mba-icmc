"""Steps for price_features.feature — the shared EMA/RSI/MACD period parameters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
import yaml
from algo_backtest.chain.price_features import (
    PriceFeatureConfig,
    parse_price_features_config,
    warmup_bars,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/price_features.feature")


@dataclass
class _PfCtx:
    """Per-scenario section under test and the parse outcome."""

    section: dict[str, Any] = field(default_factory=dict)
    parsed: PriceFeatureConfig | None = None
    error: Exception | None = None


@pytest.fixture
def pf_ctx() -> _PfCtx:
    return _PfCtx()


@given("an empty price_features section")
def _empty(pf_ctx: _PfCtx) -> None:
    pf_ctx.section = {}


@given(parsers.parse("a price_features section with {key} set to {value}"))
def _one_key(pf_ctx: _PfCtx, key: str, value: str) -> None:
    pf_ctx.section = {key: yaml.safe_load(value)}


@given(parsers.parse('a price_features section with unknown key "{key}"'))
def _unknown_key(pf_ctx: _PfCtx, key: str) -> None:
    pf_ctx.section = {key: 5}


@given(
    parsers.parse(
        "a price_features section with ema_higher_tf {htf:d}, rsi_period {rsi:d}, "
        "macd_slow {slow:d}, macd_signal {signal:d}, atr_period {atr:d}, "
        "swing_lookback_bars {swing:d}"
    )
)
def _warmup_inputs(
    pf_ctx: _PfCtx, htf: int, rsi: int, slow: int, signal: int, atr: int, swing: int
) -> None:
    pf_ctx.section = {
        "ema_higher_tf": htf, "rsi_period": rsi, "macd_slow": slow, "macd_signal": signal,
        "atr_period": atr, "swing_lookback_bars": swing,
    }


@when(parsers.parse('the price-feature config is parsed for strategy "{strategy}"'))
def _parse(pf_ctx: _PfCtx, strategy: str) -> None:
    pf_ctx.parsed = parse_price_features_config(pf_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the price-feature config for strategy "{strategy}" fails'))
def _parse_fails(pf_ctx: _PfCtx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_price_features_config(pf_ctx.section, strategy=strategy)
    pf_ctx.error = exc_info.value


@then(
    parsers.parse(
        "the parsed price features are ema_fast {fast:d}, ema_slow {slow:d}, "
        "ema_higher_tf {htf:d}, rsi_period {rsi:d}, macd_fast {mf:d}, macd_slow {ms:d}, "
        "macd_signal {sig:d}, atr_period {atr:d}, swing_lookback_bars {swing:d}"
    )
)
def _all_values(
    pf_ctx: _PfCtx,
    fast: int, slow: int, htf: int, rsi: int, mf: int, ms: int, sig: int, atr: int, swing: int,
) -> None:
    assert pf_ctx.parsed == PriceFeatureConfig(
        ema_fast=fast, ema_slow=slow, ema_higher_tf=htf, rsi_period=rsi,
        macd_fast=mf, macd_slow=ms, macd_signal=sig, atr_period=atr, swing_lookback_bars=swing,
    )


@then(parsers.parse("the parsed price feature {key} is {value:d}"))
def _one_value(pf_ctx: _PfCtx, key: str, value: int) -> None:
    assert pf_ctx.parsed is not None
    assert getattr(pf_ctx.parsed, key) == value


@then(parsers.parse('the price-feature failure names "{fragment}"'))
def _failure_names(pf_ctx: _PfCtx, fragment: str) -> None:
    assert pf_ctx.error is not None
    assert fragment in str(pf_ctx.error)


@then(parsers.parse("the warm-up is {expected:d} bars"))
def _warmup(pf_ctx: _PfCtx, expected: int) -> None:
    assert pf_ctx.parsed is not None
    assert warmup_bars(pf_ctx.parsed) == expected
