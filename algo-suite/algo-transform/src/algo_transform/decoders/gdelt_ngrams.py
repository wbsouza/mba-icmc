"""Decode raw GDELT Web News NGrams minute payloads into reconstructed articles.

Reconstruction itself is `gdeltnews`'s job (n-gram-based text recovery, ~95%
similarity, Fronzetti Colladon & Vestrelli 2026) -- this module only adapts its
file-in/file-out API to the project's in-memory decoder shape (payload bytes in,
canonical rows out), matching `decoders/gdelt.py`'s contract.

Verified against the real library (not assumed): only a payload that is not
valid gzip raises -- a malformed JSON line or a line missing a required ngram
field is silently skipped by `gdeltnews` itself (resilient to messy real-world
data), so those are *not* decode errors here either.
"""

from __future__ import annotations

import contextlib
import csv
import io
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from gdeltnews.reconstruct import process_file_multiprocessing

from algo_transform.decoders.bi5 import DecodeError
from algo_transform.events import GdeltNewsArticle

# gdeltnews truncates each reconstructed article's timestamp to the hour
# (confirmed empirically: a "20200102143400" input date yields "2020010214").
_DATE_FORMAT = "%Y%m%d%H"


def decode_ngrams_minute(payload: bytes, raw_path: Path) -> list[GdeltNewsArticle]:
    """Decode one raw NGrams minute payload into reconstructed article rows.

    An empty payload is the downloader's durable MISSING marker and yields no
    rows, no error. A non-empty payload must be valid gzip; anything else
    raises `DecodeError` naming `raw_path`.
    """
    if not payload:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        gz_path = Path(tmp) / "input.webngrams.json.gz"
        gz_path.write_bytes(payload)
        csv_path = Path(tmp) / "output.csv"
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                process_file_multiprocessing(
                    input_file=str(gz_path),
                    output_file=str(csv_path),
                    num_processes=1,
                    show_progress=False,
                )
        except Exception as exc:
            raise DecodeError(f"{raw_path}: invalid GDELT NGrams payload") from exc
        return _read_articles(csv_path, raw_path)


def _read_articles(csv_path: Path, raw_path: Path) -> list[GdeltNewsArticle]:
    """Parse gdeltnews' reconstructed-article CSV into canonical rows."""
    if not csv_path.exists():
        return []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="|", quoting=csv.QUOTE_NONE)
        return [_row_to_article(row, raw_path) for row in reader if row.get("URL")]


def _row_to_article(row: dict[str, str], raw_path: Path) -> GdeltNewsArticle:
    """Convert one reconstructed-CSV row to the canonical article row."""
    try:
        return GdeltNewsArticle(
            id=row["URL"],
            text=row["Text"],
            publish_ts=datetime.strptime(row["Date"], _DATE_FORMAT).replace(tzinfo=UTC),
        )
    except (KeyError, ValueError) as exc:
        raise DecodeError(f"{raw_path}: malformed reconstructed article row") from exc
