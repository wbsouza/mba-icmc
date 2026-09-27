"""Strategy-chain config loading (Spec 04h): `src/algo_backtest/strategies/<name>/
config.yaml`, bundled alongside `algos/` (same `Path(__file__).parent`-relative,
packaging-independent pattern `run.py` already uses for `algos/`).

Config, not code, decides which filters a strategy runs, in what order, and with which
parameters (specs.md §11.3.1: "Adding, removing or reordering a filter requires editing
config.yaml, not the engine code"; 2026-09-27 amendment, story 09: each configurable
filter owns a section of the same file — `news_context` for F4, `risk_guard` for F5,
`capital_mgmt` for F6 and `meta_learner.theta_high/theta_low/regime_gate` for F7 — parsed
by that filter's own `parse_*_config`, and a filter listed without its section, or a
section without its filter, is a hard stop). `baseline` and `hybrid` are the two Spec 04 variants
(`docs/experiments.md` §1: "hybrid extends baseline adding F4"), composed via a single
level of ``extends:`` — deliberately **not** the general cycle-detecting inheritance
`technical-debt.md` TD-8 defers ("a flat, non-cyclic two-level extends does not need that
machinery"): a strategy's base may not itself declare ``extends:`` — that's a hard stop
here, not a chain to walk.

Merge policy mirrors `algo_core.config.resolution._deep_merge` (the same policy this
workspace already uses for `conf/algo.yaml` < `conf/<tool>.yaml` layering): the child's
top-level keys — including ``filters:`` — replace the base's wholesale; nested mappings
(e.g. ``meta_learner:``) merge key-by-key, child wins. A strategy's ``filters:`` list is
always written out in full (not a diff/insert against the base) — an explicit complete
list is easier to audit in a review (and in the Mermaid diagram it drives) than a
positional "insert F4 after F3" DSL would be.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from algo_backtest.chain.filters.f2_indicator import (
    IndicatorConfig,
    indicator_mapping,
    parse_indicator_config,
)
from algo_backtest.chain.filters.f3_pattern import (
    PatternConfig,
    parse_pattern_config,
    pattern_mapping,
)
from algo_backtest.chain.filters.f4_news_context import (
    NewsContextConfig,
    parse_news_context_config,
)
from algo_backtest.chain.filters.f6_capital_mgmt import (
    CapitalMgmtConfig,
    parse_capital_mgmt_config,
)
from algo_backtest.chain.filters.f7_meta_learner import F7Config, parse_f7_config
from algo_backtest.chain.price_features import (
    PriceFeatureConfig,
    parse_price_features_config,
    price_features_mapping,
)
from algo_backtest.perception.config import PerceptionConfig, parse_perception_config
from algo_backtest.rules.risk_guard import RiskGuardCaps, parse_risk_guard_caps

# The config.yaml schema this loader understands: v2 added the per-filter sections.
SCHEMA_VERSION = 2

# Every filter name a `filters:` list may contain (chain/wiring.py builds them).
KNOWN_FILTERS: frozenset[str] = frozenset(
    {
        "f1_trend", "f2_indicator", "f3_pattern", "f4_news_context", "f5_risk_guard",
        "f6_capital_mgmt", "f7_meta_learner",
    }
)

# Which config.yaml section each configurable filter reads (F7 reads `meta_learner`,
# shared with the feature-family list, so it is handled separately). The first two
# have defaults for every key, so their section may be omitted when the filter is listed;
# the last three are trading-impactful and must be spelled out.
_SECTION_FOR_FILTER: dict[str, str] = {
    "f2_indicator": "indicator",
    "f3_pattern": "pattern",
    "f4_news_context": "news_context",
    "f5_risk_guard": "risk_guard",
    "f6_capital_mgmt": "capital_mgmt",
}
_DEFAULTABLE_FILTERS = frozenset({"f2_indicator", "f3_pattern"})
_F7_KEYS = ("theta_high", "theta_low", "regime_gate")


@dataclass(frozen=True)
class StrategyChainConfig:
    """One strategy's resolved filters, feature families and F1 perception source.

    ``raw`` is the fully-merged config dict (post-`extends:` composition) — every key,
    including sections this module does not interpret — so a future filter (e.g. F5/F6's own
    per-strategy threshold overrides) can read its own section without this module
    needing to know its schema in advance.
    """

    name: str
    filters: tuple[str, ...]
    meta_learner_families: tuple[str, ...]
    extends: str | None
    raw: Mapping[str, Any]
    perception: PerceptionConfig = PerceptionConfig()
    price_features: PriceFeatureConfig = PriceFeatureConfig()
    indicator: IndicatorConfig | None = None
    pattern: PatternConfig | None = None
    news_context: NewsContextConfig | None = None
    risk_guard: RiskGuardCaps | None = None
    capital_mgmt: CapitalMgmtConfig | None = None
    f7: F7Config | None = None


def strategies_root() -> Path:
    """The bundled `strategies/` directory, alongside `algos/` (same reliable
    `Path(__file__).parent`-relative pattern `run.py` already uses to locate `algos/`,
    so both survive being run from any working directory or packaging layout)."""
    return Path(__file__).parent / "strategies"


def _config_path(root: Path, name: str) -> Path:
    return root / name / "config.yaml"


def _read_yaml(root: Path, name: str) -> dict[str, Any]:
    """Read and parse one strategy's `config.yaml`, failing fast if it's missing/malformed."""
    path = _config_path(root, name)
    if not path.is_file():
        raise ValueError(
            f"unknown strategy {name!r}: no config at {path} — create "
            f"strategies/{name}/config.yaml first"
        )
    parsed = yaml.safe_load(path.read_text())
    if not isinstance(parsed, dict):
        raise ValueError(f"strategy config {path} must contain a YAML mapping")
    return parsed


def _deep_merge(base: dict[str, Any], over: Mapping[str, Any]) -> dict[str, Any]:
    """Recursively merge `over` onto a copy of `base` (`over` wins on scalar/list conflict)."""
    merged = dict(base)
    for key, value in over.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, Mapping):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def _ensure_str_list(strategy_name: str, field: str, value: object) -> list[str]:
    """Reject a config value that `tuple()` would silently accept but isn't really a list.

    A YAML scalar string (e.g. ``filters: f1_trend`` where a one-item list ``[f1_trend]``
    was meant) is iterable, so `tuple("f1_trend")` would split it into individual
    characters instead of raising — a config typo turning into a nonsensical filter chain
    with no error at all. Reject anything that isn't a real list/tuple up front.
    """
    if isinstance(value, str) or not isinstance(value, list | tuple):
        raise ValueError(
            f"strategy {strategy_name!r}: {field!r} must be a list (got "
            f"{type(value).__name__!r}: {value!r}) — check its config.yaml"
        )
    bad_items = [item for item in value if not isinstance(item, str)]
    if bad_items:
        raise ValueError(
            f"strategy {strategy_name!r}: {field!r} must contain only strings "
            f"(bad values={bad_items!r}) — check its config.yaml"
        )
    return list(value)


def _filter_section(
    name: str, merged: Mapping[str, Any], filters: tuple[str, ...], filter_name: str
) -> dict[str, Any] | None:
    """The parameter section for `filter_name` iff the filter is listed; mismatches fail fast.

    Raises:
        ValueError: the filter is listed without its section, the section is present
            without its filter, or the section is not a mapping.
    """
    section = _SECTION_FOR_FILTER[filter_name]
    listed, present = filter_name in filters, section in merged
    if listed and not present and filter_name in _DEFAULTABLE_FILTERS:
        return {}
    if listed and not present:
        raise ValueError(
            f"strategy {name!r} lists {filter_name!r} but has no '{section}:' section — add "
            f"the filter's parameters to strategies/{name}/config.yaml"
        )
    if present and not listed:
        raise ValueError(
            f"strategy {name!r} declares a '{section}:' section but does not list "
            f"{filter_name!r} in filters — remove the section or add the filter"
        )
    if not listed:
        return None
    value = merged[section]
    if not isinstance(value, dict):
        raise ValueError(
            f"strategy {name!r}: '{section}' must be a mapping (got "
            f"{type(value).__name__!r}) — check its config.yaml"
        )
    return value


def _require_schema_version(name: str, merged: Mapping[str, Any]) -> None:
    """Fail fast unless the config declares the schema version this loader understands.

    Raises:
        ValueError: `schema_version` is absent, not an integer, or not `SCHEMA_VERSION`.
    """
    version = merged.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        raise ValueError(
            f"strategy {name!r}: schema_version must be the integer {SCHEMA_VERSION} (got "
            f"{version!r}) — v{SCHEMA_VERSION} moved every filter's parameters into its own "
            "section (news_context, risk_guard, capital_mgmt, meta_learner.theta_*/regime_gate); "
            f"migrate strategies/{name}/config.yaml and set schema_version: {SCHEMA_VERSION}"
        )


def _require_known_filters(name: str, filters: tuple[str, ...]) -> None:
    """Fail fast on a filter name the chain cannot build (a typo would otherwise surface
    only when the LEAN algorithm initialises inside the container).

    Raises:
        ValueError: naming the unknown entries and the known filters.
    """
    unknown = [f for f in filters if f not in KNOWN_FILTERS]
    if unknown:
        raise ValueError(
            f"strategy {name!r}: unknown filters {unknown!r} in filters — known filters: "
            f"{sorted(KNOWN_FILTERS)}; check its config.yaml"
        )


def _reject_stray_f7_keys(
    name: str, filters: tuple[str, ...], meta_learner: Mapping[str, Any]
) -> None:
    """F7's rule parameters without F7 in the chain would be silently ignored — refuse them.

    Raises:
        ValueError: a `meta_learner` F7 key is present but `f7_meta_learner` is not listed.
    """
    stray = [key for key in _F7_KEYS if key in meta_learner]
    if stray and "f7_meta_learner" not in filters:
        raise ValueError(
            f"strategy {name!r}: meta_learner declares {stray!r} but does not list "
            "'f7_meta_learner' in filters — remove the keys or add the filter"
        )


def _defaulted_sections(
    name: str, merged: dict[str, Any], filters: tuple[str, ...], meta_learner: dict[str, Any]
) -> dict[str, Any]:
    """The sections with defaults (price_features, indicator, pattern, F7's horizon):
    parsed, and their *effective* values written back into `merged` so the run's
    `strategy-config.json` records what was actually used, defaults included."""
    price_raw = merged.get("price_features", {})
    if not isinstance(price_raw, dict):
        raise ValueError(
            f"strategy {name!r}: 'price_features' must be a mapping (got "
            f"{type(price_raw).__name__!r}) — check its config.yaml"
        )
    price = parse_price_features_config(price_raw, strategy=name)
    merged["price_features"] = price_features_mapping(price)
    indicator_raw = _filter_section(name, merged, filters, "f2_indicator")
    indicator = (
        parse_indicator_config(indicator_raw, strategy=name) if indicator_raw is not None else None
    )
    if indicator is not None:
        merged["indicator"] = indicator_mapping(indicator)
    pattern_raw = _filter_section(name, merged, filters, "f3_pattern")
    pattern = parse_pattern_config(pattern_raw, strategy=name) if pattern_raw is not None else None
    if pattern is not None:
        merged["pattern"] = pattern_mapping(pattern)
    f7 = parse_f7_config(meta_learner, strategy=name) if "f7_meta_learner" in filters else None
    if f7 is not None:
        meta_learner.setdefault("label_horizon_minutes", f7.label_horizon_minutes)
    return {"price_features": price, "indicator": indicator, "pattern": pattern, "f7": f7}


def _typed_sections(
    name: str, merged: dict[str, Any], filters: tuple[str, ...], meta_learner: dict[str, Any]
) -> dict[str, Any]:
    """Every listed configurable filter's section, parsed by that filter's own parser."""
    _reject_stray_f7_keys(name, filters, meta_learner)
    news = _filter_section(name, merged, filters, "f4_news_context")
    risk = _filter_section(name, merged, filters, "f5_risk_guard")
    capital = _filter_section(name, merged, filters, "f6_capital_mgmt")
    return {
        "news_context": (
            parse_news_context_config(news, strategy=name) if news is not None else None
        ),
        "risk_guard": parse_risk_guard_caps(risk, strategy=name) if risk is not None else None,
        "capital_mgmt": (
            parse_capital_mgmt_config(capital, strategy=name) if capital is not None else None
        ),
        **_defaulted_sections(name, merged, filters, meta_learner),
    }


def load_strategy_chain_config(name: str, *, root: Path | None = None) -> StrategyChainConfig:
    """Resolve one strategy's chain config, composing a single `extends:` level if present.

    Raises:
        ValueError: the strategy (or its base) has no `config.yaml`, the base itself
            declares `extends:` (only one level is supported), `filters:` resolves
            empty (a chain with no filters can never reach a terminal decision), a
            filter name is unknown, `schema_version` is not the current integer,
            `meta_learner:` is present but not a mapping (a malformed config type,
            distinct from the section being absent entirely — that legitimately
            resolves to no feature families), or a configurable filter's own section
            is missing, stray or invalid (`_filter_section` and each `parse_*_config`).
    """
    resolved_root = root if root is not None else strategies_root()
    raw = _read_yaml(resolved_root, name)
    base_name = raw.get("extends")
    if base_name is not None:
        base_raw = _read_yaml(resolved_root, base_name)
        if "extends" in base_raw:
            raise ValueError(
                f"strategy {base_name!r} (the base of {name!r}) itself declares 'extends' "
                "— only one level of extends is supported (technical-debt.md TD-8)"
            )
        merged = _deep_merge(base_raw, {k: v for k, v in raw.items() if k != "extends"})
    else:
        merged = raw

    _require_schema_version(name, merged)
    filters = tuple(_ensure_str_list(name, "filters", merged.get("filters", ())))
    if not filters:
        raise ValueError(f"strategy {name!r} resolves an empty filters list — check its config")
    _require_known_filters(name, filters)
    meta_learner = merged.get("meta_learner", {})
    if not isinstance(meta_learner, dict):
        raise ValueError(
            f"strategy {name!r}: 'meta_learner' must be a mapping (got "
            f"{type(meta_learner).__name__!r}) — check its config.yaml"
        )
    families_raw = meta_learner.get("families", ())
    families = tuple(_ensure_str_list(name, "meta_learner.families", families_raw))
    return StrategyChainConfig(
        name=name, filters=filters, meta_learner_families=families, extends=base_name, raw=merged,
        perception=parse_perception_config(merged),
        **_typed_sections(name, merged, filters, meta_learner),
    )
