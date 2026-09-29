"""On-demand epoch provider (Story 19, T11; RWT-03, RWT-12, RWT-15, RWT-26, RWT-28).

MINIMUM VIABLE SLICE (2026-09-28, today's compressed delivery): this module currently
implements only :func:`load_active`, a single pinned load-by-id on top of
:func:`algo_backtest.retraining.bundle.load` — proving the on-disk bundle format loads
and predicts through the real engine (`engine/chain_algorithm.py`). It deliberately does
NOT yet implement the full T11 surface the design calls for: boundary-based selection via
``cycle.Coordinator.eligible_bundle``, a bounded LRU-style object cache, eviction under
capacity, or an atomic paired model/threshold switch triggered mid-replay. Those remain
real, separately gated T11/T12 work (see docs/stories/in-progress/19-adaptive-recency-
retraining/progress.md, "Integration handoff notes for Phase 3") — this is a documented
scope reduction for time, not a silent shortcut.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from algo_backtest.retraining.bundle import LoadedBundle, load

_MODULE = "retraining.provider"


def load_active(
    registry: Path, bundle_id: str, *, strategy_families: Sequence[str]
) -> LoadedBundle:
    """Load and pin `bundle_id` from `registry` as the active model/threshold pair.

    A thin, explicit seam over `bundle.load` (RWT-15's identity and family checks apply
    unchanged): callers needing the full on-demand provider (cache, eviction, boundary
    switching) should not yet rely on this beyond a single pinned bundle per run.

    Raises:
        ValueError: see `bundle.load` — missing bundle, corrupt bundle, or family mismatch.
    """
    return load(registry, bundle_id, strategy_families=strategy_families)
