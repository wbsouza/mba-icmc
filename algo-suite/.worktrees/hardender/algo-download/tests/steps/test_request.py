"""Step definitions for request.feature (pytest-bdd)."""

from __future__ import annotations

from algo_download.request import DownloadRequest
from pydantic import ValidationError
from pytest_bdd import parsers, scenarios, then, when

scenarios("../features/request.feature")


def _months(spec: str) -> tuple[tuple[int, int], ...]:
    """Parse a comma-separated "YYYY-MM" list into (year, month) pairs."""
    pairs = []
    for chunk in spec.split(","):
        year, month = chunk.strip().split("-")
        pairs.append((int(year), int(month)))
    return tuple(pairs)


@when(parsers.parse('I build a request for "{symbol}" with months "{spec}"'))
def _build(context: dict[str, object], symbol: str, spec: str) -> None:
    try:
        context["request"] = DownloadRequest(symbol=symbol, months=_months(spec))
    except ValidationError as exc:
        context["error"] = exc


@then("request construction fails validation")
def _failed(context: dict[str, object]) -> None:
    assert isinstance(context["error"], ValidationError)


@then(parsers.parse('the request months are "{spec}"'))
def _months_preserved(context: dict[str, object], spec: str) -> None:
    request = context["request"]
    assert isinstance(request, DownloadRequest)
    assert request.months == _months(spec)
