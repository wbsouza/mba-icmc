"""Storage layout: the single source of truth for on-disk paths.

Every tool resolves its paths from one ``data_root`` so nothing is duplicated and
no tool hard-codes a location. The root comes from the ``ALGO_DATA_ROOT``
environment variable; if unset, it defaults to a ``data/`` directory at the
workspace root. The full path builders (Parquet `year=YYYY/month=MM/`, the
`lean-data/` execution store) are specified in ../../SPEC.md §6.2 and
land here during the algo-core implementation phase.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from algo_core.instrument import Instrument

ENV_DATA_ROOT = "ALGO_DATA_ROOT"
_PARQUET = "parquet"
_LEAN = "lean-data"
_RAW = "raw"


def data_root() -> Path:
    """Return the canonical data root.

    ``ALGO_DATA_ROOT`` if set (e.g. a NAS mount); otherwise ``data/`` at the
    workspace root, located by walking up from this file to the ``algo-suite``
    directory. The path is returned whether or not it exists yet.
    """
    env = os.environ.get(ENV_DATA_ROOT)
    if env:
        return Path(env).expanduser()
    return _workspace_root() / "data"


def _workspace_root(start: Path | None = None) -> Path:
    """The ``algo-suite`` workspace directory (holds the workspace pyproject).

    Walks up from ``start`` (this file by default). Raises ``RuntimeError`` if it
    cannot be located, rather than guessing a path: a wrong data root must fail
    loudly, not silently corrupt where data is read or written. Set
    ``ALGO_DATA_ROOT`` to use an explicit location.
    """
    base = start if start is not None else Path(__file__).resolve()
    for parent in base.parents:
        if (parent / "pyproject.toml").exists() and (parent / "algo-core").is_dir():
            return parent
    raise RuntimeError(
        "could not locate the algo-suite workspace root; set ALGO_DATA_ROOT explicitly"
    )


# --- Canonical Parquet partition paths (SPEC.md §6.2) ----------------------
#
# All Parquet data lives at parquet/{first}/{second}/year=YYYY/month=MM/data.parquet.
# Prices use (security_type, symbol); features use (feature_domain, dataset).
# Build and parse are inverses.


class PricePartition(BaseModel):
    """Components of a price Parquet partition path."""

    model_config = ConfigDict(frozen=True)

    security_type: str
    symbol: str
    resolution: str
    year: int
    month: int


class FeaturePartition(BaseModel):
    """Components of a feature Parquet partition path."""

    model_config = ConfigDict(frozen=True)

    feature_domain: str
    dataset: str
    year: int
    month: int


class _Segments(BaseModel):
    """The two leading names plus the month-partition, shared by both domains."""

    model_config = ConfigDict(frozen=True)

    first: str
    second: str
    year: int
    month: int


def _parquet_partition_path(
    data_root: Path, first: str, second: str, year: int, month: int
) -> Path:
    """Join the shared `parquet/{first}/{second}/year=/month=/data.parquet` path."""
    return (
        data_root
        / _PARQUET
        / first
        / second
        / f"year={year:04d}"
        / f"month={month:02d}"
        / "data.parquet"
    )


def _parse_parquet_partition(path: Path) -> _Segments:
    """Extract the two leading names and the year/month from a Parquet partition path."""
    parts = path.parts
    anchor = parts.index(_PARQUET)
    return _Segments(
        first=parts[anchor + 1],
        second=parts[anchor + 2],
        year=int(parts[anchor + 3].removeprefix("year=")),
        month=int(parts[anchor + 4].removeprefix("month=")),
    )


def price_path(
    data_root: Path, security_type: str, symbol: str, resolution: str, year: int, month: int
) -> Path:
    """Build the canonical price Parquet partition path.

    Prices carry a ``resolution`` segment (e.g. ``tick``/``minute``/``hour``/
    ``daily``) so stores at different resolutions live side by side under one
    symbol.
    """
    return (
        data_root
        / _PARQUET
        / security_type
        / symbol
        / resolution
        / f"year={year:04d}"
        / f"month={month:02d}"
        / "data.parquet"
    )


def feature_path(
    data_root: Path, feature_domain: str, dataset: str, year: int, month: int
) -> Path:
    """Build the canonical feature Parquet partition path."""
    return _parquet_partition_path(data_root, feature_domain, dataset, year, month)


def parse_price_path(path: Path) -> PricePartition:
    """Parse a price Parquet partition path back into its components (inverse of build)."""
    parts = path.parts
    anchor = parts.index(_PARQUET)
    return PricePartition(
        security_type=parts[anchor + 1],
        symbol=parts[anchor + 2],
        resolution=parts[anchor + 3],
        year=int(parts[anchor + 4].removeprefix("year=")),
        month=int(parts[anchor + 5].removeprefix("month=")),
    )


def parse_feature_path(path: Path) -> FeaturePartition:
    """Parse a feature Parquet partition path back into its components."""
    seg = _parse_parquet_partition(path)
    return FeaturePartition(
        feature_domain=seg.first, dataset=seg.second, year=seg.year, month=seg.month
    )


# --- LEAN-native execution-store paths (SPEC.md §6.2) ----------------------
#
# The durable, derived execution store LEAN replays from:
#   lean-data/{security_type}/{market}/{resolution}/{symbol}/
# The components are LEAN's own (lowercased by the caller); this builder only
# joins and parses them, keeping build and parse inverses.


class LeanPartition(BaseModel):
    """Components of a LEAN execution-store directory path."""

    model_config = ConfigDict(frozen=True)

    security_type: str
    market: str
    resolution: str
    symbol: str


def lean_data_dir(
    data_root: Path, security_type: str, market: str, resolution: str, symbol: str
) -> Path:
    """Build the LEAN execution-store directory for an instrument."""
    return data_root / _LEAN / security_type / market / resolution / symbol


def parse_lean_data_dir(path: Path) -> LeanPartition:
    """Parse a LEAN execution-store directory back into its components."""
    parts = path.parts
    anchor = parts.index(_LEAN)
    return LeanPartition(
        security_type=parts[anchor + 1],
        market=parts[anchor + 2],
        resolution=parts[anchor + 3],
        symbol=parts[anchor + 4],
    )


# --- Raw store root (provider-native sub-path is each adapter's) ------------
#
# algo-download writes provider-native bytes under raw/{source}/. The filename
# layout below that root differs per source (Dukascopy .bi5 hourly, GDELT
# .CSV.zip 15-minute, GPR single .xlsx), so it is owned by the adapter, not here.


def raw_dir(data_root: Path, source: str) -> Path:
    """Return the raw store directory for a download source: ``raw/{source}``."""
    return data_root / _RAW / source


# Dukascopy hourly raw-file layout. Shared here (not in algo-download) so the
# downloader that writes it and the transform that reads it use one contract.
_DUKASCOPY = "dukascopy"


class TickFile(BaseModel):
    """Coordinates of one hourly Dukascopy ``.bi5`` raw file."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    year: int
    month: int
    day: int
    hour: int


def dukascopy_raw_path(data_root: Path, tick: TickFile) -> Path:
    """Build the raw path for an hour's bi5 (month is 1-indexed on disk)."""
    return (
        raw_dir(data_root, _DUKASCOPY)
        / tick.symbol
        / f"{tick.year:04d}"
        / f"{tick.month:02d}"
        / f"{tick.day:02d}"
        / f"{tick.hour:02d}h.bi5"
    )


def parse_dukascopy_raw_path(path: Path) -> TickFile:
    """Recover the ``TickFile`` from a path built by :func:`dukascopy_raw_path`."""
    symbol, year, month, day, hour_file = path.parts[-5:]
    return TickFile(
        symbol=symbol,
        year=int(year),
        month=int(month),
        day=int(day),
        hour=int(hour_file.removesuffix("h.bi5")),
    )


# --- Instrument-derived builders -------------------------------------------
#
# Callers pass the Instrument (the single source of LEAN identity); the path
# classification is derived from it, never re-specified as raw strings.


def price_path_for(
    data_root: Path, instrument: Instrument, resolution: str, year: int, month: int
) -> Path:
    """Build the price Parquet path for an instrument's month-partition at a resolution."""
    return price_path(
        data_root, instrument.security_type.value, instrument.symbol, resolution, year, month
    )


def lean_data_dir_for(data_root: Path, instrument: Instrument, resolution: str) -> Path:
    """Build the LEAN execution-store directory for an instrument.

    LEAN's on-disk convention is lowercase, so the symbol is lowercased here.
    """
    return lean_data_dir(
        data_root,
        instrument.security_type.value,
        instrument.market,
        resolution,
        instrument.symbol.lower(),
    )
