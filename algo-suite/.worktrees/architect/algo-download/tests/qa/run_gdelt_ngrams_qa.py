"""Executable QA procedure for the GDELT Web News NGrams adapter.

The companion procedure is ``spec-gdelt-ngrams.qa.md``. Keep this script in
lockstep with that document: it drives the public ``algo-download`` CLI shape
with mocked HTTP responses and verifies the same operator-facing outcomes.
"""

from __future__ import annotations

import os
import shlex
import shutil
from pathlib import Path

import httpx
import respx
from algo_download.cli import app
from typer.testing import CliRunner

_MONTH_MINUTES = 44_640
_TARGET_REL = Path("raw/gdelt_ngrams/2020/01/02/20200102143400.webngrams.json.gz")
_TARGET_URL = (
    "https://data.gdeltproject.org/gdeltv3/webngrams/"
    "20200102143400.webngrams.json.gz"
)


class QaFailure(AssertionError):
    """Raised when an executable QA check fails."""


def main() -> None:
    """Run the complete automated QA procedure."""
    scratch = _clean_scratch()
    original_env = os.environ.copy()
    try:
        os.environ["ALGO_GDELT_NGRAMS_MIN_INTERVAL"] = "0"
        _dry_run_plans_without_io(scratch / "dry-run")
        _happy_path_and_resume(scratch / "happy-resume")
        _missing_is_durable(scratch / "missing")
        _failed_fetch_writes_nothing(scratch / "failed")
        _cli_flag_applicability(scratch / "flags")
        _unsupported_source_names_known_sources(scratch / "unsupported")
    finally:
        os.environ.clear()
        os.environ.update(original_env)


def _clean_scratch() -> Path:
    """Create an empty worktree-local scratch directory for this QA run."""
    worktree_root = Path(__file__).resolve().parents[4]
    scratch = worktree_root / "tmp" / "qa-gdelt-ngrams"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    return scratch


def _dry_run_plans_without_io(data_root: Path) -> None:
    """Verify dry-run output is complete and does not fetch or write files."""
    with _mocked_feed() as router:
        result = _invoke(data_root, "run --source gdelt_ngrams --month 2020-01 --dry-run")
        _expect(result.exit_code == 0, "dry run exits 0")
        _expect(len(result.stdout.splitlines()) == _MONTH_MINUTES, "dry run lists every minute")
        _expect(router.calls.call_count == 0, "dry run makes no HTTP request")
        _expect(not _has_any_file(data_root), "dry run writes no files under data root")


def _happy_path_and_resume(data_root: Path) -> None:
    """Verify full-month download writes canonical raw files and then skips them."""
    data_root.mkdir(parents=True)
    with _mocked_feed() as router:
        _mock_default_payload(router, b"GZIP")
        result = _invoke(data_root, "run --source gdelt_ngrams --month 2020-01")
        _expect(result.exit_code == 0, "happy path exits 0")
        _expect("written=44640" in result.stdout, "happy path reports written units")
        _expect((data_root / _TARGET_REL).read_bytes() == b"GZIP", "canonical payload exists")
        _expect(_only_raw_store_written(data_root), "happy path writes only under raw/")

        calls_before_resume = router.calls.call_count
        result = _invoke(data_root, "run --source gdelt_ngrams --month 2020-01")
        _expect(result.exit_code == 0, "resume exits 0")
        _expect("skipped=44640" in result.stdout, "resume reports every unit skipped")
        _expect(router.calls.call_count == calls_before_resume, "resume makes no HTTP request")


def _missing_is_durable(data_root: Path) -> None:
    """Verify provider no-data is persisted as a durable empty payload."""
    data_root.mkdir(parents=True)
    with _mocked_feed() as router:
        _mock_missing_target(router)
        _mock_default_payload(router, b"GZIP")
        result = _invoke(data_root, "run --source gdelt_ngrams --month 2020-01")
        _expect(result.exit_code == 0, "missing run exits 0")
        _expect("missing=1" in result.stdout, "missing run counts one missing unit")
        _expect((data_root / _TARGET_REL).read_bytes() == b"", "missing marker is empty")

        calls_before_resume = router.calls.call_count
        result = _invoke(data_root, "run --source gdelt_ngrams --month 2020-01")
        _expect(result.exit_code == 0, "missing resume exits 0")
        _expect("skipped=44640" in result.stdout, "missing marker satisfies resume")
        _expect(
            router.calls.call_count == calls_before_resume,
            "missing resume makes no HTTP request",
        )


def _failed_fetch_writes_nothing(data_root: Path) -> None:
    """Verify one repeated fetch failure does not abort the rest of the run."""
    data_root.mkdir(parents=True)
    with _mocked_feed() as router:
        _mock_failed_target(router)
        _mock_default_payload(router, b"GZIP")
        result = _invoke(data_root, "run --source gdelt_ngrams --month 2020-01")
        _expect(result.exit_code != 0, "failed fetch flips the exit code")
        _expect("failed=1" in result.stdout, "failed fetch is counted")
        _expect(not (data_root / _TARGET_REL).exists(), "failed target writes nothing")
        payloads = list((data_root / "raw/gdelt_ngrams").rglob("*.webngrams.json.gz"))
        _expect(len(payloads) == _MONTH_MINUTES - 1, "other minutes are still written")


def _cli_flag_applicability(data_root: Path) -> None:
    """Verify the global source rejects symbols and requires a date span."""
    symbol_result = _invoke(
        data_root, "run --source gdelt_ngrams --symbol EURUSD --month 2020-01"
    )
    _expect(symbol_result.exit_code != 0, "symbol flag is rejected")
    _expect("--symbol" in symbol_result.stdout, "symbol rejection names --symbol")

    with _mocked_feed() as router:
        result = _invoke(data_root, "run --source gdelt_ngrams --month 2020-01 --dry-run")
        _expect(result.exit_code == 0, "source runs without symbol")
        _expect(router.calls.call_count == 0, "symbol-free dry run makes no HTTP request")

    missing_span = _invoke(data_root, "run --source gdelt_ngrams")
    _expect(missing_span.exit_code != 0, "source requires a date span")


def _unsupported_source_names_known_sources(data_root: Path) -> None:
    """Verify an unsupported source error names the known source set."""
    result = _invoke(data_root, "run --source nope --month 2020-01")
    _expect(result.exit_code != 0, "unsupported source exits non-zero")
    for source in ("dukascopy", "gdelt", "gpr", "gdelt_ngrams"):
        _expect(source in result.stdout, f"unsupported source output names {source}")


def _mocked_feed() -> respx.MockRouter:
    """Create a permissive mocked HTTP router for one QA section."""
    return respx.mock(assert_all_called=False, assert_all_mocked=False)


def _mock_default_payload(router: respx.MockRouter, payload: bytes) -> None:
    """Mock all GDELT NGrams GETs to return the given payload."""
    router.route(method="GET", host="data.gdeltproject.org").mock(
        return_value=httpx.Response(200, content=payload)
    )


def _mock_missing_target(router: respx.MockRouter) -> None:
    """Mock the target minute as provider no-data."""
    router.get(_TARGET_URL).mock(return_value=httpx.Response(404, content=b""))


def _mock_failed_target(router: respx.MockRouter) -> None:
    """Mock the target minute as a repeated transport failure."""
    router.get(_TARGET_URL).mock(side_effect=httpx.ConnectError)


def _invoke(data_root: Path, args: str) -> object:
    """Invoke the CLI with an isolated data root."""
    data_root.mkdir(parents=True, exist_ok=True)
    env = {"ALGO_DATA_ROOT": str(data_root), "ALGO_GDELT_NGRAMS_MIN_INTERVAL": "0"}
    return CliRunner().invoke(app, shlex.split(args), env=env)


def _has_any_file(root: Path) -> bool:
    """Return whether the data root contains any file."""
    return root.exists() and any(path.is_file() for path in root.rglob("*"))


def _only_raw_store_written(root: Path) -> bool:
    """Return whether all direct data-root entries are the raw store."""
    return {path.name for path in root.iterdir()} <= {"raw"}


def _expect(condition: bool, message: str) -> None:
    """Raise a readable QA failure when a condition is false."""
    if not condition:
        raise QaFailure(message)


if __name__ == "__main__":
    main()
