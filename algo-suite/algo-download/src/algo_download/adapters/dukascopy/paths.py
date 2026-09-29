"""Dukascopy URL mapping; the raw-file path contract is shared in ``algo-core``.

The on-disk raw layout (``raw/dukascopy/SYMBOL/YYYY/MM/DD/HHh.bi5``) is owned by
``algo_core.layout`` so the downloader that writes it and ``algo-transform`` that
reads it share one contract. This module keeps only the provider-specific URL
mapping and re-exports the shared path helpers under the adapter's local names.
"""

from __future__ import annotations

from algo_core.layout import TickFile, dukascopy_raw_path, parse_dukascopy_raw_path

SOURCE = "dukascopy"
_HOST = "https://datafeed.dukascopy.com/datafeed"

# Re-export the shared raw-path contract under this adapter's historical names.
raw_path = dukascopy_raw_path
parse_raw_path = parse_dukascopy_raw_path

__all__ = ["SOURCE", "TickFile", "bi5_url", "parse_raw_path", "raw_path"]


def bi5_url(tick: TickFile) -> str:
    """The public datafeed URL for an hour's bi5 (month is 0-indexed in the URL)."""
    return (
        f"{_HOST}/{tick.symbol}/{tick.year:04d}/{tick.month - 1:02d}"
        f"/{tick.day:02d}/{tick.hour:02d}h_ticks.bi5"
    )
