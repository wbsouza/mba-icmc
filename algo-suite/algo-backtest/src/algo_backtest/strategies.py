"""Strategy-chain config loading (Spec 04h): `src/algo_backtest/strategies/<name>/
config.yaml`, bundled alongside `algos/` (same `Path(__file__).parent`-relative,
packaging-independent pattern `run.py` already uses for `algos/`).

Config, not code, decides which filters a strategy runs and in what order (specs.md
§11.3.1: "Adding, removing or reordering a filter requires editing config.yaml, not the
engine code"). `baseline` and `hybrid` are the two Spec 04 variants
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


@dataclass(frozen=True)
class StrategyChainConfig:
    """One strategy's resolved filter chain + meta-learner feature families.

    ``raw`` is the fully-merged config dict (post-`extends:` composition) — every key,
    not just the two this module interprets — so a future filter (e.g. F5/F6's own
    per-strategy threshold overrides) can read its own section without this module
    needing to know its schema in advance.
    """

    name: str
    filters: tuple[str, ...]
    meta_learner_families: tuple[str, ...]
    extends: str | None
    raw: Mapping[str, Any]


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


def load_strategy_chain_config(name: str, *, root: Path | None = None) -> StrategyChainConfig:
    """Resolve one strategy's chain config, composing a single `extends:` level if present.

    Raises:
        ValueError: the strategy (or its base) has no `config.yaml`, the base itself
            declares `extends:` (only one level is supported), `filters:` resolves
            empty (a chain with no filters can never reach a terminal decision), or
            `meta_learner:` is present but not a mapping (a malformed config type,
            distinct from the section being absent entirely — that legitimately
            resolves to no feature families).
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
        name=name, filters=filters, meta_learner_families=families, extends=base_name, raw=merged
    )
