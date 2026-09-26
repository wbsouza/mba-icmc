# Spec 08 — News/event data materialization (GDELT + GPR, real 10-year window)

**Tool scope:** `algo-download` → `algo-transform` → `algo-score` (orchestration only —
no new library code in these three tools; they are already built and merged).
**Depends on:** nothing blocking. Specs 01/02/03 are done (code). **Blocks:** Spec 04e
(F4 news-context filter), transitively 04g (meta-learner), 04h (hybrid integration),
06 (Chapter 4 writing).
**Governing contracts:** `algo-download/SPEC.md` §5, `algo-transform/SPEC.md` §5,
`algo-score/SPEC.md` §5 (CLI surfaces — this story invokes them, does not change them).

## Problem Statement

`algo-score`'s code is fully built and tested against fixtures, but its pipeline has
never been *run* against real data. The NAS data root
(`/media/nas/wellington/mba/algo-suite/data`) currently has only `parquet/forex/` —
no sentiment or event Parquet exists. `docs/stories/done/2026-09-26-04e-algo-backtest-news-context-filter/spec.md`
named this exact gap as its blocking precondition (since resolved — the event half is
real+built; see that story's `progress.md`). This story is the operational
runbook that closes it: bulk-materialize GDELT event/sentiment data and the GPR
index for the real 2015-02-19 → 2024-12-31 window, mirroring the idempotent,
resumable, checksum-verified pattern `scripts/prepare-lean-data.sh` already
established for price data.

## Goals

- [ ] GDELT raw payloads, canonical event Parquet, sentiment scores (LM lexicon),
      and event features materialized on the NAS for the full window.
- [ ] GPR raw CSV, canonical event Parquet, and event features materialized on
      the NAS for the full window.
- [ ] `algo-transform coverage` reports both sources active and names the
      resulting training window per the coverage rule
      (`monografia/chapters/03-methodology.tex` §subsec:coverage-rule: largest
      contiguous span with ≥2 corpora active ≥80% of constituent months).
- [ ] A resumable orchestration script (`scripts/prepare-news-data.sh`) exists,
      committed, mirroring `prepare-lean-data.sh`'s idempotency contract.

## Out of Scope

| Item | Reason |
|---|---|
| FinBERT scoring | User decision this session: LM lexicon only for this pass (no GPU-inference budget committed yet); FinBERT is a non-destructive second pass addable later, not a redo. |
| FNSPID / CC-News / Reddit / central-bank / Trump-archive sources | Not yet built in `algo-download` (only `dukascopy`/`gdelt`/`gpr`/`gdelt_ngrams` adapters exist per Spec 01's actual scope). Out of scope for this story. |
| `gdelt_ngrams` source (per-minute HTTP text pull) | **Superseded, not merely deferred** (session of 2026-09-25): the plain `gdelt` adapter's Events data has no article-text field at all, so `algo-score --scorer lm --source gdelt` as originally specified had nothing real to score (`run_lm_scoring`'s own docstring says "synthetic article text" -- confirmed by reading the code, not assumed). Real per-article content now comes from GDELT's **GKG** table (`Quotations`, `Extras`'s `<PAGE_TITLE>`, `V2Themes`, `V2Tone`) via the BigQuery path below -- cheap, no per-minute HTTP fetch, no ~19.4h+ throttle floor. |
| Original `algo-download run --source gdelt` / `algo-transform run --source gdelt` / `algo-score --scorer lm --source gdelt` pipeline for Events | Replaced by the BigQuery CTAS scripts below (session of 2026-09-25). The HTTP path's ≥19.4h throttle-floor estimate (still valid *as a fact about that path*) is why it was replaced, not why it was deferred -- see the Assumptions table. |
| GKG entity/relationship graph analytics (`V2Persons`/`V2Organizations`/`V2Themes`/`V2Locations`/`AllNames` as an in-memory knowledge graph) | Discussed as a follow-on -- GKG is structurally graph-shaped data. Moot for now while GKG ingestion itself is on hold (see next row). |
| **GKG ingestion + events⋈gkg join -- V2 (post-delivery)** (`bigquery_ctas_export_gdelt_gkg.py`, `bigquery_join_gdelt_events_gkg.py`, `scripts/bigquery/gdelt_gkg_ctas.sql`) | **On hold (2026-09-26), operator decision -- not dropped, deferred to a V2 pass after thesis delivery.** Reason: not enough time left before the deadline to produce the GKG artifacts *and* still run the backtest experiments on top of them -- Events-only unblocks the experiments now. Was the "real per-article content" pillar (Assumptions table, superseded row below); V1 (this delivery)'s scope is Events-only. `AvgTone` + `GoldsteinScale` (both already on every Events row) are the GDELT signal for Spec 04e's F4 filter in V1 -- no per-article quotes/themes layer until V2. Tracked as a deferred item in `docs/technical-debt.md` with the unblock trigger. Superseded ACs #3/#4/#6/#7 below are kept, marked on-hold for V2, for traceability rather than deleted (this doc amends, never overwrites). |
| Building/changing `algo-download`/`algo-transform`/`algo-score` source code | All three tools are already built; this story only orchestrates their existing CLIs. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
|---|---|---|---|
| Sentiment/impact signal for GDELT Events | **Superseded (2026-09-25).** `AvgTone` + `GoldsteinScale`, already present on every Events row, are the signal -- both real (GoldsteinScale: a fixed per-event-type weight via CAMEO, not per-article; AvgTone: GDELT's own tone algorithm computed from the actual article text at their end). No LM-lexicon pass needed for Events. | Verified against the code (`run_lm_scoring` had no real text to score for `source=gdelt`) and the actual materialized `events` table's columns | y |
| Real per-article content (beyond numeric tone/impact) | **On hold for V2 (2026-09-26).** GDELT's GKG table (`Quotations`, `Extras`'s `<PAGE_TITLE>`, `V2Themes`, `V2Tone`) via BigQuery, joined to Events on `SOURCEURL = DocumentIdentifier` (empirically verified, many-events-to-one-GKG-row) -- validated live but deferred to a post-delivery V2 pass, not part of V1. Not full article bodies, but real GDELT-extracted quotes/title/themes, when built. | Verified live (2026-09-25): join query against `gdelt-bq.gdeltv2.{events,gkg}` returned real matching rows for a sampled day. Deferred per operator decision given deadline proximity, 2026-09-26 | y |
| Execution timing | **Superseded**: the BigQuery path was actually run this session; the `events` full table is materialized into `mba-ai-509708.gdelt.events` (the `gkg` full table was also materialized this session but its consumption is on hold for V2, see above); local per-date materialization now in progress (see progress.md) | Explicit user decision this session, then revised as the BigQuery path proved fast enough to just do | y |
| GDELT materialization path (V1, this delivery) | **Replaced** `algo-download run --source gdelt` (HTTP, per-15-min-slot) with `bigquery_ctas_export_gdelt_events.py`: a one-time full-window `CREATE TABLE ... AS SELECT *` into `mba-ai-509708.gdelt.events` (reused unconditionally on every rerun -- the public source is scanned exactly once, ever), then a per-calendar-day partition-pruned query against that table, writing/rewriting the canonical monthly Parquet after every day (2026-09-26 amendment below). `bigquery_ctas_export_gdelt_gkg.py` and `bigquery_join_gdelt_events_gkg.py` exist and are code-reviewed but their invocation is on hold for V2 (Out of Scope table above). | Built and code-reviewed this session; the events full table confirmed materialized via live BigQuery console | y |
| GDELT unit scale / download runtime (≥19.4h throttle floor, ~350,000 HTTP units) | **Obsolete** -- described the now-replaced HTTP path. Still factually correct *about that path* (kept for history), but no longer governs this story's actual runtime: the BigQuery full-table materializations took ~1-2 min (Events, 390M rows) and ~15-20 min (GKG, 1.64B rows, heavier text columns), one time only. | Superseded by the BigQuery path above | y |
| `algo-score events --kind <gdelt\|gpr>` per-source flag applicability | Assume both kinds accept the same `[--month/range]` flag shape shown in `algo-score/SPEC.md` §5; no per-kind rejection table was found there (unlike `algo-download`/`algo-transform`'s explicit tables) | `algo-score/SPEC.md` §5 shows one shared signature for `events`, no divergence documented | n — verify against the live `--help` output in Task T1 before the parallel lanes start |
| GPR has no sentiment scoring pass | GPR is a numeric index (not free text), so only `algo-score events --kind gpr` applies to it, never `algo-score --scorer ...` | `algo-score/SPEC.md` §6.1 defines sentiment features as scored from text; GPR is ingested as a pre-computed index per `algo-download/SPEC.md`'s GPR row (whole-window, single file) | y |
| Coverage-rule window lower bound | 2015-02-19 (GDELT 2.0 launch date) | Matches the identical window already used by `docs/stories/in-progress` (now `done`) Spec 05's own spec.md and the methodology chapter's stated coverage rule | y |
| Parallelizing the GDELT download across multiple date-range lanes | 2 contiguous lanes (2015-02..2019-12, 2020-01..2024-12), each its own process, each still governed by `_DEFAULT_MIN_INTERVAL=0.2s` internally — aggregate request rate to GDELT's public server roughly doubles (~10 req/s vs. ~5 req/s single-lane). `data.gdeltproject.org` is a static file bucket, not a fragile origin, so this is treated as acceptable at 2 lanes; the Phase 2 pilot task (T3) is the checkpoint to abort/reduce lane count if GDELT starts rate-limiting or erroring under 2 concurrent lanes | Judgment call, no GDELT rate-limit policy document found — kept conservative (2, not 4+) for that reason | n — confirmed empirically during T3's pilot, not asserted here |

**Open questions:** none left unresolved — the one unconfirmed row above (`algo-score events` flag applicability) is bound to a concrete verification task (T1) before any lane starts, not left as a silent guess.

---

## User Stories

### P1: Materialize GDELT (events + sentiment) ⭐ MVP

**User Story**: As the thesis's data pipeline, I want GDELT Events (numeric tone/impact)
materialized as local Parquet for the full window, so that Spec 04e's F4 filter has a real
per-pair sentiment/impact signal to read instead of a synthetic fixture. (GKG's real
per-article quotes/themes, originally planned as an additional joined signal, is on hold
for V2 -- see Out of Scope table.)

**Why P1**: The one Spec 04e's own spec.md names explicitly. **Approach superseded
(2026-09-25)**: the original `algo-download`/`algo-transform`/`algo-score` HTTP pipeline is
replaced by `bigquery_ctas_export_gdelt_events.py`, run directly (not through those three
tools) for this data source. (GKG + join scripts also exist, code-reviewed, but their
invocation is on hold for V2.)

**Acceptance Criteria**:

1. WHEN `uv run --with google-cloud-bigquery --with google-cloud-storage --with pyarrow python
   scripts/bigquery_ctas_export_gdelt_events.py --project mba-ai-509708 --from 2015-02 --to
   2024-12` completes THEN `mba-ai-509708.gdelt.events` SHALL exist in BigQuery, materialized
   from `gdelt-bq.gdeltv2.events` for the full window exactly once (reused on every later
   invocation -- `_ensure_full_table` checks existence before ever re-scanning the source).
2. WHEN the same script's per-batch loop completes for a batch of months THEN the system SHALL
   have local canonical Events Parquet under `parquet/events/gdelt/.../year=YYYY/month=MM/`
   for every month in that batch, each gated by a `.done` marker written only after its
   Parquet write succeeds (never raw-file existence alone).
3. **On hold for V2 (2026-09-26).** Was: WHEN `bigquery_ctas_export_gdelt_gkg.py` completes
   THEN `mba-ai-509708.gdelt.gkg` SHALL exist, materialized from `gdelt-bq.gdeltv2.gkg` for
   the full window exactly once, with local exploratory GKG Parquet under
   `<data_root>/gdelt_gkg/year=YYYY/month=MM/data.parquet`. Script exists, code-reviewed, not
   invoked in V1.
4. **On hold for V2 (2026-09-26).** Was: WHEN `bigquery_join_gdelt_events_gkg.py` completes
   THEN the system SHALL have one joined Parquet file per calendar day under
   `<data_root>/gdelt_joined/year=YYYY/month=MM/<YYYY-MM-DD>.parquet`, ledgered in
   `.processed_dates`. Script exists, code-reviewed, not invoked in V1.
5. IF `{project}.{dataset}.events` already exists in BigQuery THEN the script SHALL reuse it
   unconditionally and SHALL NOT re-scan/re-bill the public source table, no matter how many
   times the script is invoked, killed, or retried. (`.gkg`'s equivalent reuse contract is
   unaffected but not exercised in V1 -- see AC#3.)
6. **On hold for V2 (2026-09-26).** Was: IF a day is already listed in `.processed_dates`
   THEN `bigquery_join_gdelt_events_gkg.py` SHALL skip it without querying BigQuery, unless
   `--rebuild` is passed. Not exercised in V1 -- see AC#4.
7. **On hold for V2 (2026-09-26).** Was: IF two instances of `bigquery_join_gdelt_events_gkg.py`
   are launched against the same `data_root` THEN the second SHALL block on the first's
   `flock`. Not exercised in V1 -- see AC#4.
8. **Superseded for events (2026-09-26 amendment below); on hold for GKG (V2).** GCS
   batch/export shard cleanup no longer exists in the events path at all (per-date direct
   query replaced it). For GKG, the original requirement stands whenever V2 resumes: IF a
   batch's GCS export shards from a killed prior attempt are present THEN the script SHALL
   delete them before exporting again.

**Amendment (2026-09-26):** `bigquery_ctas_export_gdelt_events.py`'s AC#2/#8 (month-batch +
GCS export/download/repartition, with stale-shard cleanup) is **superseded**, per explicit
operator decision this session. The one-time full-table CTAS (AC#1) already partitions
`{project}.{dataset}.events` by `event_date` -- paid for specifically so later reads could
be cheap, partition-pruned queries. Per-batch GCS staging was built for the (now-replaced)
unpartitioned-scan bottleneck, not for reading our own already-partitioned table. The
script now queries that table **per calendar day** (`WHERE event_date = ...`,
partition-pruned, cheap regardless of window width) directly via `job.result()`,
accumulates a month's days, then writes the canonical monthly Parquet + `.done` marker
exactly as before. No GCS bucket, export job, or shard cleanup exists in this path anymore
-- AC#8 no longer applies to this script (`bigquery_ctas_export_gdelt_gkg.py` is
unaffected by this amendment). Rationale: real-time per-date operator visibility instead
of a silent up-to-12-month wait, at no added bytes-billed cost since partition pruning was
already why the per-batch query was cheap.

**Independent Test (V1, events-only)**: Run `bigquery_ctas_export_gdelt_events.py` alone
against a single pilot month (`--from 2020-01 --to 2020-01`); confirm `day_written` log lines
appear for every date in that month, `parquet/events/gdelt/year=2020/month=01/data.parquet`
exists and grows across those log lines, and `.done` is written only once the month completes.

---

### P1: Materialize GPR (index + event features) ⭐ MVP

**User Story**: As the thesis's data pipeline, I want the GPR index and its event
features materialized for the full window, so that the coverage rule's "≥2 corpora
active" condition is met and F4 has the continuous risk-regime signal the
methodology names alongside GDELT.

**Why P1**: Small, fast, independent of the GDELT lane — the natural parallel
counterpart.

**Acceptance Criteria**:

1. WHEN `algo-download run --source gpr` completes THEN the system SHALL have the
   single whole-window GPR CSV on disk with a verified sha256 sidecar.
2. WHEN `algo-transform run --source gpr` completes THEN the system SHALL have
   canonical GPR event Parquet on disk.
3. WHEN `algo-score events --kind gpr` completes THEN the system SHALL have
   event-feature Parquet under `parquet/events/gpr/...`.
4. IF the GPR CSV already exists with a matching sha256 sidecar THEN the system
   SHALL skip re-downloading it.

**Independent Test**: Run the GPR lane alone; confirm all three artifacts exist and
`algo-transform coverage` reports GPR active for the full window in one pass (GPR is
whole-window, not month-partitioned on the download side).

---

### P2: Orchestration script

**User Story**: As the operator (Wellington), I want one resumable script covering
both lanes, so that a future run is `nohup scripts/prepare-news-data.sh > ... &`,
identical in shape to last night's price backfill, not four manually-typed CLI
invocations per lane.

**Why P2**: Convenience + consistency with the established operational pattern —
not required for the data to exist (the lanes work via direct CLI calls even
without it), but required for the story's own definition of done and for a
repeatable overnight run.

**Acceptance Criteria**:

1. The system SHALL provide `scripts/prepare-news-data.sh` with two independently
   invocable stages/functions, one per lane (`gdelt`, `gpr`), mirroring
   `prepare-lean-data.sh`'s `SYMBOLS`/`FROM`/`TO`/`VERIFY_ONLY` override
   convention (here: `SOURCES`, `FROM`, `TO`, `VERIFY_ONLY`).
2. WHILE a lane's stage runs THE system SHALL stream each unit's outcome live
   (tee-to-tempfile pattern, per the fix already landed in `prepare-lean-data.sh`
   this session) rather than buffering silently across a very long GDELT run.
3. THE system SHALL default `SOURCES` to `"gdelt gpr"` and the window to
   `2015-02..2024-12`.
4. IF a stage is invoked with `VERIFY_ONLY=1` THEN the system SHALL check existing
   sha256 sidecars without writing/fetching anything.

**Independent Test**: `bash -n scripts/prepare-news-data.sh` (syntax check) plus
`VERIFY_ONLY=1 SOURCES=gpr scripts/prepare-news-data.sh` against an empty/partial
data root exits 0 and reports nothing-to-verify without touching the network.

---

## Edge Cases

- IF the NAS mount is unavailable when a lane starts THEN the system SHALL fail
  fast naming the missing mount path, not silently write to a local fallback.
- IF GDELT's public feed rate-limits or 5xxs mid-run THEN the underlying adapter's
  existing internal retry/backoff (per `algo-download/SPEC.md` §5) handles it;
  this story's script does not add a second retry layer on top.
- WHEN the GDELT lane is interrupted (Ctrl-C, workstation reboot) THEN a re-run
  SHALL resume from the last verified unit, not restart the ~350,000-unit window
  from scratch.

## Reproducibility

What a reader would need to redo this materialization from scratch, verbatim (added
2026-09-25 per explicit request).

**1. One-time full-window materialization, Events (V1)** (checked in at `scripts/bigquery/`;
`CREATE TABLE` -- not `REPLACE` -- so a second attempt after the table exists is a no-op):

```sql
-- scripts/bigquery/gdelt_events_ctas.sql
CREATE TABLE `mba-ai-509708.gdelt.events` AS
SELECT * FROM `gdelt-bq.gdeltv2.events`
WHERE SQLDATE BETWEEN 20150201 AND 20241231
```

`scripts/bigquery/gdelt_gkg_ctas.sql` (GKG's equivalent) exists but is on hold for V2 -- see
Out of Scope table.

**2. Per-day query against the events table** (`scripts/bigquery_ctas_export_gdelt_events.py`,
2026-09-26 amendment below): one partition-pruned `SELECT ... WHERE event_date = ...` per
calendar day, writing/rewriting that month's canonical Parquet after every day.

GKG's per-day join (`bigquery_join_gdelt_events_gkg.py`, join key
`events.SOURCEURL = gkg.DocumentIdentifier`, empirically verified 2026-09-25) exists and is
code-reviewed but is on hold for V2, not run in this delivery.

**3. What's stable vs. what can drift on a rerun**: GDELT's historical days (anything not
within the last few days of ingestion) are effectively immutable once published, so re-running
the exact query above for the same `SQLDATE` window reproduces the same row set for any date
safely in the past. Very recent days (near GDELT's live ingestion edge) can still receive
corrections/backfill in the hours after publication -- avoid citing exact row counts for the
most recent few days as if they were final.

**4. Software provenance**: `scripts/bigquery_ctas_export_gdelt_events.py` (V1, in use),
`scripts/bigquery_ctas_export_gdelt_gkg.py`, `scripts/bigquery_join_gdelt_events_gkg.py` (V2,
on hold), all under version control in this repo.

## Requirement Traceability

| Requirement ID | Story | Status |
|---|---|---|
| NEWS-01 .. NEWS-06 | P1: Materialize GDELT | Pending |
| NEWS-07 .. NEWS-10 | P1: Materialize GPR | Pending |
| NEWS-11 .. NEWS-14 | P2: Orchestration script | Pending |

**Coverage:** 14 total, all mapped to Phase 2/3 tasks in `tasks.md`. NEWS-01..06 (Materialize
GDELT) includes AC#3/#4/#6/#7 (GKG ingestion + join), on hold for V2 as of 2026-09-26 -- see
Out of Scope table and `docs/technical-debt.md`.

## Success Criteria

- [ ] `algo-transform coverage` reports both GDELT and GPR active across the full
      window, with the resulting training window printed (coverage-rule output).
- [ ] `scripts/prepare-news-data.sh` committed, `bash -n` clean.
- [ ] Spec 04e's own spec.md precondition ("confirm Spec 03's sentiment/event
      Parquet is actually present on the NAS data root") is satisfiable by pointing
      at this story's output.
