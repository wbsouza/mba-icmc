"""Step definitions for coverage.feature."""

from __future__ import annotations

from datetime import date

import pytest
from algo_transform.coverage import CoverageInput, compute_matrix, select_training_window
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/coverage.feature")


@pytest.fixture
def context() -> dict[str, object]:
    """Per-scenario mutable context."""
    return {}


@given(
    parsers.parse(
        "source {source} resolution {resolution} expects {expected:d} units in month {month}"
    )
)
@given(
    parsers.parse(
        'source "{source}" resolution "{resolution}" expects {expected:d} unit in month {month}'
    )
)
def _coverage_source(
    context: dict[str, object], source: str, resolution: str, expected: int, month: str
) -> None:
    context["source"] = source
    context["resolution"] = resolution
    context["expected"] = expected
    context["month"] = month


@given(parsers.parse("{present:d} units are present"))
@given(parsers.parse("{present:d} unit is present"))
def _present(context: dict[str, object], present: int) -> None:
    context["present"] = present


@given("the GDELT monthly coverage_ratio series:")
def _series(context: dict[str, object], datatable: list[list[str]]) -> None:
    rows = []
    for month, ratio in datatable[1:]:
        rows.append(
            CoverageInput(
                month=_month(month),
                source="gdelt",
                resolution="daily",
                units_expected=100,
                units_present=int(float(ratio) * 100),
            )
        )
    context["matrix"] = compute_matrix(rows)


@when("the coverage matrix is computed")
def _compute(context: dict[str, object]) -> None:
    context["matrix"] = compute_matrix(
        [
            CoverageInput(
                month=_month(str(context["month"])),
                source=str(context["source"]),
                resolution=str(context["resolution"]),
                units_expected=int(context["expected"]),
                units_present=int(context["present"]),
            )
        ]
    )


@when("the training window is selected")
def _select(context: dict[str, object]) -> None:
    context["window"] = select_training_window(context["matrix"])  # type: ignore[arg-type]


@then(parsers.parse("the coverage_ratio for {source} {month} is {ratio:f}"))
def _ratio(context: dict[str, object], source: str, month: str, ratio: float) -> None:
    row = context["matrix"][0]  # type: ignore[index]
    assert row.source == source
    assert row.month == _month(month)
    assert row.coverage_ratio == ratio


@then(parsers.parse("backtestable is {flag}"))
def _backtestable(context: dict[str, object], flag: str) -> None:
    assert context["matrix"][0].backtestable is (flag == "true")  # type: ignore[index]


@then(parsers.parse('backtestable for "{source}" {month} is false'))
def _source_backtestable_false(context: dict[str, object], source: str, month: str) -> None:
    row = context["matrix"][0]  # type: ignore[index]
    assert row.source == source
    assert row.month == _month(month)
    assert not row.backtestable


@then(parsers.parse("the window is {start} to {end}"))
def _window(context: dict[str, object], start: str, end: str) -> None:
    window = context["window"]
    assert window.start == _month(start)
    assert window.end == _month(end)


def _month(value: str) -> date:
    """Parse YYYY-MM into a month date."""
    year, month = (int(part) for part in value.split("-"))
    return date(year, month, 1)
