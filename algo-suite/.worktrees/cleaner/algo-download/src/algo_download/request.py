"""The ``DownloadRequest`` value object: what to fetch, for one source run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class DownloadRequest(BaseModel):
    """Symbol plus optional year-month partitions for one source run.

    Per-instrument sources require ``symbol`` and month partitions. Global
    month-partitioned sources and whole-window sources leave ``symbol`` empty.
    Source-specific CLI validation decides which shape is applicable.
    """

    model_config = ConfigDict(frozen=True)

    symbol: str = ""
    months: tuple[tuple[int, int], ...] = ()

    @field_validator("months")
    @classmethod
    def _months_in_range(
        cls, months: tuple[tuple[int, int], ...]
    ) -> tuple[tuple[int, int], ...]:
        """Reject an impossible month (1-12) so it fails here, not deep in a calendar call."""
        for _year, month in months:
            if not 1 <= month <= 12:
                raise ValueError(f"month must be 1-12, got {month}")
        return months
