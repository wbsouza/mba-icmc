"""Steps for features/parquet_roundtrip.feature — adds the Parquet -> QuoteBar read leg.

The materialize/run/assert steps are the shared ones in conftest.py; here we add the
two Parquet-specific givens that persist the staged bars and read them back through the
same repository algo-transform writes with.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from algo_core.bars import QuoteBar, Timeframe
from algo_core.instrument import build_instrument
from algo_core.layout import price_path_for
from algo_core.repository.parquet import ParquetRepository
from pytest_bdd import given, scenarios

scenarios("../features/parquet_roundtrip.feature")

_EURUSD = build_instrument("EURUSD")


@given("they are written to canonical Parquet and read back")
def _parquet_round_trip(ctx: dict[str, Any], tmp_path: Path) -> None:
    """Persist the staged bars to canonical Parquet, then replace them with the read-back."""
    first = ctx["bars"][0].timestamp
    repo: ParquetRepository[QuoteBar] = ParquetRepository(
        QuoteBar, price_path_for(tmp_path, _EURUSD, Timeframe.M1.value, first.year, first.month)
    )
    repo.put(ctx["bars"])
    ctx["bars"] = sorted(repo.read_all(), key=lambda b: b.timestamp)


@given("the read-back bars equal the originals")
def _equal_originals(ctx: dict[str, Any]) -> None:
    """The Parquet round-trip is loss-free before LEAN even sees the data."""
    assert ctx["bars"] == ctx["originals"]
