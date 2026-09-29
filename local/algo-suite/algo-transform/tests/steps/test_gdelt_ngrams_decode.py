"""Steps for gdelt_ngrams_decode.feature (pytest-bdd).

Synthetic NGrams payloads are built directly (date/ngram/lang/type/pos/pre/post/url
fields, gzip-compressed line-delimited JSON) matching the real provider format
confirmed in algo-download/SPEC.md Sec 7a.3 and verified empirically against the
real `gdeltnews` package before writing this decoder.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pytest
from algo_transform.decoders.bi5 import DecodeError
from algo_transform.decoders.gdelt_ngrams import decode_ngrams_minute
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("../features/gdelt_ngrams_decode.feature")

_RAW_PATH = Path("raw/gdelt_ngrams/2020/01/02/20200102143400.webngrams.json.gz")


def _gzip_lines(records: list[dict[str, str]]) -> bytes:
    lines = "\n".join(json.dumps(r) for r in records) + "\n"
    return gzip.compress(lines.encode("utf-8"))


def _fragment(url: str, ngram: str, pos: int, pre: str = "", post: str = "") -> dict[str, str]:
    return {
        "date": "20200102143400", "ngram": ngram, "lang": "en", "type": "1",
        "pos": str(pos), "pre": pre, "post": post, "url": url,
    }


@pytest.fixture
def context() -> dict[str, Any]:
    return {}


@given(parsers.parse(
    "a GDELT NGrams payload for minute {year:d}-{month:d}-{day:d} {hour:d}:{minute:d} "
    "containing {n:d} URLs with ngram data"
))
def _multi_url_payload(
    context: dict[str, Any], year: int, month: int, day: int, hour: int, minute: int, n: int
) -> None:
    records = []
    for i in range(n):
        url = f"https://example.com/article-{i}"
        records += [
            _fragment(url, "hello world", 0, post="example"),
            _fragment(url, "world example", 6, pre="hello", post="text"),
            _fragment(url, "example text", 12, pre="world"),
        ]
    context["payload"] = _gzip_lines(records)


@given(
    "an empty raw payload (the download no-data marker for an "
    "out-of-coverage or unpublished minute)"
)
def _empty_payload(context: dict[str, Any]) -> None:
    context["payload"] = b""


@given("a non-empty payload that is not valid gzip")
def _not_gzip(context: dict[str, Any]) -> None:
    context["payload"] = b"this is not gzip data"


@given("a gzip payload whose line is not valid JSON")
def _invalid_json_line(context: dict[str, Any]) -> None:
    context["payload"] = gzip.compress(b"this is not json\n")


@given("a gzip payload whose JSON line is missing a required ngram field")
def _missing_field(context: dict[str, Any]) -> None:
    record = {"date": "20200102143400", "ngram": "x y", "lang": "en", "type": "1", "pos": "0"}
    # deliberately no "url" field
    context["payload"] = _gzip_lines([record])


@when("I decode it")
def _decode(context: dict[str, Any]) -> None:
    try:
        context["rows"] = decode_ngrams_minute(context["payload"], _RAW_PATH)
    except DecodeError as exc:
        context["error"] = exc


@then(parsers.parse("{n:d} canonical news rows are produced"))
def _n_rows(context: dict[str, Any], n: int) -> None:
    assert len(context["rows"]) == n, context["rows"]


@then("each row carries a url, a publish timestamp, and reconstructed text")
def _row_shape(context: dict[str, Any]) -> None:
    for row in context["rows"]:
        assert row.id.startswith("https://")
        assert row.publish_ts.tzinfo is not None
        assert row.text


@then("it yields zero news rows")
def _zero_rows(context: dict[str, Any]) -> None:
    assert context["rows"] == []


@then("no error is raised")
def _no_error(context: dict[str, Any]) -> None:
    assert "error" not in context


@then("a DecodeError is raised naming the minute's raw path")
def _decode_error(context: dict[str, Any]) -> None:
    error = context["error"]
    assert isinstance(error, DecodeError)
    assert str(_RAW_PATH) in str(error)
