"""Layered config resolution: merge conf files + environment, then validate.

This is the read+merge layer that `paths.py` deferred. It assembles the raw config
from (lowest to highest precedence) schema defaults < ``conf/algo.yaml`` <
``conf/<tool>.yaml`` < ``ALGO_*`` environment, then hands it to the loader policy
(``load``, SPEC.md §8) which applies defaults, enforces trading-impactful params and
records provenance.

Zero-config is first-class: with no config files present the run assumes the current
``schema_version`` (there is nothing to be stale). A config file that *is* present
must still declare ``schema_version`` — the loader rejects one that does not.

Infrastructure env vars resolved elsewhere (``ALGO_CONF_DIR`` by ``paths``,
``ALGO_DATA_ROOT`` by ``layout``) are **not** treated as schema overrides.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from algo_core import layout
from algo_core.config.loader import LoadResult, load
from algo_core.config.paths import (
    ENV_CONF_DIR,
    global_config_path,
    tool_config_path,
)
from algo_core.config.schema import ParameterSpec

_ENV_PREFIX = "ALGO_"
_ENV_NESTED_SEP = "__"
_SCHEMA_VERSION_KEY = "schema_version"
# ALGO_ vars owned by other resolvers, never mapped onto schema parameters.
_INFRA_ENV = frozenset({ENV_CONF_DIR, layout.ENV_DATA_ROOT})


def resolve(
    tool: str, schema: Sequence[ParameterSpec], current_version: int
) -> LoadResult:
    """Resolve a tool's effective config from files + environment, then validate.

    Precedence (highest first): ``ALGO_*`` environment > ``conf/<tool>.yaml`` >
    ``conf/algo.yaml`` > schema defaults. Returns the validated values + provenance,
    or raises a ``ConfigError`` (schema-version mismatch, missing trading param,
    illegal null, unknown key).

    Args:
        tool: short tool name without the ``algo-`` prefix (e.g. ``backtest``).
        schema: the parameters to enforce.
        current_version: the schema version this code expects.
    """
    global_raw = _read_yaml(global_config_path())
    tool_raw = _read_yaml(tool_config_path(tool))
    env_raw = _env_overrides(os.environ)
    files_present = global_raw is not None or tool_raw is not None

    merged: dict[str, Any] = {}
    for layer in (global_raw, tool_raw, env_raw):
        if layer:
            _deep_merge(merged, layer)
    if not files_present and _SCHEMA_VERSION_KEY not in merged:
        merged[_SCHEMA_VERSION_KEY] = current_version

    return load(merged, schema, current_version)


def _read_yaml(path: Path) -> dict[str, Any] | None:
    """Parse a YAML config file to a dict, or None if it does not exist.

    Raises:
        ValueError: if the file exists but is not a YAML mapping (fail fast).
    """
    if not path.is_file():
        return None
    parsed = yaml.safe_load(path.read_text()) or {}
    if not isinstance(parsed, dict):
        raise ValueError(
            f"config file {path} must contain a YAML mapping, got {type(parsed).__name__}"
        )
    return parsed


def _env_overrides(env: Mapping[str, str]) -> dict[str, Any]:
    """Build a nested override dict from ``ALGO_*`` env vars (``__`` delimits nesting).

    ``ALGO_MARKETS__OANDA__DATA_TZ=...`` becomes ``{markets: {oanda: {data_tz: ...}}}``.
    Infrastructure vars (``ALGO_CONF_DIR``, ``ALGO_DATA_ROOT``) are skipped.
    """
    out: dict[str, Any] = {}
    for key, value in env.items():
        if not key.startswith(_ENV_PREFIX) or key in _INFRA_ENV:
            continue
        path = key[len(_ENV_PREFIX) :].lower().split(_ENV_NESTED_SEP)
        _set_nested(out, path, value)
    return out


def _set_nested(root: dict[str, Any], path: Sequence[str], value: Any) -> None:
    """Set ``value`` at a nested key ``path``, creating intermediate dicts."""
    node = root
    for part in path[:-1]:
        child = node.setdefault(part, {})
        if not isinstance(child, dict):  # an env scalar shadowed by a deeper key
            child = node[part] = {}
        node = child
    node[path[-1]] = value


def _deep_merge(base: dict[str, Any], over: Mapping[str, Any]) -> None:
    """Recursively merge ``over`` into ``base`` in place (``over`` wins on conflict)."""
    for key, value in over.items():
        existing = base.get(key)
        if isinstance(existing, dict) and isinstance(value, Mapping):
            _deep_merge(existing, value)
        else:
            base[key] = value
