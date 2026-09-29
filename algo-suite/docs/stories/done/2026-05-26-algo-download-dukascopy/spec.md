# algo-download — Dukascopy price adapter (pre-existing, not yesterday's work)

**Tool:** `algo-suite/algo-download/` · **Status:** done · **Last commit
before 2026-09-22:** `aec37c2`, 2026-05-26 ("download: log progress per day,
not per hour — too noisy"). **Built:** 2026-05-25, commit `a34de91`
("algo-download: slice 1 (Dukascopy) — raw bi5 over HTTP, resilient +
validated"), committed directly to `master` (no PR).

This is separate from `../2026-09-22-algo-download-news-sources/` (the GDELT
+ GPR raw adapters swarmforge built yesterday). Dukascopy was already built
and working nearly four months before that session; the session never
touched it.

**Scope (from the original spec, `docs/specs/algo-download.md`, relocated
into [`algo-suite/algo-download/SPEC.md`](../../../../algo-download/SPEC.md) at `50c537e`):** bulk retrieval of
raw price payloads (Dukascopy `.bi5` tick files over HTTP), resilient
fetch/retry, resumable via filesystem-only `is_done()` checks, `DataSource`
ABC (`plan`/`is_done`/`fetch`) that later GDELT/GPR adapters mirrored.

See [`algo-suite/algo-download/SPEC.md`](../../../../algo-download/SPEC.md) for the current, living contract.
