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
(`docs/experiments.md` §1: "hybrid extends baseline adding F4"); `news-only` extends
baseline keeping F4–F7 alone on the news family — all composed via
``extends:`` chains of any depth (2026-09-27: `base → variant → sub-variant`, like
docker-compose override files or the reference engine's Spring `parent=` beans), walked
base-first with cycle detection; a base is looked up in the same directory first and then
in the bundled `strategies/`, so a variant in an external `--strategies-dir` can extend
`baseline`. The general `algo_core.config`-level inheritance `technical-debt.md` TD-8
defers is a different item.

Merge policy mirrors `algo_core.config.resolution._deep_merge` (the same policy this
workspace already uses for `conf/algo.yaml` < `conf/<tool>.yaml` layering): the child's
top-level keys — including ``filters:`` — replace the base's wholesale; nested mappings
(e.g. ``meta_learner:``) merge key-by-key, child wins. A strategy's ``filters:`` list is
always written out in full (not a diff/insert against the base) — an explicit complete
list is easier to audit in a review (and in the Mermaid diagram it drives) than a
positional "insert F4 after F3" DSL would be. A child drops an inherited top-level
section by setting it to ``null`` (``pattern: null`` — the compose-file ``!reset`` idea):
the merged document then has no such section, so a variant that removes a filter from
the chain can also remove the filter's section instead of tripping the section-without-
filter hard stop. Only a *top-level* key is dropped this way; a ``null`` inside a
section keeps its per-key meaning (e.g. ``risk_guard.max_leverage: null`` disables a cap).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from algo_backtest.chain.execution_config import (
    ExecutionConfig,
    execution_mapping,
    parse_execution_config,
)
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
    news_context_mapping,
    parse_news_context_config,
)
from algo_backtest.chain.filters.f6_capital_mgmt import (
    CapitalMgmtConfig,
    capital_mgmt_mapping,
    parse_capital_mgmt_config,
)
from algo_backtest.chain.filters.f7_meta_learner import F7Config, FeatureFamily, parse_f7_config
from algo_backtest.chain.filters.volume_strength import VolumeConfig, parse_volume_config
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
        "f6_capital_mgmt", "f7_meta_learner", "volume_strength",
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
    "volume_strength": "volume_strength",
}
_DEFAULTABLE_FILTERS = frozenset({"f2_indicator", "f3_pattern"})
# The filters whose recommendation carries a direction (BUY/SELL), so one of them may close
# a chain that runs no F7 as its `terminal_filter`; F5/F6/volume only gate.
DIRECTION_FILTERS: frozenset[str] = frozenset(
    {"f1_trend", "f2_indicator", "f3_pattern", "f4_news_context"}
)
_TERMINAL_KEY = "terminal_filter"
# Every feature family `meta_learner.families` may name (F7 fits one sub-model per family).
KNOWN_FAMILIES: tuple[str, ...] = tuple(family.value for family in FeatureFamily)
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
    # The last filter whose recommendation is the chain's decision when no F7 is listed
    # (`chain/terminal.py` LastFilterTerminalDecision); None whenever F7 closes the chain.
    terminal_filter: str | None = None
    perception: PerceptionConfig = PerceptionConfig()
    price_features: PriceFeatureConfig = PriceFeatureConfig()
    # Fill costs and holding rule (story 12): always resolved, tied to no filter.
    execution: ExecutionConfig = ExecutionConfig()
    indicator: IndicatorConfig | None = None
    pattern: PatternConfig | None = None
    news_context: NewsContextConfig | None = None
    risk_guard: RiskGuardCaps | None = None
    capital_mgmt: CapitalMgmtConfig | None = None
    f7: F7Config | None = None
    volume_strength: VolumeConfig | None = None
    # dotted parameter path -> the `<name>/config.yaml` in the extends chain that set it,
    # or "default" for a value the loader filled in. Informational: excluded from equality.
    provenance: Mapping[str, str] = field(default_factory=dict, compare=False)


def strategies_root() -> Path:
    """The bundled `strategies/` directory, alongside `algos/` (same reliable
    `Path(__file__).parent`-relative pattern `run.py` already uses to locate `algos/`,
    so both survive being run from any working directory or packaging layout)."""
    return Path(__file__).parent / "strategies"


def _config_path(root: Path, name: str) -> Path:
    return root / name / "config.yaml"


def strategy_exists(name: str, *, root: Path | None = None) -> bool:
    """Whether `name` has a `config.yaml` in `root` (when given) or the bundled directory."""
    return (root is not None and _config_path(root, name).is_file()) or _config_path(
        strategies_root(), name
    ).is_file()


def _read_yaml(root: Path, name: str) -> dict[str, Any]:
    """Read and parse one strategy's `config.yaml`, failing fast if it's missing/malformed."""
    path = _config_path(root, name)
    if not path.is_file():
        raise ValueError(
            f"unknown strategy {name!r}: no config at {path} — create "
            f"strategies/{name}/config.yaml first"
        )
    return _read_mapping(path)


def _read_mapping(path: Path) -> dict[str, Any]:
    """Parse a YAML file that must hold a mapping."""
    parsed = yaml.safe_load(path.read_text())
    if not isinstance(parsed, dict):
        raise ValueError(f"strategy config {path} must contain a YAML mapping")
    return parsed


def _read_base(root: Path, base_name: str) -> dict[str, Any]:
    """A base strategy's config: from `root` when it has one, else from the bundled
    directory — so a variant in an external `--strategies-dir` can extend `baseline`."""
    if _config_path(root, base_name).is_file():
        return _read_yaml(root, base_name)
    return _read_yaml(strategies_root(), base_name)


def resolved_yaml(config: StrategyChainConfig) -> str:
    """The fully resolved configuration as one self-contained YAML document (no `extends`),
    the form shipped into the LEAN container and written to each run's artifacts."""
    return yaml.safe_dump(dict(config.raw), sort_keys=True)


def load_resolved_strategy(path: Path, *, name: str) -> StrategyChainConfig:
    """Load a resolved YAML document (`resolved_yaml`'s output) under `name`.

    Raises:
        ValueError: the document still declares `extends` (it is not resolved), or any
            of `load_strategy_chain_config`'s validation failures.
    """
    merged = _read_mapping(path)
    if "extends" in merged:
        raise ValueError(
            f"strategy {name!r}: resolved document {path} still declares 'extends' — resolve "
            "it with load_strategy_chain_config and dump it with resolved_yaml first"
        )
    return _from_merged(name, merged, None, dict.fromkeys(_leaf_paths(merged), path.name))


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
    if listed and present:
        return _mapping_section(name, merged, section)
    if listed:
        return _omitted_section(name, filter_name, section)
    if present:
        raise ValueError(
            f"strategy {name!r} declares a '{section}:' section but does not list "
            f"{filter_name!r} in filters — remove the section or add the filter"
        )
    return None


def _omitted_section(name: str, filter_name: str, section: str) -> dict[str, Any]:
    """`{}` (every key defaults) for a listed filter whose section may be omitted; a hard
    stop for a trading-impactful filter, whose parameters must be spelled out.

    Raises:
        ValueError: `filter_name` is not one of the defaultable filters.
    """
    if filter_name in _DEFAULTABLE_FILTERS:
        return {}
    raise ValueError(
        f"strategy {name!r} lists {filter_name!r} but has no '{section}:' section — add "
        f"the filter's parameters to strategies/{name}/config.yaml"
    )


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


def _require_known_families(name: str, families: tuple[str, ...]) -> None:
    """Fail fast on a feature family F7 cannot fit (a typo would otherwise surface only
    when a trainer or a run coerces the name into `FeatureFamily`).

    Raises:
        ValueError: naming the unknown entries and the known families.
    """
    unknown = [family for family in families if family not in KNOWN_FAMILIES]
    if unknown:
        raise ValueError(
            f"strategy {name!r}: unknown meta_learner.families {unknown!r} — known families: "
            f"{list(KNOWN_FAMILIES)}; use only those in its config.yaml"
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


def _mapping_section(name: str, merged: Mapping[str, Any], section: str) -> dict[str, Any]:
    """`merged[section]` as a mapping: `{}` when the section is absent (so every key
    defaults — the `price_features`/`execution` case); anything present must be a mapping.

    Raises:
        ValueError: the section is present but not a mapping.
    """
    raw = merged.get(section, {})
    if not isinstance(raw, dict):
        raise ValueError(
            f"strategy {name!r}: '{section}' must be a mapping (got "
            f"{type(raw).__name__!r}) — check its config.yaml"
        )
    return raw


def _always_resolved_sections(name: str, merged: dict[str, Any]) -> dict[str, Any]:
    """`price_features` and `execution`: parsed with defaults for every omitted key and
    their effective values written back into `merged` (story 09 / story 12)."""
    price = parse_price_features_config(
        _mapping_section(name, merged, "price_features"), strategy=name
    )
    merged["price_features"] = price_features_mapping(price)
    execution = parse_execution_config(
        _mapping_section(name, merged, "execution"), strategy=name
    )
    merged["execution"] = execution_mapping(execution)
    return {"price_features": price, "execution": execution}


def _defaulted_sections(
    name: str, merged: dict[str, Any], filters: tuple[str, ...], meta_learner: dict[str, Any]
) -> dict[str, Any]:
    """The sections with defaults (price_features, execution, indicator, pattern, F7's
    horizon): parsed, and their *effective* values written back into `merged` so the run's
    `strategy-config.{json,yaml}` records what was actually used, defaults included."""
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
    return {
        **_always_resolved_sections(name, merged),
        "indicator": indicator, "pattern": pattern, "f7": f7,
    }


def _capital_mgmt(
    name: str, merged: dict[str, Any], filters: tuple[str, ...]
) -> CapitalMgmtConfig | None:
    """F6's section when the filter is listed; the trade-plan keys it omits default and the
    effective values are written back into `merged` (story 12)."""
    capital = _filter_section(name, merged, filters, "f6_capital_mgmt")
    if capital is None:
        return None
    config = parse_capital_mgmt_config(capital, strategy=name)
    merged["capital_mgmt"] = capital_mgmt_mapping(config)
    return config


def _typed_sections(
    name: str, merged: dict[str, Any], filters: tuple[str, ...], meta_learner: dict[str, Any]
) -> dict[str, Any]:
    """Every listed configurable filter's section, parsed by that filter's own parser."""
    _reject_stray_f7_keys(name, filters, meta_learner)
    risk = _filter_section(name, merged, filters, "f5_risk_guard")
    return {
        "news_context": _news_context(name, merged, filters),
        "risk_guard": parse_risk_guard_caps(risk, strategy=name) if risk is not None else None,
        "capital_mgmt": _capital_mgmt(name, merged, filters),
        "volume_strength": _volume_section(name, merged, filters),
        **_defaulted_sections(name, merged, filters, meta_learner),
    }


def _news_context(
    name: str, merged: dict[str, Any], filters: tuple[str, ...]
) -> NewsContextConfig | None:
    """F4's section when the filter is listed; the direction-source keys it omits default
    and the effective values are written back into `merged` (story 14)."""
    news = _filter_section(name, merged, filters, "f4_news_context")
    if news is None:
        return None
    config = parse_news_context_config(news, strategy=name)
    merged["news_context"] = news_context_mapping(config)
    return config


def _terminal_filter(name: str, merged: Mapping[str, Any], filters: tuple[str, ...]) -> str | None:
    """The `terminal_filter` a chain without F7 must declare (and one with F7 must not).

    The named filter's recommendation is the chain's decision, so it must be the last
    *direction-emitting* filter: gates (F5/F6/volume) may follow it and veto, but another
    direction filter after it would have its opinion silently ignored.

    Raises:
        ValueError: F7 is absent and the key is missing; F7 is present alongside the key;
            the key is not a string, not listed, names a filter that emits no direction,
            or is followed by another direction-emitting filter.
    """
    terminal = merged.get(_TERMINAL_KEY)
    if "f7_meta_learner" in filters:
        if terminal is not None:
            raise ValueError(
                f"strategy {name!r}: '{_TERMINAL_KEY}' is declared but f7_meta_learner is listed "
                "— F7 is the terminal rule; remove the key or drop f7_meta_learner"
            )
        return None
    if terminal is None:
        raise ValueError(
            f"strategy {name!r}: filters list no f7_meta_learner, so the chain needs a "
            f"'{_TERMINAL_KEY}' key naming the last filter whose recommendation is the "
            f"decision — add '{_TERMINAL_KEY}: {filters[-1]}' or list f7_meta_learner"
        )
    if not isinstance(terminal, str):
        raise ValueError(
            f"strategy {name!r}: '{_TERMINAL_KEY}' must be a filter name, got {terminal!r}"
        )
    if terminal not in filters:
        raise ValueError(
            f"strategy {name!r}: {_TERMINAL_KEY} {terminal!r} is not in filters {list(filters)} "
            f"— name one of the listed filters"
        )
    if terminal not in DIRECTION_FILTERS:
        raise ValueError(
            f"strategy {name!r}: {_TERMINAL_KEY} {terminal!r} emits no direction — choose one of "
            f"{sorted(DIRECTION_FILTERS)}"
        )
    later = [f for f in filters[filters.index(terminal) + 1 :] if f in DIRECTION_FILTERS]
    if later:
        raise ValueError(
            f"strategy {name!r}: {_TERMINAL_KEY} {terminal!r} is followed by direction filters "
            f"{later!r} whose recommendation would be ignored — the terminal filter must be the "
            f"last direction-emitting entry of filters; reorder filters or change {_TERMINAL_KEY}"
        )
    return terminal


def _volume_section(
    name: str, merged: dict[str, Any], filters: tuple[str, ...]
) -> VolumeConfig | None:
    """Resolve every volume parameter so reports never omit default threshold values."""
    raw = _filter_section(name, merged, filters, "volume_strength")
    if raw is None:
        return None
    config = parse_volume_config(raw, strategy=name)
    merged["volume_strength"] = asdict(config)
    return config


def load_strategy_chain_config(name: str, *, root: Path | None = None) -> StrategyChainConfig:
    """Resolve one strategy's chain config, composing a single `extends:` level if present.

    Raises:
        ValueError: the strategy (or an ancestor) has no `config.yaml`, the `extends:`
            chain revisits a name (a cycle), `filters:` resolves
            empty (a chain with no filters can never reach a terminal decision), a
            filter name is unknown, `schema_version` is not the current integer,
            `meta_learner:` is present but not a mapping (a malformed config type,
            distinct from the section being absent entirely — that legitimately
            resolves to no feature families), a family name F7 does not know, or a
            configurable filter's own section is missing, stray or invalid
            (`_filter_section` and each `parse_*_config`), or the `terminal_filter`
            contract is broken (`_terminal_filter`: required without F7, refused with
            it, must be the last direction-emitting filter listed).
    """
    resolved_root = root if root is not None else strategies_root()
    chain = _extends_chain(resolved_root, name)
    merged: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for document_name, document in reversed(chain):
        own = {k: v for k, v in document.items() if k != "extends"}
        dropped = [key for key, value in own.items() if value is None]
        merged = _deep_merge(merged, {k: v for k, v in own.items() if k not in dropped})
        provenance.update(dict.fromkeys(_leaf_paths(own), f"{document_name}/config.yaml"))
        for key in dropped:
            _drop_section(merged, provenance, key)
    base_name = chain[0][1].get("extends")
    return _from_merged(name, merged, base_name, provenance)


def _drop_section(merged: dict[str, Any], provenance: dict[str, str], key: str) -> None:
    """Remove an inherited top-level section a child set to ``null``, and its provenance."""
    merged.pop(key, None)
    for path in [p for p in provenance if p == key or p.startswith(f"{key}.")]:
        del provenance[path]


def _extends_chain(root: Path, name: str) -> list[tuple[str, dict[str, Any]]]:
    """`(name, document)` for the strategy and each ancestor, leaf first, cycle-checked.

    Raises:
        ValueError: an `extends:` that is not a string, or a chain that revisits a name.
    """
    chain: list[tuple[str, dict[str, Any]]] = []
    visited: list[str] = []
    current = name
    document = _read_yaml(root, current)
    while True:
        visited.append(current)
        chain.append((current, document))
        base = document.get("extends")
        if base is None:
            return chain
        if not isinstance(base, str):
            raise ValueError(
                f"strategy {current!r}: 'extends' must be a strategy name, got {base!r}"
            )
        if base in visited:
            raise ValueError(
                f"strategy {name!r}: extends cycle {' -> '.join([*visited, base])} — a "
                "strategy cannot (transitively) extend itself; check the config.yaml files"
            )
        current, document = base, _read_base(root, base)


def _leaf_paths(document: Mapping[str, Any], prefix: str = "") -> Iterator[str]:
    """Dotted paths of every parameter in `document`; a list counts as one parameter."""
    for key, value in document.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            yield from _leaf_paths(value, f"{path}.")
        else:
            yield path


def explain_lines(config: StrategyChainConfig) -> list[str]:
    """`key = value  # source` for every resolved parameter, sorted by key."""
    flat = {path: _value_at(config.raw, path) for path in _leaf_paths(config.raw)}
    return [
        f"{path} = {json.dumps(flat[path])}  # {config.provenance.get(path, 'unknown')}"
        for path in sorted(flat)
    ]


def _value_at(document: Mapping[str, Any], path: str) -> Any:
    """The value a dotted path names inside a nested mapping."""
    value: Any = document
    for part in path.split("."):
        value = value[part]
    return value


def _from_merged(
    name: str, merged: dict[str, Any], base_name: str | None, provenance: dict[str, str]
) -> StrategyChainConfig:
    """Validate and type one fully merged configuration mapping; parameters the loader
    fills in (defaulted sections) are attributed to "default" in `provenance`."""
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
    _require_known_families(name, families)
    typed = _typed_sections(name, merged, filters, meta_learner)
    _validate_clock(typed, parse_perception_config(merged))
    terminal = _terminal_filter(name, merged, filters)
    for path in _leaf_paths(merged):
        provenance.setdefault(path, "default")
    return StrategyChainConfig(
        name=name, filters=filters, meta_learner_families=families, extends=base_name, raw=merged,
        terminal_filter=terminal, perception=parse_perception_config(merged),
        provenance=provenance, **typed,
    )


def _validate_clock(typed: Mapping[str, Any], perception: PerceptionConfig) -> None:
    """Reject unsupported minute contracts before launching a model or the engine."""
    minutes = typed["price_features"].bar_minutes
    if minutes != 1 and perception.source != "ema":
        raise ValueError("multi-minute decision bars require EMA perception; use M1 for DSHA")
    f7 = typed["f7"]
    if f7 is not None and f7.label_horizon_minutes % minutes:
        raise ValueError("label_horizon_minutes must be a multiple of bar_minutes; fix config")
