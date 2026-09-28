"""Steps for confluence_horizon_units.feature — the horizon unit re-derivation tool
(story 21, T8).

`experiments/confluence-chain/rederive_horizon.py` is a standalone script outside the
`algo_backtest` package (design.md: follows the `experiments/heikin-ashi-signals/`
layout), so it is loaded here by file path rather than a dotted import.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/confluence_horizon_units.feature")

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "experiments" / "confluence-chain" / "rederive_horizon.py"
)


def _load_script(path: Path) -> ModuleType:
    """Load a standalone script file as an importable module, by file path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_rh = _load_script(_SCRIPT_PATH)


def _utc(raw: str) -> datetime:
    """An ISO timestamp (`Z`, an offset, or naive) as a `datetime` — naive stays naive."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


@dataclass
class _HorizonCtx:
    """Per-scenario context: the archive path, staged decisions/source closes, and outcome."""

    archive_path: Path | None = None
    archive_sha_before: str | None = None
    decisions: list[object] = field(default_factory=list)
    closes: dict[datetime, float] = field(default_factory=dict)
    series_end: datetime | None = None
    rows: list[object] = field(default_factory=list)
    error: Exception | None = None
    output_path: Path | None = None


@pytest.fixture
def horizon_ctx() -> _HorizonCtx:
    """A fresh per-scenario horizon-unit context."""
    return _HorizonCtx()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- Background: the frozen archive ---


@given(parsers.parse('the frozen signal-horizon archive at "{path}"'))
def _archive(horizon_ctx: _HorizonCtx, path: str) -> None:
    horizon_ctx.archive_path = Path(path)
    assert horizon_ctx.archive_path.is_file(), horizon_ctx.archive_path
    horizon_ctx.archive_sha_before = _sha256(horizon_ctx.archive_path)


# --- Staging decisions and source closes ---


@given(parsers.parse('a decision at "{time}" with archived close {close:g}'))
def _decision(horizon_ctx: _HorizonCtx, time: str, close: float) -> None:
    decision_time = _utc(time)
    horizon_ctx.decisions.append(
        _rh.ArchivedDecision(decision_time=decision_time, archived_close=close)
    )
    horizon_ctx.closes.setdefault(decision_time, close)
    if horizon_ctx.series_end is None or decision_time > horizon_ctx.series_end:
        horizon_ctx.series_end = decision_time + timedelta(hours=8)


@given(parsers.parse('a second decision at "{time}" with archived close {close:g}'))
def _second_decision(horizon_ctx: _HorizonCtx, time: str, close: float) -> None:
    horizon_ctx.decisions.append(
        _rh.ArchivedDecision(decision_time=_utc(time), archived_close=close)
    )


@given(parsers.parse('a timestamp-matched source close at "{time}" of {close:g}'))
def _matched_close(horizon_ctx: _HorizonCtx, time: str, close: float) -> None:
    matched_at = _utc(time)
    horizon_ctx.closes[matched_at] = close
    if horizon_ctx.series_end is None or matched_at > horizon_ctx.series_end:
        horizon_ctx.series_end = matched_at + timedelta(hours=8)


@given(
    parsers.parse('no source close is available at "{time}" because the source series ends first')
)
def _series_ends(horizon_ctx: _HorizonCtx, time: str) -> None:
    ends_at = _utc(time)
    horizon_ctx.closes.pop(ends_at, None)
    horizon_ctx.series_end = ends_at - timedelta(minutes=1)


@given(parsers.parse('the source price series has a gap at "{time}"'))
def _gap(horizon_ctx: _HorizonCtx, time: str) -> None:
    horizon_ctx.closes.pop(_utc(time), None)


def _source(horizon_ctx: _HorizonCtx) -> object:
    series_end = horizon_ctx.series_end
    assert series_end is not None
    return _rh.SourceCloseSeries(closes=dict(horizon_ctx.closes), series_end=series_end)


# --- Running the tool ---


@when("the horizon is re-derived to a new output path")
def _rederive(horizon_ctx: _HorizonCtx, tmp_path: Path) -> None:
    assert horizon_ctx.archive_path is not None
    horizon_ctx.output_path = tmp_path / "horizon-units.json"
    horizon_ctx.rows = _rh.rederive_and_write(
        archive_path=horizon_ctx.archive_path,
        decisions=horizon_ctx.decisions,
        source=_source(horizon_ctx),
        output_path=horizon_ctx.output_path,
    )


@when("the horizon is re-derived to a new output path and fails")
def _rederive_fails(horizon_ctx: _HorizonCtx, tmp_path: Path) -> None:
    assert horizon_ctx.archive_path is not None
    output_path = tmp_path / "horizon-units.json"
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _rh.rederive_and_write(
            archive_path=horizon_ctx.archive_path,
            decisions=horizon_ctx.decisions,
            source=_source(horizon_ctx),
            output_path=output_path,
        )
    horizon_ctx.error = exc_info.value


@when("the horizon is re-derived with no output path and fails")
def _rederive_no_output(horizon_ctx: _HorizonCtx) -> None:
    assert horizon_ctx.archive_path is not None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _rh.rederive_and_write(
            archive_path=horizon_ctx.archive_path,
            decisions=horizon_ctx.decisions,
            source=_source(horizon_ctx),
            output_path=None,
        )
    horizon_ctx.error = exc_info.value


@when(parsers.parse('the horizon is re-derived to "{path}" and fails'))
def _rederive_to_archive(horizon_ctx: _HorizonCtx, path: str) -> None:
    assert horizon_ctx.archive_path is not None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        _rh.rederive_and_write(
            archive_path=horizon_ctx.archive_path,
            decisions=horizon_ctx.decisions,
            source=_source(horizon_ctx),
            output_path=Path(path),
        )
    horizon_ctx.error = exc_info.value


# --- Assertions ---


def _row(horizon_ctx: _HorizonCtx) -> object:
    assert len(horizon_ctx.rows) == 1, horizon_ctx.rows
    return horizon_ctx.rows[0]


@then(parsers.parse("the re-derived row's normalized_return_pips is {value:g}"))
def _normalized(horizon_ctx: _HorizonCtx, value: float) -> None:
    assert _row(horizon_ctx).normalized_return_pips == pytest.approx(value, abs=1e-3)  # type: ignore[attr-defined]


@then("the re-derived row's normalized_return_pips is null")
def _normalized_null(horizon_ctx: _HorizonCtx) -> None:
    assert _row(horizon_ctx).normalized_return_pips is None  # type: ignore[attr-defined]


@then(parsers.parse("the re-derived row's price_pips is {value:g}"))
def _price(horizon_ctx: _HorizonCtx, value: float) -> None:
    assert _row(horizon_ctx).price_pips == pytest.approx(value, abs=1e-6)  # type: ignore[attr-defined]


@then("the re-derived row's price_pips is null")
def _price_null(horizon_ctx: _HorizonCtx) -> None:
    assert _row(horizon_ctx).price_pips is None  # type: ignore[attr-defined]


@then(parsers.parse('the re-derived row\'s unit_status is "{status}"'))
def _unit_status(horizon_ctx: _HorizonCtx, status: str) -> None:
    assert _row(horizon_ctx).unit_status == status  # type: ignore[attr-defined]


@then(
    parsers.parse(
        'the re-derived row records both "normalized_return_pips" and "price_pips" as '
        "distinct named columns"
    )
)
def _distinct_columns(horizon_ctx: _HorizonCtx) -> None:
    mapping = _row(horizon_ctx).as_mapping()  # type: ignore[attr-defined]
    assert "normalized_return_pips" in mapping
    assert "price_pips" in mapping
    assert mapping["normalized_return_pips"] != mapping["price_pips"]


@then(parsers.parse('the horizon-unit failure names "{fragment}"'))
def _failure_names(horizon_ctx: _HorizonCtx, fragment: str) -> None:
    assert horizon_ctx.error is not None, "expected a failure but none was raised"
    assert fragment in str(horizon_ctx.error), str(horizon_ctx.error)


@then("the archive's sha256 hash after the run equals its sha256 hash before the run")
def _hash_unchanged(horizon_ctx: _HorizonCtx) -> None:
    assert horizon_ctx.archive_path is not None
    assert horizon_ctx.archive_sha_before is not None
    assert _sha256(horizon_ctx.archive_path) == horizon_ctx.archive_sha_before


@then("the report exists only at that caller-specified path")
def _report_only_at_path(horizon_ctx: _HorizonCtx) -> None:
    assert horizon_ctx.output_path is not None
    assert horizon_ctx.output_path.is_file()
    siblings = list(horizon_ctx.output_path.parent.iterdir())
    assert siblings == [horizon_ctx.output_path], siblings
