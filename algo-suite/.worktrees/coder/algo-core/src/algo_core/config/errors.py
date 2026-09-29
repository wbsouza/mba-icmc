"""Configuration errors, each carrying the process exit code the CLI returns."""

from __future__ import annotations

from algo_core.config.schema import ParameterSpec


class ConfigError(Exception):
    """Base for configuration failures; ``exit_code`` is the CLI's return code."""

    exit_code: int = 2


class MissingTradingParameter(ConfigError):
    """A trading-impactful parameter was absent (an oversight), so loading stops."""

    exit_code: int = 2

    def __init__(self, spec: ParameterSpec) -> None:
        """Name the missing parameter, its section, the reference value and the fix."""
        super().__init__(
            f"missing trading-impactful parameter '{spec.leaf}' in section "
            f"'{spec.section}' (reference value: {spec.reference_value!r}); "
            f"run the config_generator to scaffold it"
        )


class InvalidNullParameter(ConfigError):
    """A non-nullable parameter was set to null, which is not permitted."""

    exit_code: int = 2

    def __init__(self, spec: ParameterSpec) -> None:
        """Name the parameter that may not be null."""
        super().__init__(
            f"parameter '{spec.leaf}' in section '{spec.section}' cannot be null"
        )


class SchemaVersionMismatch(ConfigError):
    """The config's schema_version does not match the current one."""

    exit_code: int = 3

    def __init__(self, found: int, current: int) -> None:
        """Report the version gap and point at the --upgrade migration path."""
        super().__init__(
            f"config schema_version {found} does not match current {current}; "
            f"run with --upgrade to migrate"
        )


class UnknownParameter(ConfigError):
    """The config holds keys absent from the schema (typo, stale, half-migrated)."""

    exit_code: int = 2

    def __init__(self, keys: list[str]) -> None:
        """List the offending keys and how to resolve them."""
        super().__init__(
            f"unknown config parameter(s): {', '.join(keys)}; "
            f"remove them or add them to the schema"
        )


class MissingSchemaVersion(ConfigError):
    """The config did not declare a schema_version (required; no silent default)."""

    exit_code: int = 3

    def __init__(self) -> None:
        """State that schema_version is mandatory."""
        super().__init__(
            "config is missing the required 'schema_version'; "
            "add it or run with --upgrade"
        )
