"""Steps for strategies.feature — the `extends:`-composing strategy-chain config loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from algo_backtest.strategies import StrategyChainConfig, load_strategy_chain_config
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/strategies.feature")


@dataclass
class _StrategiesCtx:
    """Per-scenario fixture context: the config-dir root plus the loaded outcome/error."""

    root: Path
    loaded: StrategyChainConfig | None = None
    error: Exception | None = None


@pytest.fixture
def strategies_ctx(tmp_path: Path) -> _StrategiesCtx:
    return _StrategiesCtx(root=tmp_path)


def _split(raw: str) -> tuple[str, ...]:
    return tuple(part for part in raw.split(",") if part)


def _config_dir(root: Path, name: str) -> Path:
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _write_config(root: Path, name: str, body: dict[str, object]) -> None:
    (_config_dir(root, name) / "config.yaml").write_text(yaml.safe_dump(body))


@given("an empty strategy config directory")
def _empty_dir(strategies_ctx: _StrategiesCtx) -> None:
    """No-op: `tmp_path` starts empty; this step exists for scenario readability."""
    assert strategies_ctx.root.exists()


@given(
    parsers.parse(
        'a strategy config directory with "{name}" filters "{filters}" and families "{families}"'
    )
)
def _base_config(strategies_ctx: _StrategiesCtx, name: str, filters: str, families: str) -> None:
    _write_config(
        strategies_ctx.root,
        name,
        {
            "schema_version": 1,
            "filters": list(_split(filters)),
            "meta_learner": {"families": list(_split(families))},
        },
    )


@given(parsers.parse('"{name}" also declares meta_learner.theta_high {value:g}'))
def _amend_theta_high(strategies_ctx: _StrategiesCtx, name: str, value: float) -> None:
    """Amend an already-written strategy config with an extra nested `meta_learner` key,
    so a merge test can prove a base-only key survives `extends:` composition."""
    path = _config_dir(strategies_ctx.root, name) / "config.yaml"
    body = yaml.safe_load(path.read_text())
    body["meta_learner"]["theta_high"] = value
    path.write_text(yaml.safe_dump(body))


@given(
    parsers.parse(
        '"{name}" extends "{base}" with filters "{filters}" and families "{families}"'
    )
)
def _extending_config(
    strategies_ctx: _StrategiesCtx, name: str, base: str, filters: str, families: str
) -> None:
    _write_config(
        strategies_ctx.root,
        name,
        {
            "schema_version": 1,
            "extends": base,
            "filters": list(_split(filters)),
            "meta_learner": {"families": list(_split(families))},
        },
    )


@given(parsers.parse('a strategy config directory with an empty filters list for "{name}"'))
def _empty_filters_config(strategies_ctx: _StrategiesCtx, name: str) -> None:
    _write_config(
        strategies_ctx.root, name, {"schema_version": 1, "filters": [], "meta_learner": {}}
    )


@given(parsers.parse('a strategy config directory with no filters key at all for "{name}"'))
def _no_filters_key_config(strategies_ctx: _StrategiesCtx, name: str) -> None:
    _write_config(strategies_ctx.root, name, {"schema_version": 1, "meta_learner": {}})


@given(parsers.parse('a strategy config directory with a non-mapping config for "{name}"'))
def _non_mapping_config(strategies_ctx: _StrategiesCtx, name: str) -> None:
    (_config_dir(strategies_ctx.root, name) / "config.yaml").write_text(
        yaml.safe_dump(["not", "a", "mapping"])
    )


@given(
    parsers.parse(
        'a strategy config directory with "{name}" filters "{filters}" and a scalar meta_learner'
    )
)
def _scalar_meta_learner_config(strategies_ctx: _StrategiesCtx, name: str, filters: str) -> None:
    _write_config(
        strategies_ctx.root,
        name,
        {"schema_version": 1, "filters": list(_split(filters)), "meta_learner": "not-a-mapping"},
    )


@given(
    parsers.parse(
        'a strategy config directory with "{name}" filters "{filters}" and an empty '
        "meta_learner mapping"
    )
)
def _empty_meta_learner_mapping_config(
    strategies_ctx: _StrategiesCtx, name: str, filters: str
) -> None:
    _write_config(
        strategies_ctx.root,
        name,
        {"schema_version": 1, "filters": list(_split(filters)), "meta_learner": {}},
    )


@given(
    parsers.parse(
        'a strategy config directory with "{name}" filters "{filters}" and '
        'meta_learner.families as the scalar "{scalar}"'
    )
)
def _scalar_families_config(
    strategies_ctx: _StrategiesCtx, name: str, filters: str, scalar: str
) -> None:
    _write_config(
        strategies_ctx.root,
        name,
        {
            "schema_version": 1,
            "filters": list(_split(filters)),
            "meta_learner": {"families": scalar},
        },
    )


@given(
    parsers.parse(
        'a strategy config directory with "{name}" filters "{filters}" and '
        "meta_learner.families as a mapping"
    )
)
def _mapping_families_config(strategies_ctx: _StrategiesCtx, name: str, filters: str) -> None:
    _write_config(
        strategies_ctx.root,
        name,
        {
            "schema_version": 1,
            "filters": list(_split(filters)),
            "meta_learner": {"families": {"a": 1}},
        },
    )


@given(parsers.parse('"{name}" extends "{base}" overriding meta_learner with a scalar value'))
def _extends_scalar_meta_learner(strategies_ctx: _StrategiesCtx, name: str, base: str) -> None:
    _write_config(
        strategies_ctx.root,
        name,
        {
            "schema_version": 1,
            "extends": base,
            "filters": ["f1_trend"],
            "meta_learner": "not-a-mapping",
        },
    )


@when(parsers.parse('strategy "{name}" is loaded'))
def _load(strategies_ctx: _StrategiesCtx, name: str) -> None:
    strategies_ctx.loaded = load_strategy_chain_config(name, root=strategies_ctx.root)


@when(parsers.parse('loading strategy "{name}" fails'))
def _load_expect_failure(strategies_ctx: _StrategiesCtx, name: str) -> None:
    try:
        strategies_ctx.loaded = load_strategy_chain_config(name, root=strategies_ctx.root)
    except ValueError as exc:
        strategies_ctx.error = exc


@then(parsers.parse('the loaded strategy\'s name is "{name}"'))
def _loaded_name(strategies_ctx: _StrategiesCtx, name: str) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.name == name


@then(parsers.parse("the loaded strategy's filters are \"{filters}\""))
def _loaded_filters(strategies_ctx: _StrategiesCtx, filters: str) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.filters == _split(filters)


@then(parsers.parse("the loaded strategy's meta-learner families are \"{families}\""))
def _loaded_families(strategies_ctx: _StrategiesCtx, families: str) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.meta_learner_families == _split(families)


@then("the loaded strategy has no meta-learner families")
def _loaded_no_families(strategies_ctx: _StrategiesCtx) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.meta_learner_families == ()


@then(parsers.parse("the loaded strategy's raw meta_learner.theta_high is {value:g}"))
def _loaded_raw_theta_high(strategies_ctx: _StrategiesCtx, value: float) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.raw["meta_learner"]["theta_high"] == pytest.approx(value)


@then("the loaded strategy extends nothing")
def _extends_nothing(strategies_ctx: _StrategiesCtx) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.extends is None


@then(parsers.parse('the loaded strategy extends "{base}"'))
def _extends_base(strategies_ctx: _StrategiesCtx, base: str) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.extends == base


@then(parsers.parse('the failure names "{fragment}"'))
def _failure_names(strategies_ctx: _StrategiesCtx, fragment: str) -> None:
    assert strategies_ctx.error is not None
    assert fragment in str(strategies_ctx.error)


@when(parsers.parse('the real strategy "{name}" is loaded with the default root'))
def _load_real(strategies_ctx: _StrategiesCtx, name: str) -> None:
    """Exercises `load_strategy_chain_config`'s own default (`root=None` ->
    `strategies_root()`), not just an explicitly-passed root."""
    strategies_ctx.loaded = load_strategy_chain_config(name)


@then(parsers.parse("the real loaded strategy's filters end with \"{filters}\""))
def _real_filters_end_with(strategies_ctx: _StrategiesCtx, filters: str) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.filters[-len(_split(filters)) :] == _split(filters)


@then(parsers.parse('the real loaded strategy\'s filters do not include "{name}"'))
def _real_filters_exclude(strategies_ctx: _StrategiesCtx, name: str) -> None:
    assert strategies_ctx.loaded is not None
    assert name not in strategies_ctx.loaded.filters


@then(parsers.parse('the real loaded strategy\'s filters include "{name}"'))
def _real_filters_include(strategies_ctx: _StrategiesCtx, name: str) -> None:
    assert strategies_ctx.loaded is not None
    assert name in strategies_ctx.loaded.filters


@then(parsers.parse("the real loaded strategy's meta-learner families are \"{families}\""))
def _real_loaded_families(strategies_ctx: _StrategiesCtx, families: str) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.meta_learner_families == _split(families)


@then(parsers.parse('the real loaded strategy extends "{base}"'))
def _real_extends_base(strategies_ctx: _StrategiesCtx, base: str) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.extends == base
