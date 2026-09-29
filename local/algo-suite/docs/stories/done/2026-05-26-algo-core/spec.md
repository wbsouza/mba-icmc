# algo-core — shared library (pre-existing, not yesterday's work)

**Tool:** `algo-suite/algo-core/` · **Status:** done · **Last commit before
2026-09-22:** `2f86107`, 2026-05-26 ("download: live per-unit progress;
route logs to stderr" — touches shared logging used by `algo-core`).
**Built:** 2026-05-24/25, primarily commit `50c537e` ("algo-core: implement
the shared library + restructure the workspace").

This predates yesterday's swarmforge session entirely — nothing from
2026-09-22 onward touched `algo-core`. Recorded here so the pipeline's
completion history isn't misdated as part of that session.

**Scope (from the original spec, `docs/specs/algo-core.md`, relocated into
[`algo-suite/algo-core/SPEC.md`](../../../../algo-core/SPEC.md) at `50c537e`):** the shared library every
other `algo-*` tool depends on — `Instrument` value object with LEAN
identity (symbol, security_type, market, lot_size) + composed `ForexSpec`
and typed forex catalog, canonical Parquet + derived lean-data storage
layout, a read-through `Cache` port with bounded `LruCache` and two-tier
`LocalCache` (memory + atomic JSON-on-disk), fail-fast config loader policy
with provenance, `structlog` logging, DuckDB helpers, and a `Repository`
port (Parquet writer + DuckDB reader).

See [`algo-suite/algo-core/SPEC.md`](../../../../algo-core/SPEC.md) for the current, living contract.
