"""Parameter schema: the single source of truth for the config-loading policy."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Impact(StrEnum):
    """Whether a parameter is trading-impactful (must be set) or operational."""

    TRADING = "trading"
    OPERATIONAL = "operational"


class ParameterSpec(BaseModel):
    """Declares one config parameter and how the loader must treat it."""

    model_config = ConfigDict(frozen=True)

    name: str
    impact: Impact
    default: object | None = None
    nullable: bool = False
    reference_value: object | None = None

    @property
    def section(self) -> str:
        """Return the parameter's top-level section (the part before the first dot)."""
        return self.name.split(".", 1)[0]

    @property
    def leaf(self) -> str:
        """Return the parameter's leaf name (the part after the last dot)."""
        return self.name.rsplit(".", 1)[-1]
