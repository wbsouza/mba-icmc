"""algo-analyze configuration: resolve the tool's effective settings, typed.

Thin wrapper over the shared `algo_core.config.resolve` (env > conf/analyze.yaml >
conf/algo.yaml > defaults), mirroring algo-backtest so analyze isn't the one tool with a
different config story. It has no tool-specific parameters yet (the schema is empty); the
only thing it needs is the data root, resolved through the shared convention
(`ALGO_DATA_ROOT` > convention), with provenance logged at the CLI boundary.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from algo_core import layout
from algo_core.config import ParameterSpec, resolve
from algo_core.layout import ENV_DATA_ROOT

SCHEMA: tuple[ParameterSpec, ...] = ()
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class AnalyzeConfig:
    """The resolved, typed algo-analyze configuration plus its provenance log."""

    data_root: Path
    provenance: tuple[str, ...]


def load_analyze_config() -> AnalyzeConfig:
    """Resolve the algo-analyze config (data root via the shared convention).

    Raises:
        ConfigError: from the loader (schema-version mismatch / unknown key / etc.).
    """
    result = resolve("analyze", SCHEMA, SCHEMA_VERSION)
    data_root = layout.data_root()
    source = ENV_DATA_ROOT if os.environ.get(ENV_DATA_ROOT) else "convention"
    provenance = (*result.provenance, f"DATA ROOT: data_root={data_root} (from {source})")
    return AnalyzeConfig(data_root=data_root, provenance=provenance)
