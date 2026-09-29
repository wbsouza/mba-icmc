"""Read the whole-window raw GPR index file."""

from __future__ import annotations

from pathlib import Path

from algo_core.layout import raw_dir
from pydantic import BaseModel, ConfigDict

from algo_transform.decoders.gpr import decode_gpr
from algo_transform.events import GprEvent

_SOURCE = "gpr"
_RAW_FILE = "data_gpr_export.xls"


class GprLoadResult(BaseModel):
    """Decoded GPR index rows."""

    model_config = ConfigDict(frozen=True)

    rows: tuple[GprEvent, ...]


def raw_path(data_root: Path) -> Path:
    """Build the canonical raw GPR file path."""
    return raw_dir(data_root, _SOURCE) / _RAW_FILE


def event_path(data_root: Path) -> Path:
    """Build the canonical whole-window GPR event Parquet path."""
    return data_root / "parquet" / "events" / _SOURCE / "data.parquet"


def load_events(data_root: Path) -> GprLoadResult:
    """Decode the single raw GPR file."""
    rows = decode_gpr(raw_path(data_root).read_bytes(), raw_path(data_root))
    return GprLoadResult(rows=tuple(rows))
