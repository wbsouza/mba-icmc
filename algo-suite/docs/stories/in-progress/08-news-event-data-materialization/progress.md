# Progress — Spec 08 (news/event data materialization)

Approach superseded 2026-09-25: GDELT Events/GKG now materialized via BigQuery
(one-time full-table CTAS + cheap per-batch/day extraction), not the original
`algo-download`/`algo-transform`/`algo-score` HTTP pipeline. See `spec.md`'s
Assumptions table and Reproducibility section for the full reasoning.

PR #24 (opened earlier the same session, captured an intermediate state of
this work) was closed without merging — superseded by everything below.

## Status snapshot — 2026-09-26 (checked on the NAS data root, not assumed)

Checked by listing `/media/nas/wellington/mba/algo-suite/data` directly at 2026-09-26 17:30 PDT.
**Partial:** the GDELT Events lane is running. GPR, the coverage rule, and the P2
`VERIFY_ONLY` contract are not done.

| Item (spec AC) | State |
|---|---|
| GDELT P1 AC#1 (`gdelt.events` CTAS) | done (see BigQuery state below) |
| GDELT P1 AC#2 (local canonical Events Parquet + `.done`) | **partial.** `parquet/events/gdelt/year=2015/month=02..07` each have `data.parquet` + `.done`. `month=08` has `data.parquet` but no `.done` yet (last written 03:22). `year=2020/month=01` is done (pilot). The other 2015-08..2024-12 months are not materialized yet; the backfill continues per TD-56 |
| GDELT event features (`algo-score events --kind gdelt`) | **partial.** `parquet/events/_features/gdelt/` has only `year=2015/month=02` and `year=2020/month=01`. The Spec 04h RUNBOOK's hybrid example (2015-02..2016-01) needs every touched month built first |
| GDELT P1 AC#3/#4/#6/#7 (GKG + join) | on hold for V2 (spec Out of Scope). Not run |
| GPR P1 AC#1 (raw download) | **partial.** `raw/gpr/data_gpr_export.xls` exists (2026-09-25 19:00). No sha256 sidecar is present next to it |
| GPR P1 AC#2/#3 (canonical + event features) | **not done.** No `parquet/gpr/` and no `parquet/events/gpr/` |
| Coverage rule (success criterion #1) | **not met.** `parquet/_meta/coverage.parquet` (2026-09-26 03:38) has GDELT rows only, all with `units_present=0`. It counts the old HTTP raw units, not the BigQuery-path Parquet, and has no GPR rows. It does not yet report a training window |
| P2 `scripts/prepare-news-data.sh` | **mostly done.** Committed (`a0502d8`, updated `c096403`/`1d823d3`), `bash -n` clean, has an flock guard and the `SOURCES`/`FROM`/`TO` overrides. **Missing: P2 AC#4 `VERIFY_ONLY`.** The script has no such mode. Default `TO` is `today`, not `2024-12` (P2 AC#3 drift) |

Sections below are the 2026-09-25 working log. Items the table above contradicts are
superseded by it.

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
- [ ] ~~**None of the three scripts above have actually been run yet.**~~
      *Superseded 2026-09-26:* the Events script has run. 2015-02..07 and
      2020-01 are done and 2015-08 is in progress (see the status snapshot above).
      The GKG and join scripts are on hold for V2 and have not been run.
- [x] `scripts/prepare-news-data.sh` — orchestration wrapper. *Rebuilt and
      committed 2026-09-25* (`a0502d8`). It wraps the Events script, GPR, and event
      features, with an flock guard. It still lacks `VERIFY_ONLY` (P2 AC#4).

## GPR

- [ ] Raw download only (2026-09-26 check): `raw/gpr/data_gpr_export.xls` is on
      the NAS, with no sha256 sidecar. `algo-transform run --source gpr` and
      `algo-score events --kind gpr` have not produced output yet.

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
