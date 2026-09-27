"""Steps for execution_config.feature — the optional top-level `execution` section."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
import yaml
from algo_backtest.chain.execution_config import (
    ExecutionConfig,
    execution_mapping,
    parse_execution_config,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/execution_config.feature")


@dataclass
class _ExCtx:
    """Per-scenario section under test and the parse outcome."""

    section: dict[str, Any] = field(default_factory=dict)
    parsed: ExecutionConfig | None = None
    error: Exception | None = None


@pytest.fixture
def ex_ctx() -> _ExCtx:
    return _ExCtx()


@given("an empty execution section")
def _empty(ex_ctx: _ExCtx) -> None:
    ex_ctx.section = {}


@given(parsers.parse("an execution section with {key} set to {value}"))
def _one_key(ex_ctx: _ExCtx, key: str, value: str) -> None:
    """The table cell goes through YAML so it can carry strings, booleans and floats."""
    ex_ctx.section = {key: yaml.safe_load(value)}


@when(parsers.parse('the execution config is parsed for strategy "{strategy}"'))
def _parse(ex_ctx: _ExCtx, strategy: str) -> None:
    ex_ctx.parsed = parse_execution_config(ex_ctx.section, strategy=strategy)


@when(parsers.parse('parsing the execution config for strategy "{strategy}" fails'))
def _parse_fails(ex_ctx: _ExCtx, strategy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        parse_execution_config(ex_ctx.section, strategy=strategy)
    ex_ctx.error = exc_info.value


@then(
    parsers.parse(
        "the parsed execution config is spread_pips {spread:g}, commission_per_lot "
        "{commission:g}, min_hold_bars {hold:d}"
    )
)
def _all_values(ex_ctx: _ExCtx, spread: float, commission: float, hold: int) -> None:
    assert ex_ctx.parsed == ExecutionConfig(
        spread_pips=spread, commission_per_lot=commission, min_hold_bars=hold
    )


@then(parsers.parse("the execution mapping records {key} {value}"))
def _mapping_records(ex_ctx: _ExCtx, key: str, value: str) -> None:
    """Effective values as the loader writes them back into the resolved config."""
    assert ex_ctx.parsed is not None
    assert execution_mapping(ex_ctx.parsed)[key] == yaml.safe_load(value)


@then(parsers.parse('the execution failure names "{fragment}"'))
def _failure_names(ex_ctx: _ExCtx, fragment: str) -> None:
    assert ex_ctx.error is not None
    assert fragment in str(ex_ctx.error)
