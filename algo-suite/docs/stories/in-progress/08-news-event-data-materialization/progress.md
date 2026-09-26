# Progress — Spec 08 (news/event data materialization)

Approach superseded 2026-09-25: GDELT Events/GKG now materialized via BigQuery
(one-time full-table CTAS + cheap per-batch/day extraction), not the original
`algo-download`/`algo-transform`/`algo-score` HTTP pipeline. See `spec.md`'s
Assumptions table and Reproducibility section for the full reasoning.

PR #24 (opened earlier the same session, captured an intermediate state of
this work) was closed without merging — superseded by everything below.

## BigQuery state (permanent, already done)

- [x] `mba-ai-509708.gdelt.events` — materialized (`CREATE TABLE ... SELECT *`,
      full 2015-02..2024-12 window). Confirmed via live BigQuery console.
- [x] `mba-ai-509708.gdelt.gkg` — materialized, same window. Confirmed via
      live BigQuery console.
- These are permanent; never re-scan the public source again regardless of
  how many times the local-materialization scripts below are run or killed.

## Local materialization scripts (code done, not yet run)

- [x] `scripts/bigquery_ctas_export_gdelt_events.py` — one-time full-table
      CTAS + per-batch local Parquet materializer. `py_compile` clean,
      code-reviewed.
- [x] `scripts/bigquery_ctas_export_gdelt_gkg.py` — same pattern for GKG
      (non-canonical output, `gdelt_gkg/`). `py_compile` clean, code-reviewed.
- [x] `scripts/bigquery_join_gdelt_events_gkg.py` — day-granularity
      Events↔GKG join (`SOURCEURL = DocumentIdentifier`), `.processed_dates`
      ledger, flock guard. `py_compile` clean.
- [x] `scripts/bigquery/gdelt_events_ctas.sql`, `gdelt_gkg_ctas.sql` —
      checked-in reference copies of the queries actually run in console.
- [ ] **None of the three scripts above have actually been run yet.** No
      local Parquet exists under `parquet/events/gdelt/`, `gdelt_gkg/`, or
      `gdelt_joined/` from this session's BigQuery path.
- [ ] `scripts/prepare-news-data.sh` — orchestration wrapper tying the three
      BigQuery scripts + GPR + event features into one command. Not yet
      rebuilt (was deleted in a scoped reset this session along with the
      rest of the pre-rebuild GDELT artifacts).

## GPR

- [ ] Not started at all — original `algo-download`/`algo-transform`/
      `algo-score` pipeline, unaffected by today's GDELT changes, still
      needs to actually run.

## Price backfill (separate track, unaffected by this story)

- `scripts/prepare-lean-data.sh` — hardened this session: flock guard,
  fail-fast mount check (aborts if the NAS mount can't guarantee locking
  instead of silently trusting a broken one), checksum sidecars on by
  default (`CHECKSUM=1`), PID-scoped tmp filenames in `leandata.py` fixing
  a genuine concurrent-write race. All code-reviewed. Status of the actual
  backfill run itself: not confirmed as of this update — check
  `pgrep -af "prepare-lean-data\|algo-backtest materialize"` before
  assuming it's still running or already done.

## Known bugs fixed this session (all in the data pipeline, not this story's scope directly)

- `leandata.py`: `write_lean_minute`'s tmp filename had no unique suffix —
  two concurrent `materialize` processes on the same day raced on the same
  tmp path. Fixed: PID-suffixed.
- `prepare-lean-data.sh`: no concurrency guard at all — multiple manual
  launches from the same terminal corrupted a run's log and could
  duplicate-write lean-data zips. Fixed: flock, plus a fail-fast check that
  the lock's underlying mount can actually enforce it (not just silently
  trust CIFS/NFS options that might not honor byte-range locks).
- BigQuery GCS export: a killed batch's leftover shards under a
  deterministic prefix could get mixed into a retried batch's download,
  duplicating rows. Fixed: self-clean the batch's GCS prefix before every
  export attempt.

**TD-56 (2026-09-26):** operator decision — don't wait for the full 10-year backfill;
`2015-02`→`2015-07` (~6 months) is judged sufficient to start real Chapter-4 experiments now,
backfill continues in background. See `docs/technical-debt.md` TD-56.

## Next concrete steps (in order)

1. Run `bigquery_ctas_export_gdelt_events.py` for the full window (or a
   pilot month first) — produces the local canonical Events Parquet.
2. Run `bigquery_ctas_export_gdelt_gkg.py` similarly.
3. Run `bigquery_join_gdelt_events_gkg.py` for the full window.
4. Rebuild `scripts/prepare-news-data.sh` to wrap 1-3 + GPR + event features
   into one command, with its own flock guard.
5. Run `algo-score events --kind gdelt` against whatever local Events
   Parquet exists, to prove the feature layer (not just raw acquisition)
   actually works end to end.
6. Start GPR (currently fully untouched).
7. `algo-transform coverage` once both sources have real data, to get the
   actual coverage-rule training window.

## Known-not-done, deliberately deferred

- The 80%-coverage-rule threshold in `spec.md`/the methodology chapter has
  no documented provenance; flagged in the monograph as an experimental
  value subject to adjustment, not yet empirically justified.
- GKG entity/relationship graph analytics (loading `V2Persons`/
  `V2Organizations`/`V2Themes` into an actual knowledge-graph structure) —
  discussed as a follow-on, not started.
- `.worktrees/*` duplicate-repo cleanup — flagged earlier this session,
  explicitly deferred, not touched.
