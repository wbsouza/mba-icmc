"""Steps for retraining_weights.feature: exponential recency weights and support checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import pytest
from algo_backtest.retraining.weights import (
    SupportMinima,
    age_days,
    check_support,
    effective_n,
    exponential_weights,
    normalize_mean_one,
    uniform_weights,
)
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/retraining_weights.feature")

_REL = 1e-12


@dataclass
class _WeightCtx:
    """Per-scenario state: the stage inputs, computed vectors and the last failure."""

    cutoff: datetime | None = None
    half_life: float = 60.0
    available: list[datetime] = field(default_factory=list)
    raw: tuple[float, ...] = ()
    normalized: tuple[float, ...] = ()
    n_eff: float | None = None
    stage_raw: dict[str, tuple[float, ...]] = field(default_factory=dict)
    minima: dict[str, SupportMinima] = field(default_factory=dict)
    labels: list[int] = field(default_factory=list)
    weights: list[float] = field(default_factory=list)
    error: Exception | None = None


@pytest.fixture
def w_ctx() -> _WeightCtx:
    """A fresh per-scenario context."""
    return _WeightCtx()


def _stamp(text: str) -> datetime:
    """The ISO text as given: `Z` and offsets honoured, naive stays naive."""
    return datetime.fromisoformat(text)


def _floats(text: str) -> list[float]:
    """A comma-separated float list (`nan`/`inf` allowed); empty text is the empty list."""
    return [float(cell) for cell in text.split(",") if cell.strip()]


def _cells(datatable: list[list[str]]) -> list[dict[str, str]]:
    """A Gherkin table as one dict per row, keyed by the header."""
    header, *rows = datatable
    return [dict(zip(header, row, strict=True)) for row in rows]


def _optional(text: str) -> float | None:
    """`None` for the literal `none`, else a number."""
    return None if text == "none" else float(text)


def _assert_close(got: tuple[float, ...] | list[float], expected: list[float]) -> None:
    """Element-wise closeness at 1e-12 relative (exact zeros must be exact)."""
    assert len(got) == len(expected), (got, expected)
    for value, want in zip(got, expected, strict=True):
        if want == 0.0:
            assert value == 0.0, (got, expected)
        else:
            assert value == pytest.approx(want, rel=_REL), (got, expected)


# --- exponential weights ------------------------------------------------------------------


@given(parsers.parse("the stage cutoff {cutoff} and half-life {half_life} days"))
def _stage(w_ctx: _WeightCtx, cutoff: str, half_life: str) -> None:
    w_ctx.cutoff = _stamp(cutoff)
    w_ctx.half_life = float(half_life)


@given("rows available at")
def _rows_available(w_ctx: _WeightCtx, datatable: list[list[str]]) -> None:
    w_ctx.available = [_stamp(cell["available_at"]) for cell in _cells(datatable)]


@given("rows with ages in days")
def _rows_with_ages(w_ctx: _WeightCtx, datatable: list[list[str]]) -> None:
    assert w_ctx.cutoff is not None
    w_ctx.available = [
        w_ctx.cutoff - timedelta(days=float(cell["age_days"])) for cell in _cells(datatable)
    ]


@given("no rows")
def _no_rows(w_ctx: _WeightCtx) -> None:
    w_ctx.available = []


@when("the exponential weights are computed")
def _compute(w_ctx: _WeightCtx) -> None:
    assert w_ctx.cutoff is not None
    w_ctx.raw = exponential_weights(w_ctx.available, w_ctx.cutoff, w_ctx.half_life)


@when("computing the exponential weights fails")
def _compute_fails(w_ctx: _WeightCtx) -> None:
    assert w_ctx.cutoff is not None
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        exponential_weights(w_ctx.available, w_ctx.cutoff, w_ctx.half_life)
    w_ctx.error = exc_info.value


@when(
    parsers.parse(
        "the exponential weights are computed for the {stage} stage with cutoff {cutoff} and "
        "half-life {half_life} days"
    )
)
def _compute_stage(w_ctx: _WeightCtx, stage: str, cutoff: str, half_life: str) -> None:
    w_ctx.stage_raw[stage] = exponential_weights(w_ctx.available, _stamp(cutoff), float(half_life))


@then(parsers.parse("the ages in days are {values}"))
def _ages(w_ctx: _WeightCtx, values: str) -> None:
    assert w_ctx.cutoff is not None
    _assert_close(age_days(w_ctx.available, w_ctx.cutoff), _floats(values))


@then(parsers.parse("the raw weights are {values}"))
def _raw(w_ctx: _WeightCtx, values: str) -> None:
    _assert_close(w_ctx.raw, _floats(values))


@then(parsers.parse("the {stage}-stage raw weights are {values}"))
def _stage_raw(w_ctx: _WeightCtx, stage: str, values: str) -> None:
    _assert_close(w_ctx.stage_raw[stage], _floats(values))


@then(parsers.parse("the {stage}-stage normalized weights are {values}"))
def _stage_normalized(w_ctx: _WeightCtx, stage: str, values: str) -> None:
    _assert_close(normalize_mean_one(w_ctx.stage_raw[stage]), _floats(values))


# --- normalization and effective N -------------------------------------------------------


@given(parsers.re(r"^the raw weights\s*(?P<values>.*)$"))
def _raw_weights(w_ctx: _WeightCtx, values: str) -> None:
    w_ctx.raw = tuple(_floats(values))


@when("the weights are normalized to mean one")
def _normalize(w_ctx: _WeightCtx) -> None:
    w_ctx.normalized = normalize_mean_one(w_ctx.raw)


@then(parsers.parse("the normalized weights are {values}"))
def _normalized(w_ctx: _WeightCtx, values: str) -> None:
    if not w_ctx.normalized:
        w_ctx.normalized = normalize_mean_one(w_ctx.raw)
    _assert_close(w_ctx.normalized, _floats(values))


@then(parsers.parse("the normalized weights sum to {total}"))
def _normalized_sum(w_ctx: _WeightCtx, total: str) -> None:
    assert sum(w_ctx.normalized) == pytest.approx(float(total), rel=_REL)


@when("the effective N is computed")
def _effective(w_ctx: _WeightCtx) -> None:
    w_ctx.n_eff = effective_n(w_ctx.raw)


@when("the weights are normalized to mean one and the effective N is computed again")
def _effective_after_normalizing(w_ctx: _WeightCtx) -> None:
    w_ctx.n_eff = effective_n(normalize_mean_one(w_ctx.raw))


@then(parsers.parse("the effective N is {value}"))
def _effective_is(w_ctx: _WeightCtx, value: str) -> None:
    if w_ctx.n_eff is None:
        w_ctx.n_eff = effective_n(w_ctx.raw)
    assert w_ctx.n_eff == pytest.approx(float(value), rel=_REL)


@when(parsers.re(r"^(?P<operation>normalizing to mean one|computing the effective N) fails$"))
def _operation_fails(w_ctx: _WeightCtx, operation: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        if operation == "normalizing to mean one":
            normalize_mean_one(w_ctx.raw)
        else:
            effective_n(w_ctx.raw)
    w_ctx.error = exc_info.value


# --- uniform weights ----------------------------------------------------------------------


@when(parsers.parse("uniform weights are requested for {count:d} rows"))
def _uniform(w_ctx: _WeightCtx, count: int) -> None:
    w_ctx.raw = uniform_weights(count)


@when(parsers.parse("requesting uniform weights for {count:d} rows fails"))
def _uniform_fails(w_ctx: _WeightCtx, count: int) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        uniform_weights(count)
    w_ctx.error = exc_info.value


@then(parsers.parse("there are {count:d} weights, all equal to 1.0"))
def _all_ones(w_ctx: _WeightCtx, count: int) -> None:
    assert len(w_ctx.raw) == count
    assert all(weight == 1.0 for weight in w_ctx.raw)


@then("normalizing them to mean one leaves them unchanged")
def _normalizing_is_identity(w_ctx: _WeightCtx) -> None:
    assert normalize_mean_one(w_ctx.raw) == w_ctx.raw


@then(parsers.parse("their effective N is {value}"))
def _their_effective(w_ctx: _WeightCtx, value: str) -> None:
    assert effective_n(w_ctx.raw) == pytest.approx(float(value), rel=_REL)


@then(parsers.parse('the weight failure names "{fragment}"'))
def _failure_names(w_ctx: _WeightCtx, fragment: str) -> None:
    assert w_ctx.error is not None
    assert fragment in str(w_ctx.error)


# --- support minima -----------------------------------------------------------------------


@given("the registered support minima")
def _minima(w_ctx: _WeightCtx, datatable: list[list[str]]) -> None:
    for cell in _cells(datatable):
        per_class = _optional(cell["min_per_class"])
        w_ctx.minima[cell["stage"]] = SupportMinima(
            min_rows=int(cell["min_rows"]),
            min_per_class=None if per_class is None else int(per_class),
            min_effective_n=_optional(cell["min_effective_n"]),
        )


@given(parsers.parse("{rows:d} labeled rows with {up:d} UP and {down:d} DOWN"))
def _labeled_rows(w_ctx: _WeightCtx, rows: int, up: int, down: int) -> None:
    assert up + down == rows
    w_ctx.labels = [1] * up + [0] * down


@given(parsers.parse("weights where the first {unit:d} rows weigh 1.0 and the rest weigh 0.0"))
def _unit_weights(w_ctx: _WeightCtx, unit: int) -> None:
    w_ctx.weights = [1.0] * unit + [0.0] * (len(w_ctx.labels) - unit)


@given(parsers.parse("{count:d} explicit weights of 1.0"))
def _explicit_weights(w_ctx: _WeightCtx, count: int) -> None:
    w_ctx.weights = [1.0] * count


@when(parsers.parse("the {stage} stage support is checked"))
def _check(w_ctx: _WeightCtx, stage: str) -> None:
    try:
        check_support(w_ctx.labels, w_ctx.weights, w_ctx.minima[stage], stage=stage)
    except ValueError as exc:
        w_ctx.error = exc


@when(parsers.parse("checking the {stage} stage support fails"))
def _check_fails(w_ctx: _WeightCtx, stage: str) -> None:
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011 - message asserted in Then
        check_support(w_ctx.labels, w_ctx.weights, w_ctx.minima[stage], stage=stage)
    w_ctx.error = exc_info.value


@then("the support check passes")
def _check_passes(w_ctx: _WeightCtx) -> None:
    assert w_ctx.error is None


@then(parsers.parse('the support check fails naming "{fragment}"'))
def _check_fails_naming(w_ctx: _WeightCtx, fragment: str) -> None:
    assert w_ctx.error is not None
    assert fragment in str(w_ctx.error)
