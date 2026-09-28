"""Steps for strategies.feature — the `extends:`-composing strategy-chain config loader."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest
import yaml
from algo_backtest.strategies import (
    StrategyChainConfig,
    load_resolved_strategy,
    load_strategy_chain_config,
    resolved_yaml,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/strategies.feature")


@dataclass
class _StrategiesCtx:
    """Per-scenario fixture context: the config-dir root plus the loaded outcome/error."""

    root: Path
    loaded: StrategyChainConfig | None = None
    reloaded: StrategyChainConfig | None = None
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


def _read_config(root: Path, name: str) -> dict[str, Any]:
    body = yaml.safe_load((_config_dir(root, name) / "config.yaml").read_text())
    assert isinstance(body, dict)
    return body


def _amend_config(root: Path, name: str, amend: Callable[[dict[str, Any]], None]) -> None:
    """Read-modify-write one already-written strategy config."""
    body = _read_config(root, name)
    amend(body)
    _write_config(root, name, body)


# One valid parameter section per configurable filter, so a scenario that lists the
# filter gets a complete config unless it deliberately breaks it.
_SECTIONS: dict[str, tuple[str, dict[str, Any]]] = {
    "f2_indicator": ("indicator", {"rsi_midline": 50.0, "macd_hist_threshold": 0.0}),
    "f3_pattern": (
        "pattern",
        {
            "bullish_patterns": ["bullish_engulfing", "hammer", "morning_star"],
            "bearish_patterns": ["bearish_engulfing", "shooting_star", "evening_star"],
        },
    ),
    "f4_news_context": (
        "news_context",
        {"event_intensity_veto_threshold": -0.5, "sentiment_direction_threshold": 0.15},
    ),
    "f5_risk_guard": (
        "risk_guard",
        {
            "portfolio_at_risk_cap": 0.1, "daily_drawdown_limit": -0.05,
            "weekly_drawdown_limit": -0.15, "max_concurrent_trades_per_account": 5,
            "max_leverage": 30,
        },
    ),
    "f6_capital_mgmt": (
        "capital_mgmt",
        {
            "risk_per_trade": 0.03, "stop_loss_pips": 20.0, "pip_value_per_lot": 10.0,
            "lot_notional_units": 100_000, "assumed_leverage": 30,
        },
    ),
}
_F7_KEYS: dict[str, Any] = {"theta_high": 0.55, "theta_low": 0.45, "regime_gate": False}


def _body(filters: tuple[str, ...], families: tuple[str, ...]) -> dict[str, Any]:
    """A complete config body: every listed configurable filter gets its section."""
    meta_learner: dict[str, Any] = {"families": list(families)}
    if "f7_meta_learner" in filters:
        meta_learner.update(_F7_KEYS)
    body: dict[str, Any] = {
        "schema_version": 2, "filters": list(filters), "meta_learner": meta_learner,
    }
    for name in filters:
        if name in _SECTIONS:
            section, values = _SECTIONS[name]
            body[section] = dict(values)
    return body


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
    _write_config(strategies_ctx.root, name, _body(_split(filters), _split(families)))


@given(parsers.parse('"{name}" also declares meta_learner.theta_high {value:g}'))
def _amend_theta_high(strategies_ctx: _StrategiesCtx, name: str, value: float) -> None:
    """Amend an already-written strategy config's nested `meta_learner` key, so a merge
    test can prove a base-only key survives `extends:` composition."""
    _amend_config(
        strategies_ctx.root, name, lambda b: b["meta_learner"].__setitem__("theta_high", value)
    )


@given(parsers.parse('"{name}" also declares risk_guard.max_leverage {value:g}'))
def _amend_max_leverage(strategies_ctx: _StrategiesCtx, name: str, value: float) -> None:
    """Override one key of an inherited `risk_guard` section in a child config."""
    _amend_config(
        strategies_ctx.root, name,
        lambda b: b.setdefault("risk_guard", {}).__setitem__("max_leverage", value),
    )


@given(parsers.parse('"{name}" also declares {section}.{key} as {value}'))
def _amend_section_key(
    strategies_ctx: _StrategiesCtx, name: str, section: str, key: str, value: str
) -> None:
    """Set one key of any section (created if absent); the value is flow-style YAML."""
    _amend_config(
        strategies_ctx.root, name,
        lambda b: b.setdefault(section, {}).__setitem__(key, yaml.safe_load(value)),
    )


@given(parsers.parse('"{name}" adds meta_learner key "{key}" with value {value}'))
def _add_meta_learner_key(strategies_ctx: _StrategiesCtx, name: str, key: str, value: str) -> None:
    _amend_config(
        strategies_ctx.root, name,
        lambda b: b["meta_learner"].__setitem__(key, yaml.safe_load(value)),
    )


@given(parsers.parse('"{name}" sets schema_version to {value}'))
def _set_schema_version(strategies_ctx: _StrategiesCtx, name: str, value: str) -> None:
    """`absent` removes the key; anything else is parsed as YAML (so "2" stays a string)."""
    def amend(body: dict[str, Any]) -> None:
        if value == "absent":
            body.pop("schema_version")
        else:
            body["schema_version"] = yaml.safe_load(value)

    _amend_config(strategies_ctx.root, name, amend)


@given(parsers.parse('"{name}" sets extends to {value}'))
def _set_extends(strategies_ctx: _StrategiesCtx, name: str, value: str) -> None:
    """`extends` as any YAML value, so a non-string can be proven a hard stop."""
    _amend_config(
        strategies_ctx.root, name, lambda b: b.__setitem__("extends", yaml.safe_load(value))
    )


@given(parsers.parse('"{name}" is changed to extend "{base}"'))
def _make_extend(strategies_ctx: _StrategiesCtx, name: str, base: str) -> None:
    _amend_config(strategies_ctx.root, name, lambda b: b.__setitem__("extends", base))


@given(parsers.parse('"{name}" sets its "{section}" section to null'))
def _null_section(strategies_ctx: _StrategiesCtx, name: str, section: str) -> None:
    """A child's explicit top-level `null`: the loader drops the inherited section."""
    _amend_config(strategies_ctx.root, name, lambda b: b.__setitem__(section, None))


@given(parsers.parse('"{name}" drops its "{section}" section'))
def _drop_section(strategies_ctx: _StrategiesCtx, name: str, section: str) -> None:
    _amend_config(strategies_ctx.root, name, lambda b: b.pop(section))


@given(parsers.parse('"{name}" drops meta_learner key "{key}"'))
def _drop_meta_learner_key(strategies_ctx: _StrategiesCtx, name: str, key: str) -> None:
    _amend_config(strategies_ctx.root, name, lambda b: b["meta_learner"].pop(key))


@given(parsers.parse('"{name}" adds a "{section}" section {section_yaml}'))
def _add_section_yaml(
    strategies_ctx: _StrategiesCtx, name: str, section: str, section_yaml: str
) -> None:
    """Add (or replace) a section from the table's flow-style YAML mapping."""
    value = yaml.safe_load(section_yaml)
    _amend_config(strategies_ctx.root, name, lambda b: b.__setitem__(section, value))


@given(parsers.parse('"{name}" adds a "{section}" section anyway'))
def _add_stray_section(strategies_ctx: _StrategiesCtx, name: str, section: str) -> None:
    values = next(v for s, v in _SECTIONS.values() if s == section)
    _amend_config(strategies_ctx.root, name, lambda b: b.__setitem__(section, dict(values)))


@given(parsers.parse('"{name}" replaces its "{section}" section with a scalar'))
def _scalar_section(strategies_ctx: _StrategiesCtx, name: str, section: str) -> None:
    _amend_config(strategies_ctx.root, name, lambda b: b.__setitem__(section, "not-a-mapping"))


@given(
    parsers.parse(
        '"{name}" extends "{base}" with filters "{filters}" and families "{families}"'
    )
)
def _extending_config(
    strategies_ctx: _StrategiesCtx, name: str, base: str, filters: str, families: str
) -> None:
    """A child config: only the sections the base lacks are written, the rest inherit."""
    base_body = _read_config(strategies_ctx.root, base)
    body = _body(_split(filters), _split(families))
    keep = {"filters", "schema_version"}
    defaultable = {"indicator", "pattern", "price_features"}
    body = {
        k: v for k, v in body.items()
        if (k not in base_body or k in keep) and k not in defaultable
    }
    body["meta_learner"] = {"families": list(_split(families))}
    base_has_f7 = "f7_meta_learner" in base_body.get("filters", [])
    if "f7_meta_learner" in _split(filters) and not base_has_f7:
        body["meta_learner"].update(_F7_KEYS)
    body["extends"] = base
    _write_config(strategies_ctx.root, name, body)


@given(parsers.parse('a strategy config directory with an empty filters list for "{name}"'))
def _empty_filters_config(strategies_ctx: _StrategiesCtx, name: str) -> None:
    _write_config(
        strategies_ctx.root, name, {"schema_version": 2, "filters": [], "meta_learner": {}}
    )


@given(parsers.parse('a strategy config directory with no filters key at all for "{name}"'))
def _no_filters_key_config(strategies_ctx: _StrategiesCtx, name: str) -> None:
    _write_config(strategies_ctx.root, name, {"schema_version": 2, "meta_learner": {}})


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
        {"schema_version": 2, "filters": list(_split(filters)), "meta_learner": "not-a-mapping"},
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
        {"schema_version": 2, "filters": list(_split(filters)), "meta_learner": {}},
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
            "schema_version": 2,
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
            "schema_version": 2,
            "filters": list(_split(filters)),
            "meta_learner": {"families": {"a": 1}},
        },
    )


@given(
    parsers.parse(
        'a strategy config directory with "{name}" filters "{filters}" and '
        "meta_learner.families containing a non-string entry"
    )
)
def _non_string_families_config(strategies_ctx: _StrategiesCtx, name: str, filters: str) -> None:
    _write_config(
        strategies_ctx.root,
        name,
        {
            "schema_version": 2,
            "filters": list(_split(filters)),
            "meta_learner": {"families": ["trend", 7]},
        },
    )


@given(parsers.parse('"{name}" extends "{base}" overriding meta_learner with a scalar value'))
def _extends_scalar_meta_learner(strategies_ctx: _StrategiesCtx, name: str, base: str) -> None:
    _write_config(
        strategies_ctx.root,
        name,
        {
            "schema_version": 2,
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


@then(parsers.parse("the loaded strategy's F7 config has theta_high {value:g}"))
def _loaded_f7_theta_high(strategies_ctx: _StrategiesCtx, value: float) -> None:
    assert strategies_ctx.loaded is not None and strategies_ctx.loaded.f7 is not None
    assert strategies_ctx.loaded.f7.theta_high == pytest.approx(value)


@then(parsers.parse("the loaded strategy's risk-guard caps have max_leverage {value:g}"))
def _loaded_max_leverage(strategies_ctx: _StrategiesCtx, value: float) -> None:
    assert strategies_ctx.loaded is not None and strategies_ctx.loaded.risk_guard is not None
    assert strategies_ctx.loaded.risk_guard.max_leverage == pytest.approx(value)


@then(parsers.parse("the loaded strategy's risk-guard caps have daily_drawdown_limit {value:g}"))
def _loaded_daily_limit(strategies_ctx: _StrategiesCtx, value: float) -> None:
    assert strategies_ctx.loaded is not None and strategies_ctx.loaded.risk_guard is not None
    assert strategies_ctx.loaded.risk_guard.daily_drawdown_limit == pytest.approx(value)


_TYPED_ATTR = {
    "indicator": "indicator", "pattern": "pattern",
    "news_context": "news_context", "risk_guard": "risk_guard",
    "capital_mgmt": "capital_mgmt", "meta_learner": "f7",
}


@then(
    parsers.parse(
        "the loaded strategy's price features are ema_fast {fast:d}, ema_slow {slow:d}, "
        "ema_higher_tf {htf:d}, rsi_period {rsi:d}, macd_fast {mf:d}, macd_slow {ms:d}, "
        "macd_signal {sig:d}"
    )
)
def _loaded_price_features(  # noqa: PLR0913 - one parameter per table column
    strategies_ctx: _StrategiesCtx,
    fast: int, slow: int, htf: int, rsi: int, mf: int, ms: int, sig: int,
) -> None:
    assert strategies_ctx.loaded is not None
    pf = strategies_ctx.loaded.price_features
    assert (pf.ema_fast, pf.ema_slow, pf.ema_higher_tf) == (fast, slow, htf)
    assert (pf.rsi_period, pf.macd_fast, pf.macd_slow, pf.macd_signal) == (rsi, mf, ms, sig)


@then(
    parsers.parse(
        "the loaded strategy's execution config is spread_pips {spread:g}, "
        "commission_per_lot {commission:g}, min_hold_bars {hold:d}, "
        "broker_stop_level_pips {level:g}"
    )
)
def _loaded_execution(
    strategies_ctx: _StrategiesCtx, spread: float, commission: float, hold: int, level: float
) -> None:
    assert strategies_ctx.loaded is not None
    execution = strategies_ctx.loaded.execution
    assert (execution.spread_pips, execution.commission_per_lot) == (spread, commission)
    assert (execution.min_hold_bars, execution.broker_stop_level_pips) == (hold, level)


@then(parsers.parse("the loaded strategy's raw config records {section}.{key} {value}"))
def _raw_records(strategies_ctx: _StrategiesCtx, section: str, key: str, value: str) -> None:
    """Effective (possibly defaulted) values must appear in `raw`, hence in strategy-config.json."""
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.raw[section][key] == yaml.safe_load(value)


@then(parsers.parse('the loaded strategy\'s raw config has no "{section}" section'))
def _raw_lacks_section(strategies_ctx: _StrategiesCtx, section: str) -> None:
    """A dropped section is absent from `raw`, hence from strategy-config.{json,yaml}."""
    assert strategies_ctx.loaded is not None
    assert section not in strategies_ctx.loaded.raw, sorted(strategies_ctx.loaded.raw)


@then(parsers.parse('the loaded strategy records no provenance under "{prefix}"'))
def _no_provenance_under(strategies_ctx: _StrategiesCtx, prefix: str) -> None:
    """Neither the dropped section nor any key inside it keeps a provenance entry."""
    assert strategies_ctx.loaded is not None
    provenance = strategies_ctx.loaded.provenance
    stale = [k for k in provenance if k == prefix or k.startswith(f"{prefix}.")]
    assert stale == [], stale


@then(parsers.parse('the loaded strategy has a typed "{section}" config'))
def _typed_section(strategies_ctx: _StrategiesCtx, section: str) -> None:
    assert strategies_ctx.loaded is not None
    assert getattr(strategies_ctx.loaded, _TYPED_ATTR[section]) is not None


@then(parsers.parse('the loaded strategy has no "{section}" config'))
def _no_typed_section(strategies_ctx: _StrategiesCtx, section: str) -> None:
    assert strategies_ctx.loaded is not None
    assert getattr(strategies_ctx.loaded, _TYPED_ATTR[section]) is None


@then(parsers.parse('the real loaded strategy has typed "{sections}" configs'))
def _real_typed_sections(strategies_ctx: _StrategiesCtx, sections: str) -> None:
    assert strategies_ctx.loaded is not None
    for section in _split(sections):
        assert getattr(strategies_ctx.loaded, _TYPED_ATTR[section]) is not None, section


@then(parsers.parse('the real loaded strategy has no "{section}" config'))
def _real_no_typed_section(strategies_ctx: _StrategiesCtx, section: str) -> None:
    assert strategies_ctx.loaded is not None
    assert getattr(strategies_ctx.loaded, _TYPED_ATTR[section]) is None


@then(
    parsers.parse(
        "the real loaded strategy's F7 config has theta_high {high:g}, theta_low {low:g} and "
        "the regime gate {gate}"
    )
)
def _real_f7_config(strategies_ctx: _StrategiesCtx, high: float, low: float, gate: str) -> None:
    assert strategies_ctx.loaded is not None and strategies_ctx.loaded.f7 is not None
    f7 = strategies_ctx.loaded.f7
    assert (f7.theta_high, f7.theta_low) == pytest.approx((high, low))
    assert f7.regime_gate is (gate == "on")


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


@when(
    parsers.parse(
        'the loaded strategy is dumped to a resolved YAML file and loaded back as "{name}"'
    )
)
def _round_trip(strategies_ctx: _StrategiesCtx, name: str) -> None:
    assert strategies_ctx.loaded is not None
    path = strategies_ctx.root / "strategy.yaml"
    path.write_text(resolved_yaml(strategies_ctx.loaded))
    strategies_ctx.reloaded = load_resolved_strategy(path, name=name)


@then("the reloaded strategy equals the loaded one apart from its extends provenance")
def _round_trip_equal(strategies_ctx: _StrategiesCtx) -> None:
    """The resolved document has no `extends` left to record; everything else must match."""
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.reloaded == replace(strategies_ctx.loaded, extends=None)


@given(parsers.parse('a resolved strategy file for "{name}" that still declares extends'))
def _resolved_with_extends(strategies_ctx: _StrategiesCtx, name: str) -> None:
    body = _body(("f1_trend",), ("trend",))
    body["extends"] = "baseline"
    (strategies_ctx.root / "strategy.yaml").write_text(yaml.safe_dump(body))


@when(parsers.parse('loading the resolved strategy file as "{name}" fails'))
def _load_resolved_fails(strategies_ctx: _StrategiesCtx, name: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        load_resolved_strategy(strategies_ctx.root / "strategy.yaml", name=name)
    strategies_ctx.error = exc_info.value


@given(
    parsers.parse(
        'an external strategy config directory with "{name}" extending bundled "{base}" and '
        "meta_learner theta_high {value:g}"
    )
)
def _external_variant(strategies_ctx: _StrategiesCtx, name: str, base: str, value: float) -> None:
    """Only the variant lives in the external root; its base must resolve from the package."""
    _write_config(
        strategies_ctx.root, name,
        {"extends": base, "meta_learner": {"theta_high": value}},
    )


@when(parsers.parse('strategy "{name}" is loaded from that external directory'))
def _load_external(strategies_ctx: _StrategiesCtx, name: str) -> None:
    strategies_ctx.loaded = load_strategy_chain_config(name, root=strategies_ctx.root)


@then(parsers.parse('the loaded strategy\'s filters end with "{names}"'))
def _loaded_filters_end_with(strategies_ctx: _StrategiesCtx, names: str) -> None:
    assert strategies_ctx.loaded is not None
    tail = _split(names)
    assert strategies_ctx.loaded.filters[-len(tail):] == tail


@then(parsers.parse('the loaded strategy\'s parameter "{key}" comes from "{source}"'))
def _provenance(strategies_ctx: _StrategiesCtx, key: str, source: str) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.provenance.get(key) == source, strategies_ctx.loaded.provenance


@then(parsers.parse('the reloaded strategy\'s parameter "{key}" comes from "{source}"'))
def _reloaded_provenance(strategies_ctx: _StrategiesCtx, key: str, source: str) -> None:
    """A resolved document attributes every parameter it carries to its own file name."""
    assert strategies_ctx.reloaded is not None
    provenance = strategies_ctx.reloaded.provenance
    assert provenance.get(key) == source, provenance


@given(parsers.parse('"{name}" sets extends to {value}'))
def _set_extends(strategies_ctx: _StrategiesCtx, name: str, value: str) -> None:
    """Set `extends` from the table's YAML so a non-string value can be tried."""
    _amend_config(
        strategies_ctx.root, name, lambda b: b.__setitem__("extends", yaml.safe_load(value))
    )


@given(parsers.parse('"{name}" drops "{section}" key "{key}"'))
def _drop_section_key(strategies_ctx: _StrategiesCtx, name: str, section: str, key: str) -> None:
    """Remove one key from an already-written filter section, leaving the section listed."""
    _amend_config(strategies_ctx.root, name, lambda b: b[section].pop(key))


@given(parsers.parse('"{name}" sets perception_source to {source}'))
def _set_perception_source(strategies_ctx: _StrategiesCtx, name: str, source: str) -> None:
    """Declare the F1 perception source at the top level of the config."""
    _amend_config(strategies_ctx.root, name, lambda b: b.__setitem__("perception_source", source))


@given(parsers.parse('a strategy config directory with "{name}" filters as the scalar "{scalar}"'))
def _scalar_filters_config(strategies_ctx: _StrategiesCtx, name: str, scalar: str) -> None:
    """`filters:` written as a bare string where a one-item list was meant."""
    _write_config(
        strategies_ctx.root, name,
        {"schema_version": 2, "filters": scalar, "meta_learner": {"families": ["trend"]}},
    )


@then(parsers.parse('the loaded strategy\'s perception source is "{source}"'))
def _perception_source(strategies_ctx: _StrategiesCtx, source: str) -> None:
    assert strategies_ctx.loaded is not None
    assert strategies_ctx.loaded.perception.source == source
