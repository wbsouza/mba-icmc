# algo-download

Bulk-downloads historical data from each source into the raw store. Pipeline
step 1 (with `algo-transform`): **download** → transform → score → backtest →
analyze.

## What it does

- Self-registering **registry + factory adapters**, one per source, each adapting
  an external feed to a single `DataSource` port. **Delivered in slices**: (1)
  Dukascopy prices now; (2) GDELT events; (3) the GPR index; (4) GDELT Web
  News NGrams article-text source; yfinance daily fallback last (resilience
  only).
- Writes original payloads under `raw/<source>/...` and **nothing else** — no
  parsing, extraction, or Parquet (that is `algo-transform`'s job).
- **Source-owned units, normalized status.** The orchestrator deals only in a
  source's own `DownloadUnit` and a normalized `UnitStatus`
  (`WRITTEN/SKIPPED/MISSING/FAILED`); it never assumes a `(symbol, year, month)`
  shape.
- **Filesystem-only resume** — re-running skips units already on disk. There is
  **no machine-managed state**: provider no-data is persisted as the provider's
  own (empty) payload (so it `SKIP`s next run); a failed fetch leaves nothing (so
  it retries). Fail-fast: never fabricate, never hide a failure.

## Inputs and outputs

| Direction | Item |
|---|---|
| In | public source feeds (Dukascopy needs no credentials) + CLI args |
| Out | `raw/<source>/...` under the data root (provider-native bytes) |

## CLI

```bash
uv run algo-download --help
# slice 1: algo-download run --source dukascopy --symbol EURUSD --month 2020-01 [--dry-run]
```

## Config

Optional and **read-only**. With none, convention defaults apply (symbols/span
from the CLI). File/env layering (`conf/`) exists in `algo-core` (TD-3) but is not
used by this tool yet; this tool never mutates operator config.

## Status

**Slices 1–4 (Dukascopy, GDELT, GPR, GDELT NGrams) are implemented, gated,
hardened, and validated against their real feeds.** Port (`source.py`) + registry
(`registry.py`, fail-fast on a clashing name) + synchronous orchestrator
(contains any unexpected unit error as FAILED) + provider adapters that write
raw bytes only. Resilience: transient failures (network, **429**, 5xx) retried
with backoff, other non-2xx → FAILED (no crash); **politeness throttles** for
bulk feeds (`ALGO_DUKASCOPY_MIN_INTERVAL`, `ALGO_GDELT_MIN_INTERVAL`,
`ALGO_GDELT_NGRAMS_MIN_INTERVAL`, all default 0.2s); **atomic writes** so an
interrupted bulk run resumes cleanly. The
offline Gherkin suite covers raw paths, resume, MISSING-vs-FAILED, dry-run, and
source-specific CLI validation; opt-in `@pytest.mark.network` smoke tests
confirm the live feed assumptions. The legacy GDELT `reference-impl/` scaffold
was removed when the fresh raw GDELT adapter landed (TD-12). The yfinance
fallback remains future work.

Spec: [`SPEC.md`](SPEC.md).
