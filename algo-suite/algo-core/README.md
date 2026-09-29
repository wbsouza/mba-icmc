# algo-core

Shared **library** for the algo-suite (no CLI; imported, never run). It is the one
place the cross-cutting contracts live, so the tools never diverge.

## What it owns

- **`Instrument`** value object (composition: an `AssetSpec` per security type;
  `ForexSpec` for the TCC) — the **single source of LEAN identity**: `symbol`,
  `security_type` (LEAN `SecurityType`), `market` (`oanda`), `digits`,
  `unit`/`unit_size`, `lot_size` (100 000), `details`. `layout.price_path_for` /
  `lean_data_dir_for` derive paths from it; callers never pass raw
  `security_type`/`market` strings.
- **Storage layout** (`layout.py`): resolves `data_root` (`ALGO_DATA_ROOT`,
  default `algo-suite/data/`) and builds/parses the canonical Parquet paths
  (`parquet/{security_type}/{symbol}/year=/month=/`) and the derived `lean-data/`
  execution-store paths. Also exposes the generic raw store root
  (`raw_dir(data_root, source)` → `raw/{source}/`); each download adapter owns its
  provider-native sub-path below it.
- **Config** (`config/`): the schema-driven **loader policy** — hard-stop on a
  missing trading-impactful param, default-with-log on operational, explicit-null
  disables, schema-version check, provenance per parameter. *Not* built on
  pydantic-settings; `config.resolve()` reads/merges the YAML files + `ALGO_*`
  env overrides (the convention-over-config resolution, TD-3 resolved).
- **DuckDB helpers** (`duck.py`): connection factory + Parquet read.
- **`Repository[M]` port**: `put` / `read_all` / `exists` over typed value
  objects; `ParquetRepository` (pyarrow writer) + `DuckDBRepository` (DuckDB
  reader, composing the writer; imported lazily so a duckdb-less environment such
  as the LEAN container can still use `ParquetRepository`). A query/analytical interface (filtered/joined
  reads with pushdown) is **deferred — TD-14**.
- **`Cache` port**: read-through `get_or_compute`; `LruCache` (bounded
  in-process default) selected via `build_cache(name)`; two-tier `LocalCache`
  (memory tier + atomic JSON-on-disk). A containerized backend is an optional
  later upgrade behind the same port.
- **`logging.py`**: structlog config (`resolve_level`, `configure_logging`,
  `get_logger`).

No I/O side effects at import time.

## Used by

All five pipeline tools depend on it via the uv workspace
(`algo-core = { workspace = true }`).

## Status

Implemented and gated: `Instrument` + catalog, `layout`, the full `cache` stack,
the `config` loader policy, `logging`, `duck`, and the `Repository`. 46 BDD
scenarios, 99% line coverage, fail-fast throughout. Deferred items are tracked in
[`../docs/technical-debt.md`](../docs/technical-debt.md).

## Develop

```bash
uv run pytest algo-core      # BDD features under tests/features/, steps under tests/steps/
make -C .. cov               # coverage for this package
```

Spec: [`SPEC.md`](SPEC.md).
