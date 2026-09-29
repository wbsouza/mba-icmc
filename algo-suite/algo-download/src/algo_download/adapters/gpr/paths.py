"""GPR URL and raw-path mapping."""

from __future__ import annotations

from pathlib import Path

from algo_core import layout

SOURCE = "gpr"
GPR_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"
_FILENAME = "data_gpr_export.xls"


def raw_path(data_root: Path) -> Path:
    """Build the canonical raw path for the whole-window GPR index file."""
    return layout.raw_dir(data_root, SOURCE) / _FILENAME
