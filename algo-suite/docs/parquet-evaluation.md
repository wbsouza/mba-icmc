# Parquet Evaluation

## Context

This note records the storage-format decision discussion for the TCC execution
pipeline.

The initial idea was to keep all datasets in Parquet because it is compact,
portable, and works well with DuckDB. That is attractive for research and
feature-engineering workflows. However, the execution engine chosen for the
project is LEAN, and LEAN is fundamentally file-oriented for historical
backtests.

This creates an important distinction:

- some datasets are used mainly for offline processing and analysis;
- some datasets sit directly on the hot backtest replay path.

Those two categories should not be forced into the same storage format.

## Main question

Should Parquet be the canonical format for everything, including the data that
LEAN replays repeatedly during thousands of simulations?

## Why Parquet was attractive in the first place

Parquet was considered for broad adoption because it offers several real
advantages:

- compact columnar storage;
- efficient scans and aggregations;
- strong compatibility with DuckDB;
- portability across ecosystems;
- a clean interchange boundary for a future migration to Go or Rust;
- good support for intermediate datasets that need to be rebuilt, inspected,
  or joined with other sources.

For the research side of the project, those are meaningful benefits. They
reduce friction when:

- storing normalized datasets;
- joining news with scores and event tables;
- running offline feature engineering;
- validating coverage windows;
- auditing what was ingested and how it was transformed.

So the discussion was never "Parquet is bad". The discussion was whether those
advantages still justify its use on the execution-facing side of the system.

## Findings

### 1. Parquet is strong for analytical workloads

Parquet remains valuable because:

- it is compact and columnar;
- DuckDB queries it efficiently;
- it is portable across ecosystems;
- it is a good interchange boundary for a future migration to Go or Rust;
- it works well for joins, deduplication, scoring, aggregation, and audit.

So Parquet is justified where the workload is:

- ingest;
- normalize;
- query;
- enrich;
- rescore;
- aggregate;
- audit;
- export.

### 2. Parquet is weak on LEAN's hot replay path

For the repeated simulation loop, Parquet introduces avoidable overhead if the
engine cannot consume it natively.

The problematic path is:

- read Parquet;
- convert to LEAN-compatible representation;
- write LEAN files;
- let LEAN read those files again.

If this happens repeatedly, Parquet becomes a conversion tax rather than an
advantage.

The main cost driver in the project is not downloading once. It is executing
many backtests while varying filters, thresholds, and strategy combinations.
Therefore, the dominant architectural optimization target is replay efficiency,
not ingest elegance.

## Main concern: CPU and I/O overhead during intensive simulations

The central concern behind this decision is that the project is expected to run
many simulations, not just one or two.

The real workload looks like:

- download once;
- normalize once;
- prepare the feature set;
- then execute a large number of backtests while changing filters, thresholds,
  ablations, and strategy variants.

In that workflow, the expensive part is the repeated simulation cycle.

If Parquet sits on that hot path, the operating system and runtime may pay for:

- repeated Parquet reads;
- repeated decompression and decoding;
- repeated conversion into LEAN-friendly files or records;
- repeated writes of derived execution files;
- repeated re-reads by LEAN itself.

Even if each individual step is acceptable in isolation, the compound cost
becomes material when multiplied across many runs.

This creates two specific concerns:

### CPU concern

Repeated decoding and transformation is wasted compute if the same historical
execution inputs are reused across many runs.

The CPU should be spent on:

- the backtest engine;
- model inference when required;
- filter evaluation;
- parameter sweeps;
- significance testing.

It should not be spent repeatedly regenerating the same execution-ready data if
that data could have been materialized once and reused.

### I/O concern

Repeated conversion also increases filesystem churn:

- read one format;
- write another;
- read the derived format again;
- repeat for every simulation batch.

From the OS perspective, that means additional cache pressure, more temporary
artifacts, and more serialization work than the simulation loop actually needs.

This is especially undesirable when the project goal is to run many backtests
to compare combinations of filters and strategies.

## Interpretation of the concern

The concern is not that Parquet is inefficient in general.

The concern is that:

- Parquet is efficient for analytical access,
- while LEAN is optimized for its own historical-data conventions,
- so forcing Parquet into LEAN's replay path creates a mismatch between storage
  format and execution consumer.

That mismatch is what risks wasting CPU and I/O during intensive simulations.

### 3. LEAN-native format is better for execution-facing data

For data that LEAN consumes intensively during simulations, the best choice is
to persist it directly in a LEAN-friendly format and reuse it across runs.

That avoids:

- repeated conversion;
- extra filesystem churn;
- unnecessary serialization hops;
- more moving parts in the critical runtime path.

### 4. DuckDB does not require Parquet, but Parquet still has value

DuckDB can store native tables and does not depend on Parquet. In a purely
Python + DuckDB stack, a DuckDB-only design would be simpler.

However, Parquet still has strategic value as a language-neutral storage layer.
Because a future migration to Go or Rust is a real possibility, Parquet is
useful as an interoperability boundary.

That means Parquet earns its place when it protects the data layer from being
tied too tightly to one engine implementation.

## Decision

Use a split-storage architecture:

- **Parquet** for analytical and portable datasets.
- **LEAN-native format** for execution-ready datasets on the hot simulation
  path.

## Practical rule

If a dataset is:

- queried, joined, transformed, rescored, audited, or exchanged across tools,
  store it in **Parquet**.

If a dataset is:

- replayed by LEAN on every simulation run,
  store it in **LEAN-native format**.

## Recommended storage split

### `raw/`

Original downloaded payloads.

Examples:

- raw news/event payloads;
- raw market-data payloads from source providers.

### `parquet/`

Canonical analytical store.

Examples:

- normalized news/articles;
- scored sentiment data;
- event aggregates;
- intermediate feature tables;
- audit-friendly derived datasets;
- any dataset expected to be reused by DuckDB, Python, Go, or Rust tools.

### `lean-data/`

Canonical execution store for repeated simulations.

Examples:

- market price history used by LEAN;
- exogenous time series that must be replayed efficiently by LEAN during
  backtests.

### `runs/`

Backtest outputs.

Examples:

- `trades.parquet`;
- `decisions.parquet`;
- equity curves;
- run metadata and provenance files.

## Consequences

### Advantages

- keeps the hot simulation path fast;
- preserves Parquet where it actually adds value;
- keeps DuckDB effective for offline analysis;
- supports future migration to Go or Rust;
- avoids forcing a single storage format across incompatible workloads.

### Tradeoff

- the architecture is no longer "one canonical format for everything";
- instead, it uses the right format for each workload boundary.

This is acceptable because the boundaries are clear:

- analytical boundary -> Parquet;
- execution boundary -> LEAN-native.

## Final conclusion

Parquet should be kept, but not everywhere.

It is justified as the canonical analytical and interoperability layer. It is
not justified as the runtime format for data that LEAN replays repeatedly during
the hot backtest loop.

Therefore, the project should:

- keep Parquet for the DuckDB/research/feature-engineering side;
- keep LEAN-native files for the execution/replay side.

---

## Refined decision (2026-05-24)

The discussion above settled the *storage* split. A follow-up discussion settled
the *compute* model and reconciled it with live production. This section is the
authoritative version; the sections above are the reasoning that led here.

### 1. Split storage: by reuse, not one format for everything

- **Parquet = canonical source of truth.** Analytical and portable data: ingest,
  normalize, join, score, aggregate, audit, export, and the language-neutral
  interchange boundary for a future Go/Rust port. Read a handful of times.
- **`lean-data/` = durable materialized execution store.** The execution-facing
  data LEAN replays. *Derived* from Parquet (so Parquet stays the source of
  truth and `lean-data/` is rebuildable if lost), but **persisted on the
  filesystem and reused across the whole backtest sweep**, not regenerated per
  run. The avoidable cost was never "Parquet on the hot path"; it was
  **reconverting/recomputing per run**. Fix = materialize once, reuse.
- **tmpfs `/dev/shm`** is an optional RAM-resident *copy* of `lean-data/` for hot
  reads, re-stageable from the durable store, an accelerator, never the source.
- **Price lives in both** (intentional ~100 MB duplication at minute resolution):
  Parquet copy feeds the offline feature/training/analytics layer (which needs
  columnar dataframes and DuckDB joins); `lean-data/` copy feeds replay. **Ticks
  stay Parquet-only** (5–10 GB, used only in slippage modeling, not on the
  minute-replay path).

### 2. One feature/scorer engine, mode-agnostic (batch ∥ stream)

There is a **single implementation** of feature and sentiment computation, a pure
function of `(bar + rolling state)`. It runs in two execution modes from the same
code: vectorized over history (backtest) and one bar at a time (live). This is
**non-negotiable**: two implementations would cause **train/serve skew**, the
deployed model seeing inputs it was not trained on. The model is **always trained
offline** on the historical panel and **deployed**; production never trains, it
loads the trained artifact and infers.

### 3. Read-through cache: compute each new bar exactly once

All cacheable derived outputs (features, sentiment scores, materialized
`lean-data/`) go through the `Cache` port in **read-through + write** mode,
**identically in backtest and live**:

```
feature(bar) = cache.get_or_compute(key, engine.compute(bar, state))
   hit  → return cached
   miss → compute → store → return
```

- **Backtest:** the first run cold-misses and fills the cache; the rest of the
  sweep (varying filters/thresholds/ablations over the *same* history) is all
  hits. This is where "compute again and again" used to hurt, and what the cache
  kills.
- **Live:** the cache is read and written the same way. Warmup history,
  earlier-today bars, and post-restart re-warm are all **cache hits**: read,
  never recomputed. The **only** computation in live is the bar that just closed,
  because it never existed before; that is its first-and-only compute, not a
  recompute.

**Invariant:** nothing is ever computed twice. Each bar is computed **exactly
once**, the first time it exists; every later access (across a backtest sweep, or
a live restart) is a cache hit. Keys are explicit and versioned
(`feature_version` / `model_version` bust the cache).

### Consequence for the pipeline ordering

Training cannot stream: it fits on the whole panel. So the first feature access
(by training, or by the first backtest) cold-fills the cache; training reads the
filled panel; the model is trained; backtests and live then read features and
the trained model. No special "materialization pass" exists; it is just the
first cache miss filling as it goes.

### 4. Cache backend: pluggable, dependency-free by default

The *mechanism* of the cache is deliberately left open behind the `Cache` port;
only the *contract* (read-through `get_or_compute`, versioned keys) is fixed.

- **Default = dependency-free.** A simple in-process LRU (already implemented,
  zero new dependencies) for the in-run hot path, plus a file-backed store
  (Parquet or embedded KV) for the durable cross-sweep reuse. This keeps the
  no-server-database architecture for the TCC baseline.
- **Optional performance upgrade.** If profiling later justifies it, *any*
  efficient backend can replace it behind the same port without touching callers:
  in-process, embedded, or a **containerized service** (Redis, Aerospike,
  MongoDB, or whatever profiles best). The project already runs Docker, so a
  containerized cache is cheap to add; it runs **unprivileged** (workstation
  rule). It is **opt-in, never a baseline dependency**.
- A containerized backend, if introduced, brings its `testcontainers` integration
  test in the same development cycle.

Keys are explicit and versioned (`feature_version` / `model_version` bust the
cache). Backend choice is an open item, not a blocker; the port absorbs it.

### 5. Why Parquet is kept for price (the offline consumers)

Price is duplicated into `lean-data/` for replay, but Parquet is kept as the
price source of truth because everything *except* LEAN reads price as columnar
dataframes, and LEAN's zip-CSV format cannot serve those efficiently:

- **model training** (LightGBM over the feature panel, with random access to the
  whole history, not a stream);
- **DuckDB joins** (sentiment↔price minute-join, coverage matrix), one SQL
  query over the partitioned tree, no custom loader;
- **TA-Lib pattern computation** and the **currency-strength** 5th family
  (cross-pair aggregation in polars/DuckDB);
- the **Go/Rust portability** boundary.

Making LEAN-native the canonical price format would re-couple the data layer to
one engine (the very thing rejected above) and is lossy for analytics. So the
direction is: Parquet canonical, `lean-data/` derived.

### Related decision (recorded elsewhere): LEAN runs locally, at no platform cost

The cost complaints associated with the LEAN name concern the QuantConnect
**cloud** platform (hosted backtest/live compute nodes and the subscription Data
Library), not the engine, which is Apache 2.0. This project runs the LEAN engine
**locally** via the LEAN CLI in Docker, fed by data it downloads itself
(Dukascopy, public, no credentials). No QuantConnect subscription, compute node
or hosted dataset is used, so the backtest sweeps incur **no platform cost beyond
local compute**. This is precisely why the storage architecture above is built
around a local, bulk-downloaded store rather than a hosted feed. (Stated in the
monograph, §Execution Engine; recorded here for the review's completeness.)
