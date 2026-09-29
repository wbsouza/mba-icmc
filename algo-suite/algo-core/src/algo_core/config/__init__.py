"""Configuration: convention-based path resolution + the schema-driven loader.

`paths` resolves where config lives (conf/ + env). The loader applies the policy
that is a methodology contribution of this work: missing trading-impactful params
hard-stop, missing operational params fall back to a logged default, explicit
`null` disables a nullable param, and a schema-version mismatch refuses to load
(SPEC.md §8).
"""

from algo_core.config.errors import (
    ConfigError,
    InvalidNullParameter,
    MissingSchemaVersion,
    MissingTradingParameter,
    SchemaVersionMismatch,
    UnknownParameter,
)
from algo_core.config.loader import LoadResult, load
from algo_core.config.paths import (
    ENV_CONF_DIR,
    GLOBAL_CONFIG_NAME,
    conf_dir,
    global_config_path,
    tool_config_path,
)
from algo_core.config.resolution import resolve
from algo_core.config.schema import Impact, ParameterSpec

__all__ = [
    "ENV_CONF_DIR",
    "GLOBAL_CONFIG_NAME",
    "ConfigError",
    "Impact",
    "InvalidNullParameter",
    "LoadResult",
    "MissingSchemaVersion",
    "MissingTradingParameter",
    "ParameterSpec",
    "SchemaVersionMismatch",
    "UnknownParameter",
    "conf_dir",
    "global_config_path",
    "load",
    "resolve",
    "tool_config_path",
]
