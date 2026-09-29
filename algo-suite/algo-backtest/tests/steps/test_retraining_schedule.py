"""Steps for retraining_schedule.feature: exact-UTC epoch planning and row selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pytest
from algo_backtest.chain.filters.f7_meta_learner import (
    TrainingRow,
    WalkForwardSplit,
    walk_forward_split,
)
from algo_backtest.retraining.ingestion import SourceRow
from algo_backtest.retraining.schedule import (
    Epoch,
    Span,
    StageSpans,
    epoch_starting,
    monthly_epochs,
    select_rows,
    stage_spans,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/retraining_schedule.feature")


@dataclass
class _ScheduleCtx:
    """Per-scenario state: planned epochs, computed spans, candidate rows, last failure."""

    epochs: tuple[Epoch, ...] = ()
    spans: StageSpans | None = None
    all_spans: list[StageSpans] = field(default_factory=list)
    rows: list[SourceRow] = field(default_factory=list)
    training_rows: list[TrainingRow] = field(default_factory=list)
    selected: tuple[SourceRow, ...] = ()
    legacy_split: WalkForwardSplit | None = None
    error: Exception | None = None


@pytest.fixture
def sched_ctx() -> _ScheduleCtx:
    """A fresh per-scenario context."""
    return _ScheduleCtx()


def _stamp(text: str) -> datetime:
    """The ISO text as given: `Z` and offsets are honoured, naive stays naive."""
    return datetime.fromisoformat(text)


def _optional_stamp(text: str) -> datetime | None:
    """`None` for the literal `None`, else `_stamp`."""
    return None if text == "None" else _stamp(text)


def _cells(datatable: list[list[str]]) -> list[dict[str, str]]:
    """A Gherkin table as one dict per row, keyed by the header."""
    header, *rows = datatable
    return [dict(zip(header, row, strict=True)) for row in rows]


def _keys(text: str) -> tuple[str, ...]:
    """A comma-separated key list; the empty string is the empty tuple."""
    return tuple(key.strip() for key in text.split(",") if key.strip())


# --- monthly epochs -------------------------------------------------------------------


@when(parsers.parse("the monthly epochs from {start} to {end} are planned"))
def _plan(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    sched_ctx.epochs = monthly_epochs(_stamp(start), _stamp(end))


@when(parsers.parse("planning the monthly epochs from {start} to {end} fails"))
def _plan_fails(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        monthly_epochs(_stamp(start), _stamp(end))
    sched_ctx.error = exc_info.value


@then(parsers.parse("there are {count:d} epochs"))
def _epoch_count(sched_ctx: _ScheduleCtx, count: int) -> None:
    assert len(sched_ctx.epochs) == count


@then(parsers.parse("the first epoch deploys over [{start}, {end})"))
def _first_epoch(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    assert (sched_ctx.epochs[0].start, sched_ctx.epochs[0].end) == (_stamp(start), _stamp(end))


@then(parsers.parse("the last epoch deploys over [{start}, {end})"))
def _last_epoch(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    assert (sched_ctx.epochs[-1].start, sched_ctx.epochs[-1].end) == (
        _stamp(start),
        _stamp(end),
    )


@then("every epoch starts exactly where the previous one ends")
def _contiguous(sched_ctx: _ScheduleCtx) -> None:
    for earlier, later in zip(sched_ctx.epochs, sched_ctx.epochs[1:], strict=False):
        assert later.start == earlier.end
        assert later.start > earlier.start


@then(parsers.parse("the union of the epochs is exactly [{start}, {end})"))
def _union(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    """Contiguity plus the outer bounds: the union is the registered span, nothing more."""
    _contiguous(sched_ctx)
    assert sched_ctx.epochs[0].start == _stamp(start)
    assert sched_ctx.epochs[-1].end == _stamp(end)


@then(parsers.parse("the epoch starting {start} ends at {end} and lasts {days:d} days"))
def _epoch_length(sched_ctx: _ScheduleCtx, start: str, end: str, days: int) -> None:
    epoch = epoch_starting(sched_ctx.epochs, _stamp(start))
    assert epoch.end == _stamp(end)
    assert (epoch.end - epoch.start).days == days


@then(parsers.parse('the schedule failure names "{fragment}"'))
def _failure_names(sched_ctx: _ScheduleCtx, fragment: str) -> None:
    assert sched_ctx.error is not None
    assert fragment in str(sched_ctx.error)


# --- stage spans ----------------------------------------------------------------------


@given(parsers.parse("the registered monthly schedule from {start} to {end}"))
def _registered(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    sched_ctx.epochs = monthly_epochs(_stamp(start), _stamp(end))


@when(
    parsers.parse("the stage spans of the epoch starting {start} are computed for policy {policy}")
)
def _compute_spans(sched_ctx: _ScheduleCtx, start: str, policy: str) -> None:
    sched_ctx.spans = stage_spans(epoch_starting(sched_ctx.epochs, _stamp(start)), policy)


@when(
    parsers.parse(
        "computing the stage spans of the epoch starting {start} for policy {policy} fails"
    )
)
def _compute_spans_fails(sched_ctx: _ScheduleCtx, start: str, policy: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        stage_spans(epoch_starting(sched_ctx.epochs, _stamp(start)), policy)
    sched_ctx.error = exc_info.value


@when(parsers.parse("the stage spans of every epoch are computed for policy {policy}"))
def _compute_all_spans(sched_ctx: _ScheduleCtx, policy: str) -> None:
    sched_ctx.all_spans = [stage_spans(epoch, policy) for epoch in sched_ctx.epochs]


def _assert_span(span: Span, start: str, end: str) -> None:
    """Exact bounds, as instants."""
    assert (span.start, span.end) == (_stamp(start), _stamp(end)), str(span)


@then(parsers.parse("the family span is [{start}, {end})"))
def _family_span(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    assert sched_ctx.spans is not None
    _assert_span(sched_ctx.spans.family, start, end)


@then(parsers.parse("the combiner span is [{start}, {end})"))
def _combiner_span(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    assert sched_ctx.spans is not None
    _assert_span(sched_ctx.spans.combiner, start, end)


@then(parsers.parse("the threshold span is [{start}, {end})"))
def _threshold_span(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    assert sched_ctx.spans is not None
    _assert_span(sched_ctx.spans.threshold, start, end)


@then(parsers.parse("the deployment span is [{start}, {end})"))
def _deployment_span(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    assert sched_ctx.spans is not None
    _assert_span(sched_ctx.spans.deployment, start, end)


@then("in every epoch the family span ends where the combiner span begins")
def _family_meets_combiner(sched_ctx: _ScheduleCtx) -> None:
    assert sched_ctx.all_spans
    for spans in sched_ctx.all_spans:
        assert spans.family.end == spans.combiner.start


@then("in every epoch the combiner span ends where the threshold span begins")
def _combiner_meets_threshold(sched_ctx: _ScheduleCtx) -> None:
    for spans in sched_ctx.all_spans:
        assert spans.combiner.end == spans.threshold.start


@then("in every epoch the threshold span ends one day before deployment begins")
def _threshold_before_deployment(sched_ctx: _ScheduleCtx) -> None:
    for spans in sched_ctx.all_spans:
        assert (spans.deployment.start - spans.threshold.end).total_seconds() == 86400


# --- row selection --------------------------------------------------------------------


@given("the candidate rows")
def _candidate_rows(sched_ctx: _ScheduleCtx, datatable: list[list[str]]) -> None:
    """Rows for the exact-UTC selector (by availability) and, in parallel, legacy
    `TrainingRow`s stamped at their bucket start for the walk-forward regression guard."""
    for cell in _cells(datatable):
        sched_ctx.rows.append(
            SourceRow(
                key=cell["key"],
                available_at=_stamp(cell["available_at"]),
                label_time=_optional_stamp(cell["label_time"]),
                label=int(cell["label"]),
            )
        )
        sched_ctx.training_rows.append(
            TrainingRow(
                timestamp=_stamp(cell["bucket_start"]),
                features={"key": cell["key"]},
                label=int(cell["label"]),
                label_time=_optional_stamp(cell["label_time"]),
            )
        )


@given("the candidate rows with trade context")
def _candidate_rows_with_context(sched_ctx: _ScheduleCtx, datatable: list[list[str]]) -> None:
    """The selector's row type has no vetoed/traded/pnl fields: the context is dropped here,
    which is exactly RWT-09 (eligibility cannot depend on what the selector cannot see)."""
    for cell in _cells(datatable):
        assert {"vetoed", "traded", "trade_pnl"} <= cell.keys()
        sched_ctx.rows.append(
            SourceRow(
                key=cell["key"],
                available_at=_stamp(cell["available_at"]),
                label_time=_optional_stamp(cell["label_time"]),
                label=int(cell["label"]),
            )
        )


@when(parsers.parse("the rows are selected for the span [{start}, {end})"))
def _select(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    sched_ctx.selected = select_rows(sched_ctx.rows, Span(_stamp(start), _stamp(end)))


@when(parsers.parse("selecting the rows for the span [{start}, {end}) fails"))
def _select_fails(sched_ctx: _ScheduleCtx, start: str, end: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        select_rows(sched_ctx.rows, Span(_stamp(start), _stamp(end)))
    sched_ctx.error = exc_info.value


@then(parsers.re(r'the selected keys are "(?P<keys>.*)"'))
def _selected_keys(sched_ctx: _ScheduleCtx, keys: str) -> None:
    assert tuple(row.key for row in sched_ctx.selected) == _keys(keys)


@when(
    parsers.parse(
        "the rows are walk-forward split (legacy) at train_end {train_end}, "
        "validation_end {validation_end}, test_end {test_end}"
    )
)
def _legacy_split(
    sched_ctx: _ScheduleCtx, train_end: str, validation_end: str, test_end: str
) -> None:
    sched_ctx.legacy_split = walk_forward_split(
        sched_ctx.training_rows,
        train_end=date.fromisoformat(train_end),
        validation_end=date.fromisoformat(validation_end),
        test_end=date.fromisoformat(test_end),
    )


@then(parsers.parse('the legacy train span holds the keys "{keys}"'))
def _legacy_train_keys(sched_ctx: _ScheduleCtx, keys: str) -> None:
    assert sched_ctx.legacy_split is not None
    train_keys: tuple[Any, ...] = tuple(row.features["key"] for row in sched_ctx.legacy_split.train)
    assert train_keys == _keys(keys)
