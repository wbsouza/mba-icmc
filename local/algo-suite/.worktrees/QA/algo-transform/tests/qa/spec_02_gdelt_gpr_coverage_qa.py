"""Executable CLI-only QA procedure for Spec 02.

This script mirrors ``spec-02-gdelt-gpr-coverage.qa.md``. It deliberately drives
``algo-transform`` through its command-line interface and inspects only files the
operator would see in the data root.
"""

from __future__ import annotations

import calendar
import os
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pyarrow.parquet as pq


@dataclass(frozen=True)
class CommandResult:
    """A completed CLI invocation."""

    code: int
    output: str


def main() -> None:
    """Run the full Spec 02 QA checklist."""
    scratch = worktree_root() / "tmp"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="algo-transform-qa-", dir=scratch) as tmp:
        root = Path(tmp)
        run_gdelt_happy_path(root / "gdelt-happy")
        run_gdelt_incomplete_and_corrupt(root / "gdelt-bad")
        run_gdelt_cli_flags(root / "gdelt-cli")
        run_gpr_happy_path(root / "gpr-happy")
        run_gpr_cli_flags(root / "gpr-cli")
        run_coverage_matrix(root / "coverage")
        run_unsupported_source(root / "unsupported")


def run_gdelt_happy_path(root: Path) -> None:
    """Verify GDELT decode, idempotent skip, and rebuild through the CLI."""
    populate_gdelt_month(root, 2020, 1)
    result = run_cli(root, "run", "--source", "gdelt", "--month", "2020-01")
    assert_success(result, "written")
    partition = root / "parquet/events/gdelt/year=2020/month=01/data.parquet"
    require(partition.is_file(), "GDELT event partition was not written")
    table = pq.read_table(partition)
    names = set(table.column_names)
    require(table.num_rows > 0, "GDELT partition is empty")
    require("source_url" in names, "GDELT source_url column missing")
    require("event_code" in names, "GDELT event_code column missing")
    require("goldstein_scale" in names, "GDELT goldstein_scale column missing")
    require("avg_tone" in names, "GDELT avg_tone column missing")
    require(not any("text" in name.lower() for name in names), "GDELT text column was written")
    first_mtime = partition.stat().st_mtime_ns

    result = run_cli(root, "run", "--source", "gdelt", "--month", "2020-01")
    assert_success(result, "skipped")
    require(partition.stat().st_mtime_ns == first_mtime, "GDELT skip rewrote the partition")

    result = run_cli(root, "run", "--source", "gdelt", "--month", "2020-01", "--rebuild")
    assert_success(result, "written")
    require(partition.stat().st_mtime_ns >= first_mtime, "GDELT rebuild did not leave a partition")


def run_gdelt_incomplete_and_corrupt(root: Path) -> None:
    """Verify incomplete and corrupt GDELT months write no partition."""
    populate_gdelt_month(root, 2020, 1)
    missing = gdelt_raw_path(root, 2020, 1, 5, 9, 0)
    missing.unlink()
    result = run_cli(root, "run", "--source", "gdelt", "--month", "2020-01")
    assert_failure(result, "incomplete")
    partition_dir = root / "parquet/events/gdelt/year=2020/month=01"
    require(not partition_dir.exists(), "Incomplete GDELT month wrote a partition")

    populate_gdelt_month(root, 2020, 1)
    corrupt = gdelt_raw_path(root, 2020, 1, 5, 9, 0)
    corrupt.write_bytes(b"not-a-zip")
    result = run_cli(root, "run", "--source", "gdelt", "--month", "2020-01")
    assert_failure(result, "corrupt")
    require(str(corrupt) in result.output, "Corrupt GDELT output did not name the raw path")
    require(not partition_dir.exists(), "Corrupt GDELT month wrote a partition")


def run_gdelt_cli_flags(root: Path) -> None:
    """Verify GDELT flag applicability."""
    result = run_cli(root, "run", "--source", "gdelt", "--symbol", "EURUSD", "--month", "2020-01")
    assert_failure(result, "--symbol")
    result = run_cli(root, "run", "--source", "gdelt", "--month", "2020-01")
    assert_failure(result, "incomplete")


def run_gpr_happy_path(root: Path) -> None:
    """Verify GPR whole-window transform, skip, and missing-input report."""
    write_gpr_raw(root)
    result = run_cli(root, "run", "--source", "gpr")
    assert_success(result, "written")
    partition = root / "parquet/events/gpr/data.parquet"
    require(partition.is_file(), "GPR partition was not written")
    require(pq.read_table(partition).num_rows == 3, "GPR partition row count is wrong")

    result = run_cli(root, "run", "--source", "gpr")
    assert_success(result, "skipped")

    gpr_raw_path(root).unlink()
    result = run_cli(root, "run", "--source", "gpr")
    assert_failure(result, "missing")


def run_gpr_cli_flags(root: Path) -> None:
    """Verify GPR flag applicability."""
    for flags, rejected in (
        (("--symbol", "EURUSD"), "--symbol"),
        (("--month", "2020-01"), "--month"),
        (("--from", "2020-01", "--to", "2020-02"), "--from"),
    ):
        result = run_cli(root, "run", "--source", "gpr", *flags)
        assert_failure(result, rejected)


def run_coverage_matrix(root: Path) -> None:
    """Verify coverage matrix artifacts, selected window, and reproducibility."""
    for year, month, ratio in (
        (2015, 2, 0.9),
        (2015, 3, 0.85),
        (2015, 4, 0.5),
        (2015, 5, 0.95),
        (2015, 6, 0.9),
        (2015, 7, 0.92),
    ):
        populate_gdelt_month(root, year, month, ratio=ratio, event_slot=None)
    result = run_cli(root, "coverage")
    assert_success(result, "2015-05 to 2015-07")
    matrix = root / "parquet/_meta/coverage.parquet"
    figure = root / "parquet/_meta/coverage-matrix.pdf"
    require(matrix.is_file(), "Coverage matrix was not written")
    require(figure.is_file(), "Coverage figure was not written")
    names = set(pq.read_table(matrix).column_names)
    for column in (
        "month",
        "source",
        "units_expected",
        "units_present",
        "coverage_ratio",
        "resolution",
        "backtestable",
    ):
        require(column in names, f"Coverage column missing: {column}")
    first_matrix = matrix.read_bytes()
    first_figure = figure.read_bytes()
    result = run_cli(root, "coverage")
    assert_success(result, "2015-05 to 2015-07")
    require(matrix.read_bytes() == first_matrix, "Coverage matrix is not byte-reproducible")
    require(figure.read_bytes() == first_figure, "Coverage figure is not byte-reproducible")


def run_unsupported_source(root: Path) -> None:
    """Verify unsupported sources name the known sources."""
    result = run_cli(root, "run", "--source", "nope", "--symbol", "EURUSD", "--month", "2020-01")
    assert_failure(result, "dukascopy")


def run_cli(root: Path, *args: str) -> CommandResult:
    """Run ``algo-transform`` through the installed console script."""
    env = os.environ.copy()
    env["ALGO_DATA_ROOT"] = str(root)
    completed = subprocess.run(
        ["uv", "run", "algo-transform", *args],
        cwd=algo_suite_root(),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return CommandResult(code=completed.returncode, output=completed.stdout)


def populate_gdelt_month(
    root: Path,
    year: int,
    month: int,
    *,
    ratio: float = 1.0,
    event_slot: tuple[int, int, int] | None = (2, 14, 30),
) -> None:
    """Write deterministic raw GDELT slot files for a month."""
    slots = [
        (day, hour, minute)
        for day in range(1, calendar.monthrange(year, month)[1] + 1)
        for hour in range(24)
        for minute in (0, 15, 30, 45)
    ]
    present_count = int(len(slots) * ratio)
    for day, hour, minute in slots[:present_count]:
        path = gdelt_raw_path(root, year, month, day, hour, minute)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    if event_slot is not None:
        day, hour, minute = event_slot
        gdelt_raw_path(root, year, month, day, hour, minute).write_bytes(
            gdelt_payload(year, month, day)
        )


def gdelt_payload(year: int, month: int, day: int) -> bytes:
    """Build one valid GDELT Events zip with a known row."""
    row = [""] * 61
    row[0] = "12345"
    row[1] = f"{year:04d}{month:02d}{day:02d}"
    row[5] = "USA"
    row[15] = "IRN"
    row[26] = "042"
    row[30] = "3.5"
    row[31] = "7"
    row[32] = "2"
    row[33] = "5"
    row[34] = "-1.25"
    row[60] = "https://example.test/known"
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("20200102143000.export.CSV", "\t".join(row))
    return buffer.getvalue()


def gdelt_raw_path(root: Path, year: int, month: int, day: int, hour: int, minute: int) -> Path:
    """Return the raw GDELT slot path."""
    stamp = f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}00"
    return (
        root
        / "raw"
        / "gdelt"
        / f"{year:04d}"
        / f"{month:02d}"
        / f"{day:02d}"
        / f"{stamp}.export.CSV.zip"
    )


def write_gpr_raw(root: Path) -> None:
    """Write a small raw GPR fixture."""
    path = gpr_raw_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("period,gpr\n2015-02,91.4\n2015-03,92.0\n2015-04,93.5\n")


def gpr_raw_path(root: Path) -> Path:
    """Return the raw GPR path."""
    return root / "raw" / "gpr" / "data_gpr_export.xls"


def assert_success(result: CommandResult, needle: str) -> None:
    """Assert a successful command whose output contains ``needle``."""
    require(result.code == 0, f"Expected success, got {result.code}:\n{result.output}")
    require(needle.lower() in result.output.lower(), f"Output missing {needle!r}:\n{result.output}")


def assert_failure(result: CommandResult, needle: str) -> None:
    """Assert a failing command whose output contains ``needle``."""
    require(result.code != 0, f"Expected failure, got success:\n{result.output}")
    require(needle.lower() in result.output.lower(), f"Output missing {needle!r}:\n{result.output}")


def require(condition: bool, message: str) -> None:
    """Raise an assertion failure with ``message`` when ``condition`` is false."""
    if not condition:
        raise AssertionError(message)


def algo_suite_root() -> Path:
    """Return the algo-suite workspace root."""
    return Path(__file__).resolve().parents[3]


def worktree_root() -> Path:
    """Return the assigned SwarmForge worktree root."""
    return Path(__file__).resolve().parents[4]


if __name__ == "__main__":
    main()
