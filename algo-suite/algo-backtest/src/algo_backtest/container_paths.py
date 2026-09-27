"""Paths inside the pinned LEAN container, shared by the host run path and bundled algos.

Pure constants with no LEAN or testcontainers import, so `lean_runner.py`/`run.py` on
the host and `algos/*/main.py` inside the container read the same values instead of
each hardcoding `/Lean/Data`/`/Results`.
"""

from __future__ import annotations

from pathlib import PurePosixPath

LEAN_DATA_ROOT = PurePosixPath("/Lean/Data")
RESULTS_MOUNT = PurePosixPath("/Results")

# Spec 03 (`algo-score`) Parquet is mounted under this subpath of LEAN_DATA_ROOT,
# preserving the host data root's own `parquet/...` layout beneath it so
# `algo_score`'s path builders work unchanged against NEWS_DATA_ROOT.
NEWS_SUBPATH = "news"
NEWS_DATA_ROOT = LEAN_DATA_ROOT / NEWS_SUBPATH

DECISIONS_FILE = RESULTS_MOUNT / "decisions.parquet"
