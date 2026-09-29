# Spec 01 — algo-download: GDELT + GPR raw adapters

**Tool:** `algo-suite/algo-download/` · **Status:** done (2026-09-22, see
`lessons-learned.md`) · **Blocks:** Spec 02
**Depends on:** nothing — can start immediately, in parallel with Spec 05.

**Scope note:** this spec covers only the GDELT + GPR raw adapters, built
2026-09-22. It does not cover the Dukascopy price adapter ("slice 1"), which
is separate, prior work committed directly to `master` on 2026-05-25
(`a34de91`, no PR) and last touched (progress-logging polish) on 2026-05-26
(`aec37c2`/`2f86107`) — that piece was already built and working nearly four
months before this story started. `master` itself then went quiet on code
entirely (only monografia prose commits) until this session resumed on
2026-09-22; the swarmforge run did not modify or restart the Dukascopy
adapter, only added GDELT/GPR alongside it. Dukascopy's original spec lived
at `docs/specs/algo-download.md`; that file was relocated (not lost) into
[`algo-suite/algo-download/SPEC.md`](../../../../algo-download/SPEC.md) in the same commit (`50c537e`,
2026-05-25) that established the "spec colocated with its tool" convention
this repo still uses.
**Governing contract:** [`algo-suite/algo-download/SPEC.md`](../../../../algo-download/SPEC.md) (read this fully first
— this spec file tells you *what to build now and why it's next*, the tool
SPEC.md tells you the *contract* your code must satisfy: the `DataSource` ABC,
`UnitStatus`/`DownloadUnit`/`UnitResult`, the raw-only stage boundary, the
resume-is-filesystem-only rule).

## 1. Objective

Add two new self-registering adapters behind the existing `DataSource` port,
exactly as `dukascopy` (slice 1) already does:

1. **`gdelt`** — GDELT 2.0 event/news raw files, 2015-02-19 → present.
2. **`gpr`** — the Geopolitical Risk index (Caldara & Iacoviello), single file,
   full window.

Both write **raw payloads only** to `raw/{source}/...`. No parsing, no Parquet —
that is Spec 02's job (`algo-transform`). If you catch yourself decoding a
GDELT CSV or computing anything from GPR values, stop: that belongs in
`algo-transform`, not here.

## 2. Why this is next

[`PRD.md`](../../../../PRD.md) §6 gantt: this was the planned next item in the original Full-scope
plan (`algo-download GDELT + GPR news`) and remains the critical-path entry
point for the hybrid work whenever it resumes — every later spec (transform,
score, hybrid backtest, Chapter 4 hybrid results) is blocked on this landing
first. **As of 2026-09-22, this spec is deferred, not active**: the monografia
deposit deadline is 2026-09-29, scope froze at Medium (see [`00-PLAN.md`](../../00-PLAN.md)), and
this spec's own build order (§2) plus Spec 03's 16-day budget make it
infeasible before then. Pick this spec back up post-submission.

## 3. `gdelt` adapter

### 3.1 What GDELT is, concretely

GDELT 2.0 publishes update files every 15 minutes at a stable, documented HTTP
location (`http://data.gdeltproject.org/gdeltv2/<YYYYMMDDHHMMSS>.export.CSV.zip`
for the events table; `.gkg.csv.zip` for the Global Knowledge Graph — confirm
which table(s) `algo-transform` Spec 02 actually needs before committing to
fetching both, to avoid downloading data nobody consumes). One "unit" in this
adapter's terms is one 15-minute slot file, per the tool SPEC.md §2 example
(`GDELT = one 15-minute slot file`).

### 3.2 What to reuse from `reference-impl/`

`algo-suite/algo-download/reference-impl/` (the parked legacy `news-downloader`)
has a working GDELT master-file index and URL patterns — mine it **only for
source-specific facts** (URL shape, file cadence, master-list mechanism, date
bounds of GDELT 2.0 coverage). Per the tool SPEC.md §9 and [`technical-debt.md`](../../../technical-debt.md)
TD-12: do **not** port its code or its abstractions (it violates the raw-only
stage boundary — it downloads, extracts, converts to Parquet and deletes raw
intermediates in one object). Write the adapter fresh against the `DataSource`
ABC. Once this spec lands, delete `reference-impl/` (TD-12's trigger — "the
GDELT download slice starts" — is met by this spec).

### 3.3 Adapter shape

Mirror `algo_download/adapters/dukascopy/` exactly:
```
algo_download/adapters/gdelt/
├── __init__.py
├── paths.py     # URL builder (master-file index or direct 15-min slot URL) + raw-path builder
└── source.py    # GdeltDataSource(DataSource): plan/is_done/fetch
```
Register it with one import line in `algo_download/adapters/__init__.py`, no
edits to `dukascopy/`.

- `plan(request)` yields one `DownloadUnit` per 15-minute slot in the requested
  span — no I/O, no network (so `--dry-run` works for free, same as Dukascopy).
- `is_done()` — filesystem-only, `raw_path.exists()` (default from the ABC is
  fine unless GDELT needs multi-file units, e.g. events + GKG per slot).
- `fetch()` — HTTP GET the zip, write **raw bytes verbatim**. Concurrency and
  retry/backoff live inside this adapter (the orchestrator stays
  source-agnostic), same pattern as Dukascopy's `min_interval` politeness
  throttle — GDELT is a public academic feed, be a good citizen, add an
  equivalent `ALGO_GDELT_MIN_INTERVAL`.
- A slot with no update (GDELT sometimes skips a 15-min tick) → `MISSING`,
  persisted as a durable empty marker, never `FAILED`. A genuine HTTP failure
  after retries → `FAILED`, nothing written, retried next run. This is the same
  `MISSING` vs `FAILED` distinction the tool SPEC.md draws for Dukascopy
  weekend gaps — do not conflate them.

### 3.4 Real-feed validation (do this before writing the BDD suite)

Per the tool SPEC.md §7a precedent (Dukascopy's URL/payload shape was confirmed
by one real fetch before the mocked test suite was written) — do the same for
GDELT: one real, manual fetch to confirm the exact URL pattern, whether a
master-file list is required or slot URLs are directly guessable from
timestamp, and the zip's internal structure. Record findings in a `§7a`-style
section of the tool SPEC.md. Then write the offline, mocked BDD suite (the
Dukascopy pattern: `respx` or equivalent, no live network in `make check`).
Mark the real-feed confirmation test `@pytest.mark.network`, excluded from the
gate, reproducible via `uv run pytest -m network`.

## 4. `gpr` adapter

Much simpler: single file, full window, no per-month partitioning question.

- Source: Caldara & Iacoviello's published GPR index (already cited in
  `specs.md` §13.2/§13.3 as `caldara2022geopolitical` — confirm the canonical
  download URL from the authors' own site, not a mirror).
- `plan()` yields exactly one `DownloadUnit`.
- `fetch()` GETs the file, writes it raw under `raw/gpr/...`.
- No retry-storm risk (one file, one fetch) but still atomic-write (temp +
  `os.replace`) per the tool's general convention.
- Since it's one file covering the whole window, there's no meaningful
  `--month`/`--from`/`--to` slicing — the CLI surface should make that
  explicit rather than silently ignoring date flags (fail fast: if the
  operator passes `--month` to `--source gpr`, either it's a documented no-op
  or a hard error — pick the one that matches the CLI's existing UX for
  single-unit sources, and say so in the SPEC.md CLI surface table).

## 5. Test requirements

Every scenario is Gherkin/pytest-bdd (`tests/features/gdelt.feature`,
`tests/features/gpr.feature`, steps in `tests/steps/`). Mirror the shape of the
existing Dukascopy feature file section in the tool SPEC.md §7 — happy path,
resume-is-filesystem-no-op, provider-no-data-is-MISSING-not-FAILED,
failed-fetch-writes-nothing-and-exits-nonzero, dry-run-plans-without-I/O. Add
GDELT-specific: a 15-min slot with no update is `MISSING`; a slot download that
times out after retries is `FAILED`. Add GPR-specific: single-unit plan; the
whole-window semantics.

## 6. Definition of done

- `algo-download run --source gdelt --from 2015-02 --to 2024-12` (dry-run and
  real) works exactly like the Dukascopy command shape.
- `algo-download run --source gpr` fetches the one file.
- Raw payloads land at `raw/gdelt/...` and `raw/gpr/...` — nothing parsed,
  nothing written outside `raw/`.
- Offline BDD suite green, no live network in `make check`; one `@network`
  smoke test per source, opt-in.
- `make check` and `make audit` green.
- Tool SPEC.md §1 slice table updated (gdelt/gpr move from "planned" to
  "done"); §7a gets the GDELT real-feed findings.
- `reference-impl/` deleted; `technical-debt.md` TD-12 moved to Resolved with
  today's date.
- `00-PLAN.md` §1 state table updated; Spec 02 unblocked.
