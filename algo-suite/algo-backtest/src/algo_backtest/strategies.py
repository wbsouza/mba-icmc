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

from algo_backtest.chain.filters.f4_news_context import (
    NewsContextConfig,
    parse_news_context_config,
)
from algo_backtest.chain.filters.f6_capital_mgmt import (
    CapitalMgmtConfig,
    parse_capital_mgmt_config,
)
from algo_backtest.chain.filters.f7_meta_learner import F7Config, parse_f7_config
from algo_backtest.perception.config import PerceptionConfig, parse_perception_config
from algo_backtest.rules.risk_guard import RiskGuardCaps, parse_risk_guard_caps

# Which config.yaml section each configurable filter reads (F7 reads `meta_learner`,
# shared with the feature-family list, so it is handled separately).
_SECTION_FOR_FILTER: dict[str, str] = {
    "f4_news_context": "news_context",
    "f5_risk_guard": "risk_guard",
    "f6_capital_mgmt": "capital_mgmt",
}


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


def _typed_sections(
    name: str, merged: Mapping[str, Any], filters: tuple[str, ...], meta_learner: Mapping[str, Any]
) -> dict[str, Any]:
    """Every listed configurable filter's section, parsed by that filter's own parser."""
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
        "f7": (
            parse_f7_config(meta_learner, strategy=name) if "f7_meta_learner" in filters else None
        ),
    }


def load_strategy_chain_config(name: str, *, root: Path | None = None) -> StrategyChainConfig:
    """Resolve one strategy's chain config, composing a single `extends:` level if present.

    Raises:
        ValueError: the strategy (or its base) has no `config.yaml`, the base itself
            declares `extends:` (only one level is supported), `filters:` resolves
            empty (a chain with no filters can never reach a terminal decision),
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

    filters = tuple(_ensure_str_list(name, "filters", merged.get("filters", ())))
    if not filters:
        raise ValueError(f"strategy {name!r} resolves an empty filters list — check its config")
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
