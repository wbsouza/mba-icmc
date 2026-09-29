"""Step definitions for gdelt_decode.feature."""

from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from algo_transform.decoders.bi5 import DecodeError
from algo_transform.decoders.gdelt import decode_events_zip
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/gdelt_decode.feature")


@pytest.fixture
def context() -> dict[str, object]:
    """Per-scenario mutable context."""
    return {"raw_path": Path("raw/gdelt/2020/01/02/20200102143000.export.CSV.zip")}


def _event_row(event_id: int, date_added: str = "20200102153000") -> str:
    """Build a 61-column GDELT Events row with canonical fields populated."""
    row = [""] * 61
    row[0] = str(event_id)
    row[1] = "20200102"
    row[5] = "USA"
    row[15] = "IRN"
    row[26] = "042"
    row[30] = "3.5"
    row[31] = "7"
    row[32] = "2"
    row[33] = "5"
    row[34] = "-1.25"
    row[59] = date_added
    row[60] = f"https://example.test/{event_id}"
    return "\t".join(row)


def _zip(rows: list[str]) -> bytes:
    """Zip tab-delimited rows as one Events CSV member."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("events.export.CSV", "\n".join(rows))
    return buffer.getvalue()


@given(
    parsers.parse(
        "a GDELT Events zip for slot {stamp} containing {count:d} tab-delimited event rows"
    )
)
def _events_zip(context: dict[str, object], stamp: str, count: int) -> None:
    context["payload"] = _zip([_event_row(index + 1) for index in range(count)])


@given(
    parsers.parse(
        "a GDELT Events zip for slot {stamp} containing {count:d} tab-delimited event rows "
        "with DATEADDED {date_added}"
    )
)
def _events_zip_with_date_added(
    context: dict[str, object], stamp: str, count: int, date_added: str
) -> None:
    context["payload"] = _zip([_event_row(index + 1, date_added) for index in range(count)])


@given(
    "an empty raw payload (the download no-data marker for an out-of-coverage or "
    "unpublished slot)"
)
def _empty_payload(context: dict[str, object]) -> None:
    context["payload"] = b""


@given("a non-empty payload that is not a valid zip")
def _not_a_zip(context: dict[str, object]) -> None:
    context["payload"] = b"not-a-zip"


@given("a zip whose CSV row has a mismatched column count")
def _bad_column_count(context: dict[str, object]) -> None:
    context["payload"] = _zip(["too\tfew\tcolumns"])


@given("a zip whose CSV row has an invalid numeric field")
def _bad_numeric_field(context: dict[str, object]) -> None:
    row = _event_row(1).split("\t")
    row[30] = "not-a-number"
    context["payload"] = _zip(["\t".join(row)])


@given("a zip whose CSV row has an invalid DATEADDED value")
def _bad_date_added(context: dict[str, object]) -> None:
    row = _event_row(1).split("\t")
    row[59] = "not-a-date"
    context["payload"] = _zip(["\t".join(row)])


@when("I decode it")
def _decode(context: dict[str, object]) -> None:
    try:
        context["events"] = decode_events_zip(
            context["payload"], context["raw_path"]  # type: ignore[arg-type]
        )
    except DecodeError as exc:
        context["error"] = exc


@then(parsers.parse("{count:d} canonical event rows are produced"))
def _row_count(context: dict[str, object], count: int) -> None:
    assert len(context["events"]) == count  # type: ignore[arg-type]


@then(
    "each row keeps its GLOBALEVENTID, event date, EventCode, GoldsteinScale, "
    "AvgTone and SOURCEURL verbatim"
)
def _fields_preserved(context: dict[str, object]) -> None:
    event = context["events"][0]  # type: ignore[index]
    assert event.global_event_id == 1
    assert event.event_date.isoformat() == "2020-01-02"
    assert event.event_code == "042"
    assert event.goldstein_scale == 3.5
    assert event.avg_tone == -1.25
    assert event.source_url == "https://example.test/1"


@then(parsers.parse("the event's date_added is {expected}"))
def _date_added(context: dict[str, object], expected: str) -> None:
    event = context["events"][0]  # type: ignore[index]
    assert event.date_added.isoformat() == expected


@then("no row has an article-text field")
def _no_article_text(context: dict[str, object]) -> None:
    assert "article_text" not in type(context["events"][0]).model_fields  # type: ignore[index]


@then("it yields zero event rows")
def _zero_rows(context: dict[str, object]) -> None:
    assert context["events"] == []


@then("no error is raised")
def _no_error(context: dict[str, object]) -> None:
    assert "error" not in context


@then("a DecodeError is raised naming the slot's raw path")
def _decode_error(context: dict[str, object]) -> None:
    error = context["error"]
    assert isinstance(error, DecodeError)
    assert "20200102143000.export.CSV.zip" in str(error)
