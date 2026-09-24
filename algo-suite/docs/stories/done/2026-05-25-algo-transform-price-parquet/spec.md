# algo-transform — bi5 → minute QuoteBar Parquet (pre-existing, not yesterday's work)

**Tool:** `algo-suite/algo-transform/` · **Status:** done · **Last commit
before 2026-09-22:** `7f84f0c`, 2026-05-25 (repo-wide American-English
spelling pass, cosmetic only). **Substantive build commits, same day
2026-05-25:** `d4a92ab` ("slice 1 — Dukascopy .bi5 decoder, raw bytes →
validated ticks"), `9015566` ("slice 2 — raw .bi5 → minute QuoteBar Parquet,
runnable"), `d670163` ("MT5 timeframes + multi-timeframe; close TD-4/TD-7").

This is separate from `../2026-09-22-algo-transform-news-events/` (the
GDELT/GPR event decode + coverage matrix swarmforge built yesterday). The
price-side decode/transform pipeline was already built and working nearly
four months earlier; the session never touched it.

**Scope (from the original spec, `docs/specs/algo-transform.md`, relocated
into [`algo-suite/algo-transform/SPEC.md`](../../../../algo-transform/SPEC.md) at `50c537e`):** the second
pipeline stage — reads provider-native raw price payloads, decodes Dukascopy
`.bi5` ticks, aggregates to minute `QuoteBar` Parquet, and supports multiple
MT5 timeframes.

See [`algo-suite/algo-transform/SPEC.md`](../../../../algo-transform/SPEC.md) for the current, living contract.
