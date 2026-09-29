"""Outcome of transforming one month."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class TransformStatus(StrEnum):
    """What happened to one month's transform."""

    WRITTEN = "written"        # decoded + resampled + Parquet written
    SKIPPED = "skipped"        # canonical Parquet already present (idempotent)
    MISSING = "missing"        # whole-window raw input is absent
    INCOMPLETE = "incomplete"  # raw month not fully downloaded yet; nothing written
    CORRUPT = "corrupt"        # a raw hour failed to decode; nothing written (no truncation)


class TransformReport(BaseModel):
    """Per-month transform result."""

    # extra="forbid": an orchestrator passing an undeclared count kwarg (e.g. `articles=`
    # before this field existed) must raise, not silently drop the count (fail-fast, CLAUDE.md).
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    year: int
    month: int
    status: TransformStatus
    ticks: int = 0
    bars: int = 0
    events: int = 0
    articles: int = 0
    quarantined: int = 0
    paths: tuple[str, ...] = ()

    @property
    def exit_code(self) -> int:
        """Non-zero when nothing was produced from a problem input (INCOMPLETE/CORRUPT)."""
        return (
            1
            if self.status
            in (TransformStatus.MISSING, TransformStatus.INCOMPLETE, TransformStatus.CORRUPT)
            else 0
        )

    def render(self) -> str:
        """One-line human summary."""
        paths = f" paths={','.join(self.paths)}" if self.paths else ""
        return (
            f"{self.symbol} {self.year:04d}-{self.month:02d}: {self.status.value} "
            f"(ticks={self.ticks} bars={self.bars} events={self.events} "
            f"articles={self.articles} quarantined={self.quarantined}{paths})"
        )
