"""Step definitions for gpr_decode.feature."""

from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
import xlwt
from algo_transform.decoders.bi5 import DecodeError
from algo_transform.decoders.gpr import decode_gpr
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/gpr_decode.feature")


@pytest.fixture
def context() -> dict[str, object]:
    """Per-scenario mutable context."""
    return {"raw_path": Path("raw/gpr/data_gpr_export.xls")}


@given(parsers.parse("a raw GPR file row for period {period} with index value {value:f}"))
def _gpr_row(context: dict[str, object], period: str, value: float) -> None:
    context["payload"] = f"period,gpr\n{period},{value}\n".encode()


@given("a 0-byte raw GPR file")
def _empty(context: dict[str, object]) -> None:
    context["payload"] = b""


@given("a raw GPR file that is not a valid spreadsheet")
def _malformed(context: dict[str, object]) -> None:
    context["payload"] = b"not,a,valid,gpr,file\n1,2,3,4\n"


@given(parsers.parse("a binary XLS GPR file for period {period} with index value {value:f}"))
def _gpr_xls_row(context: dict[str, object], period: str, value: float) -> None:
    """Build a real BIFF .xls workbook, the production GPR distribution format,
    with an Excel-typed date cell for the period column (the branch a UTF-8
    CSV/TSV fixture can never reach: the decoder only falls through to
    xlrd once utf-8-sig decoding itself fails)."""
    year, month = (int(part) for part in period.split("-"))
    book = xlwt.Workbook()
    sheet = book.add_sheet("GPR")
    date_style = xlwt.XFStyle()
    date_style.num_format_str = "YYYY-MM-DD"
    sheet.write(0, 0, "Period")
    sheet.write(0, 1, "GPR")
    sheet.write(1, 0, date(year, month, 1), date_style)
    sheet.write(1, 1, value)
    buf = BytesIO()
    book.save(buf)
    context["payload"] = buf.getvalue()


@when("I decode it")
def _decode(context: dict[str, object]) -> None:
    try:
        context["rows"] = decode_gpr(context["payload"], context["raw_path"])  # type: ignore[arg-type]
    except DecodeError as exc:
        context["error"] = exc


@then(parsers.parse("a canonical GPR row exists for period {period} with index {value:f}"))
def _row(context: dict[str, object], period: str, value: float) -> None:
    row = context["rows"][0]  # type: ignore[index]
    assert row.period.strftime("%Y-%m") == period
    assert row.gpr == value


@then("no value is forward-filled or interpolated")
def _no_fill(context: dict[str, object]) -> None:
    assert len(context["rows"]) == 1  # type: ignore[arg-type]


@then("a DecodeError is raised naming the file")
def _decode_error(context: dict[str, object]) -> None:
    error = context["error"]
    assert isinstance(error, DecodeError)
    assert "data_gpr_export.xls" in str(error)
