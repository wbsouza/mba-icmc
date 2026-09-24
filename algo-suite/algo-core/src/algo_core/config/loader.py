"""The schema-driven config loader: the hybrid policy of SPEC.md §8.

Each parameter is resolved against the schema and a provenance line is recorded,
so a strategy's effective configuration is fully traceable. ``extends:``
inheritance is post-TCC and intentionally not implemented here.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict

from algo_core.config.errors import (
    InvalidNullParameter,
    MissingSchemaVersion,
    MissingTradingParameter,
    SchemaVersionMismatch,
    UnknownParameter,
)
from algo_core.config.schema import Impact, ParameterSpec

_ABSENT = object()
_SCHEMA_VERSION_KEY = "schema_version"


class LoadResult(BaseModel):
    """A validated configuration: resolved values plus their provenance log."""

    model_config = ConfigDict(frozen=True)

    values: dict[str, Any]
    provenance: tuple[str, ...]


def load(
    raw: dict[str, Any], schema: Sequence[ParameterSpec], current_version: int
) -> LoadResult:
    """Validate ``raw`` against ``schema`` under the hybrid policy, or raise.

    Args:
        raw: the parsed config as a nested dict (e.g. from YAML), keyed by section.
        schema: the parameters to enforce; any key in ``raw`` not in the schema is
            ignored (the schema is the source of truth for what matters).
        current_version: the schema version this code expects; a different
            ``schema_version`` in ``raw`` is a hard stop.

    Raises:
        ConfigError: with its ``exit_code`` set, on a schema-version mismatch, a
            missing trading-impactful parameter, or an illegal null.
    """
    _check_version(raw, current_version)
    _reject_unknown(raw, schema)
    values: dict[str, Any] = {}
    provenance: list[str] = []
    for spec in schema:
        value, line = _resolve(spec, raw)
        values[spec.name] = value
        provenance.append(line)
    return LoadResult(values=values, provenance=tuple(provenance))


def _reject_unknown(raw: dict[str, Any], schema: Sequence[ParameterSpec]) -> None:
    """Hard-stop if the config has keys the schema does not declare (fail fast)."""
    known = {spec.name for spec in schema} | {_SCHEMA_VERSION_KEY}
    unknown = _flatten_keys(raw) - known
    if unknown:
        raise UnknownParameter(sorted(unknown))


def _flatten_keys(node: dict[str, Any], prefix: str = "") -> set[str]:
    """Return the dotted leaf paths of a nested config dict."""
    keys: set[str] = set()
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys |= _flatten_keys(value, path)
        else:
            keys.add(path)
    return keys


def _check_version(raw: dict[str, Any], current_version: int) -> None:
    """Hard-stop if schema_version is missing or differs from the current one.

    A missing version is rejected (not silently defaulted): we cannot assume
    compatibility, so fail fast.
    """
    found = raw.get(_SCHEMA_VERSION_KEY)
    if found is None:
        raise MissingSchemaVersion()
    if found != current_version:
        raise SchemaVersionMismatch(found, current_version)


def _resolve(spec: ParameterSpec, raw: dict[str, Any]) -> tuple[object, str]:
    """Resolve one parameter to its value and a provenance line (or raise)."""
    value = _lookup(raw, spec.name)
    if value is _ABSENT:
        return _resolve_absent(spec)
    if value is None:
        return _resolve_null(spec)
    return value, f"FROM CONFIG: {spec.leaf}={value!r}"


def _resolve_absent(spec: ParameterSpec) -> tuple[object, str]:
    """Apply the absent-parameter policy: default for operational, else hard-stop."""
    if spec.impact is Impact.OPERATIONAL:
        return spec.default, f"USING DEFAULT: {spec.leaf}={spec.default}"
    raise MissingTradingParameter(spec)


def _resolve_null(spec: ParameterSpec) -> tuple[object, str]:
    """Apply the explicit-null policy: disable a nullable param, else reject."""
    if spec.nullable:
        return None, f"EXPLICITLY DISABLED: {spec.leaf}"
    raise InvalidNullParameter(spec)


def _lookup(raw: dict[str, Any], dotted: str) -> object:
    """Return the value at a dotted path, or the ``_ABSENT`` sentinel if missing."""
    node: Any = raw
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return _ABSENT
        node = node[part]
    return node
