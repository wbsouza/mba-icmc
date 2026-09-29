"""Shared plotting style for thesis-ready algo-analyze figures."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast

import matplotlib

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt  # noqa: E402

FIGURE_SIZE = (5.2, 3.0)
PRIMARY = "#1f77b4"
ACCENT = "#2ca02c"
DANGER = "#d62728"
GRID = "#d9d9d9"

__all__ = ["ACCENT", "DANGER", "FIGURE_SIZE", "GRID", "PRIMARY", "plt", "thesis_style"]

_RC_PARAMS: dict[str, Any] = {
    "axes.edgecolor": "#333333",
    "axes.grid": True,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "legend.fontsize": 8,
    "pdf.fonttype": 42,
    "savefig.bbox": "tight",
}


@contextmanager
def thesis_style() -> Iterator[None]:
    """Apply the shared thesis figure style for one plotting operation."""
    with plt.rc_context(cast(Any, _RC_PARAMS)):
        yield
