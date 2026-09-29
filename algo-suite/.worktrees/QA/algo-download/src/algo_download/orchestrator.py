"""The synchronous download orchestrator: plan → skip-done → fetch → aggregate.

Source-agnostic by construction — it speaks only the ``DataSource`` port. A
FAILED unit is logged and the run continues (other units still fetched); the
non-zero exit is carried in the report, never raised mid-run. See ../../SPEC.md §3.
"""

from __future__ import annotations

from pathlib import Path

from algo_core.logging import get_logger

from algo_download.request import DownloadRequest
from algo_download.result import RunReport, UnitResult, UnitStatus
from algo_download.source import DataSource

_log = get_logger(__name__)


def run(source: DataSource, request: DownloadRequest) -> RunReport:
    """Process every planned unit once and return the aggregate report.

    A unit that fails (returned FAILED, or an unexpected exception from the
    adapter) is logged and recorded as FAILED; the run continues so one bad unit
    never aborts a long bulk download. The non-zero exit is carried in the report.
    """
    results: list[UnitResult] = []
    last_group: Path | None = None
    for unit in source.plan(request):
        if source.is_done(unit):
            results.append(UnitResult(unit=unit, status=UnitStatus.SKIPPED))
            continue
        # Live progress, one line per day (the unit's containing directory) actually
        # fetched — not per hour, which is too noisy. Already-present units skip silently,
        # so a resume stays quiet until it reaches new work.
        group = unit.raw_path.parent
        if group != last_group:
            _log.info("downloading", source=source.name, unit=unit.key)
            last_group = group
        try:
            result = source.fetch(unit)
        except Exception as exc:
            # Boundary: contain any unexpected adapter error as FAILED (logged loudly),
            # so the run completes and signals failure via the exit code.
            _log.warning("unit_error", source=source.name, unit=unit.key, error=repr(exc))
            result = UnitResult(unit=unit, status=UnitStatus.FAILED)
        else:
            if result.status is UnitStatus.FAILED:
                _log.warning("unit_failed", source=source.name, unit=unit.key)
        results.append(result)
    return RunReport(results=tuple(results))
