# Spec 02 — algo-transform: GDELT/GPR raw → canonical Parquet + coverage matrix

**Tool:** `algo-suite/algo-transform/` · **Status:** built by coder
2026-09-23 (GDELT/GPR event Parquet + coverage matrix) ·
**Blocks:** Spec 03
**Depends on:** Spec 01's real-feed validation (`algo-download/SPEC.md`
§7a.1/§7a.2, read directly off branch `spec-01-algo-download-gdelt-gpr`, not
yet merged to master) — sufficient to specify against; does not require Spec
01's adapter code to be merged first.
**Governing contract:** `algo-suite/algo-transform/SPEC.md` §"slice 3" (event
datasets, `parquet/events/{gdelt,gpr}/...`, `gdelt.py`/`gpr.py` decoders under
`algo_transform/decoders/`).

**Resolved 2026-09-22 (specifier):** `parquet/news/gdelt/...` is **not**
written — `algo-download`'s confirmed GDELT scope (Events table only) has no
article-text field, only `SOURCEURL`. This tool writes `parquet/events/gdelt/`
and `parquet/events/gpr/` only, mirroring the raw source's own facts (§2/§3
below, unchanged from the original task text, stay as historical scoping
questions this answers). The text-sentiment gap this leaves for `algo-score`
is tracked as `technical-debt.md` TD-28 (GDELT Web News NGrams 3.0), not this
tool's job to close. Currency-strength (§3) confirmed unconsumed by any
F1–F7 filter — deferred as TD-29.

## 1. Objective

Decode the raw GDELT and GPR payloads Spec 01 fetched into the canonical,
partitioned Parquet contract that `algo-score` (Spec 03) reads from. Also build
the **data-coverage matrix** — the artifact that drives the empirical training
window decision (`PRD.md` §4, `specs.md` §3.2) and becomes a Chapter 4 figure
(`algo-suite/docs/experiments.md` §3, "Data-coverage matrix").

This mirrors what `algo-transform` already did for Dukascopy (slice 1: bi5 →
minute QuoteBar Parquet, `decoders/bi5.py`, `readers/dukascopy.py`,
`resample.py`) — same pattern, new source-specific decoder, same orchestrator.

## 2. Scope

**In scope:**
- `decoders/gdelt.py` — parse the raw GDELT CSV/zip payloads into structured
  rows (event or article records — confirm against what `algo-score` Spec 03
  actually consumes: it wants "news Parquet" with article text + publish
  timestamp for sentiment scoring, and separately GDELT *event* aggregates for
  the event-intensity feature; these may be two different output shapes from
  the same raw source — read `algo-score/SPEC.md` §2/§6 before deciding the
  output schema here, since Spec 03 is the consumer and its contract is
  already written).
- `decoders/gpr.py` — parse the GPR index file into a daily time series.
- Write to `parquet/news/gdelt/...` and `parquet/events/{gdelt,gpr}/...` per
  the tool SPEC.md line `| Out (slice 3) | news/index datasets |
  parquet/{news,sentiment,events}/{dataset}/... |` (note: `sentiment/` under
  that path is `algo-score`'s output, not this tool's — this tool writes
  `news/` and `events/` only; do not write into `sentiment/`).
- **Coverage matrix.** A `algo-transform coverage` command (or equivalent —
  check current `cli.py` surface and extend consistently) that computes, per
  month across the target window (2015-02 → 2024-12), whether each ingested
  news corpus has data, and renders the matrix as both a data artifact
  (`parquet/_meta/...` per the tool SPEC.md line 27) and a figure (vector PDF,
  per `experiments.md` §3 figure inventory — coordinate the plotting library
  choice with Spec 05/`algo-analyze`, which owns matplotlib elsewhere in the
  suite, so there isn't a second plotting dependency for one figure).
- Apply the **coverage rule** from `PRD.md` §4: with GDELT as the only
  MVP-phase news corpus, the window is the largest contiguous span where GDELT
  covers ≥80% of months. Implement this as a pure function over the coverage
  matrix, testable without I/O.

**Out of scope:** sentiment scoring, event-intensity feature normalization for
the backtest (that's `algo-score`, which explicitly reads `parquet/news/...`
and `parquet/events/...` as *its* input — see `algo-score/SPEC.md` §2). Do not
pre-normalize into [-1,1] or bucket onto the minute grid here; that's Spec 03's
job. This tool's job ends at "canonical, typed, partitioned Parquet mirroring
the raw source's own facts."

## 3. Currency-strength feature

The tool SPEC.md line 27 also lists "currency-strength" as slice-3 scope. This
is a **price-derived** feature (not news-derived) — check whether it's actually
needed before Spec 04 (the filter chain) or whether it's a `future work` item
that got bundled into the slice-3 line item prematurely. If `algo-backtest`
Spec 04 doesn't consume it, defer it with a `technical-debt.md` entry (blocker:
no consumer; trigger: filter chain needs a currency-strength filter) rather
than building unused output. Don't guess — read `algo-backtest/SPEC.md` and
`specs.md` §11.3.2 (the F1–F7 filter table) to see if any filter's "source of
input" column names currency-strength. If not, defer it; this spec's core
deliverable is the coverage matrix and the two decoders.

## 4. Test requirements

Gherkin/pytest-bdd, mirroring the existing Dukascopy transform feature style.
Cover: happy-path decode for each source; malformed/truncated raw payload
(fail fast, name the file); coverage-matrix correctness on a synthetic
multi-month fixture with deliberate gaps (assert the rule picks the right
contiguous span); GPR forward-continuity (it's a daily index — decide here
whether forward-fill happens in this tool or is deferred to `algo-score`
per that tool's SPEC.md §6.2, which already claims GPR forward-fill as *its*
job — if so, this tool just emits the raw daily series untouched, no
forward-fill here, to avoid duplicating that logic in two tools).

## 5. Definition of done

- `algo-transform run --source gdelt ...` and `--source gpr ...` produce
  canonical Parquet under `parquet/news/gdelt/` and `parquet/events/{gdelt,gpr}/`.
- Coverage-matrix command runs over the real Spec-01-downloaded window (even if
  partial) and emits both the data artifact and the figure.
- The coverage rule's window decision is logged/printed, not silently applied —
  this number gets cited in Chapter 4 (Spec 06), so it must be traceable to a
  command and a run, per the reproducibility discipline in `experiments.md` §5.
- `make check`, `make audit` green.
- Tool SPEC.md slice-3 status updated; `00-PLAN.md` §1 updated; Spec 03
  unblocked (confirm the actual on-disk schema of `parquet/news/gdelt/...`
  matches what `algo-score/SPEC.md` §2 declares as its input — if it doesn't,
  fix the mismatch here, in this tool, since `algo-score`'s contract is already
  fixed and published in its own SPEC.md).
