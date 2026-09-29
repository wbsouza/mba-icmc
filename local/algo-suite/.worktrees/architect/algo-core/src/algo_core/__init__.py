"""algo-core: shared abstractions for the algo-suite.

Houses the ``Instrument`` value object, the canonical storage layout (Parquet as
the source of truth plus the derived ``lean-data`` execution store), DuckDB
helpers, the config schema/loader, and the Repository and Cache ports. No I/O
side effects at import time.

See ../../SPEC.md for the contract.
"""

__version__ = "0.0.0"
