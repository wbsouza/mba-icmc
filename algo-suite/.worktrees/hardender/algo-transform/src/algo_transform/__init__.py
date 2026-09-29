"""algo-transform: raw payloads into canonical Parquet.

Resamples ticks to minute QuoteBars, writes the canonical Parquet tree, and
builds the coverage matrix and currency-strength. See
../../SPEC.md.
"""

__version__ = "0.0.0"
