"""Coverage matrix rows and training-window selection."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

_MIN_COVERAGE = 0.8


class CoverageInput(BaseModel):
    """Raw counts for one source/month."""

    model_config = ConfigDict(frozen=True)

    month: date
    source: str
    resolution: str
    units_expected: int = Field(gt=0)
    units_present: int = Field(ge=0)


class CoverageRow(BaseModel):
    """Canonical monthly coverage matrix row."""

    model_config = ConfigDict(frozen=True)

    month: date
    source: str
    units_expected: int
    units_present: int
    coverage_ratio: float
    resolution: str
    backtestable: bool


class TrainingWindow(BaseModel):
    """The selected contiguous training window."""

    model_config = ConfigDict(frozen=True)

    start: date
    end: date

    def render(self) -> str:
        """Render as YYYY-MM to YYYY-MM."""
        return f"{self.start:%Y-%m} to {self.end:%Y-%m}"


class _WindowCandidate(BaseModel):
    """Contiguous coverage span considered for training."""

    model_config = ConfigDict(frozen=True)

    start: date
    end: date

    @property
    def length(self) -> int:
        """Inclusive span length in months."""
        return (self.end.year - self.start.year) * 12 + self.end.month - self.start.month + 1


def compute_matrix(inputs: list[CoverageInput]) -> list[CoverageRow]:
    """Compute ratios and backtestable flags from expected/present counts."""
    return [_to_row(item) for item in inputs]


def select_training_window(rows: list[CoverageRow]) -> TrainingWindow | None:
    """Select the largest contiguous GDELT span at or above 80% coverage.

    Ties prefer the later span, by comparing candidate starts after length.
    """
    best: _WindowCandidate | None = None
    current: _WindowCandidate | None = None
    for month in _eligible_gdelt_months(rows):
        current = _extend_or_restart(current, month)
        best = _better_window(best, current)
    if best is None:
        return None
    return TrainingWindow(start=best.start, end=best.end)


def _to_row(item: CoverageInput) -> CoverageRow:
    """Convert counts into the canonical coverage schema."""
    ratio = item.units_present / item.units_expected
    return CoverageRow(
        month=item.month,
        source=item.source,
        units_expected=item.units_expected,
        units_present=item.units_present,
        coverage_ratio=ratio,
        resolution=item.resolution,
        backtestable=item.source != "yfinance" and ratio >= _MIN_COVERAGE,
    )


def _eligible_gdelt_months(rows: list[CoverageRow]) -> list[date]:
    """Return sorted GDELT months whose coverage clears the training threshold."""
    return sorted(
        row.month
        for row in rows
        if row.source == "gdelt" and row.coverage_ratio >= _MIN_COVERAGE
    )


def _extend_or_restart(current: _WindowCandidate | None, month: date) -> _WindowCandidate:
    """Extend a contiguous candidate or start a new one at ``month``."""
    if current is not None and month == _next_month(current.end):
        return _WindowCandidate(start=current.start, end=month)
    return _WindowCandidate(start=month, end=month)


def _better_window(
    best: _WindowCandidate | None, candidate: _WindowCandidate
) -> _WindowCandidate:
    """Prefer longer windows, then later starts for deterministic ties."""
    if best is None:
        return candidate
    if candidate.length > best.length:
        return candidate
    if candidate.length == best.length and candidate.start > best.start:
        return candidate
    return best


def _next_month(month: date) -> date:
    """Return the first day of the next month."""
    return date(month.year + 1, 1, 1) if month.month == 12 else date(month.year, month.month + 1, 1)
