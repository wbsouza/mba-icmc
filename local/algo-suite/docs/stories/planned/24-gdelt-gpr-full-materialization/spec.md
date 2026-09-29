# Story 24 — GDELT/GPR full materialization and coverage rule

Status: planned. Continuation of Story 08 (news/event data materialization),
closed 2026-09-28 for what it actually delivered: the GDELT Events pipeline
proven end to end via BigQuery CTAS, with real feature data built and
successfully consumed by real backtests over the registered study window
(2016-03-01 to 2017-02-28). See `../../done/08-news-event-data-materialization/progress.md`
for exactly what that story closed with and why.

## Problem statement

Story 08 proved the pipeline works for one registered window. It did not
complete the original full scope: the 10-year GDELT backfill, GPR (raw
download exists, no canonical/feature layer), the GKG/join tables (on hold
for a future V2), the coverage-rule empirical validation (the 80% threshold
in `specs.md`/the methodology chapter has no documented provenance), and the
`prepare-news-data.sh` script's `VERIFY_ONLY` mode (P2 AC#4).

## Goals

- [ ] Complete the GDELT Events backfill across the full available window
      (2015-02 through the latest complete month), not just the registered
      study window.
- [ ] Build GPR's canonical Parquet and event-feature layer (currently only
      the raw `.xls` download exists, no sha256 sidecar either).
- [ ] Empirically justify (or replace) the 80%-coverage-rule threshold with
      real provenance, not an unvalidated constant.
- [ ] Add `VERIFY_ONLY` mode to `prepare-news-data.sh` (P2 AC#4).
- [ ] Decide whether GKG/entity-relationship graph analytics (V2) is in scope
      for this continuation or deferred again.

## Out of scope

- Everything already proven working by Story 08 (GDELT Events for the
  registered window, the `available_at` provenance fix, PR #95/#96) — this
  story only picks up what Story 08 explicitly left unfinished.

## Notes

Wellington is running the `available_at` backfill himself (`backfill_gdelt_available_at.py`,
PR #96) across the full local data range (2015-02 to 2018-04) as of 2026-09-28;
that work is a prerequisite/overlaps with this story's full-backfill goal and
should be checked before restarting anything here.
