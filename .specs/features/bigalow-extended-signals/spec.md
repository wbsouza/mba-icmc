# Bigalow extended signals — specification

Status: draft, approved for implementation 2026-09-28 (user decision, scoped
down for time: ship the four computable rules now, defer the named/factory
filter-instance architecture). Story: 23. Builds on Story 22's Phase 1
(candle_contract.py/candle_catalog.py/candle_context.py, hardened at `ebac509`
on `feat/22-candlestick-rules`).

## Problem Statement

`book-mining` (2026-09-28) read the full 15,977-line clean markdown of
*High-Profit Candlestick Patterns* and found three new patterns and one new
context/confluence input with fully- or near-fully-computable criteria, not
covered by the presentation deck the original 18-rule ledger was built from.
Full findings: `~/.claude/skills/bigalow-candlestick-patterns/references/book-only-material.md`.
This story admits the four items whose confidence was "fully computable" or
"needs one stated convention" into the active catalog/context, using exactly
the mechanism the 18 admitted rules already use — no new class, no new chain
architecture.

## Goals

- [ ] Add three new pattern rules to `candle_catalog.py`'s multilabel table.
- [ ] Add one new context field (Fibonacci confluence) to `candle_context.py`.
- [ ] Each new rule keeps a stable ID, source citation and positive/negative/
      boundary examples, same convention as the existing 18.
- [ ] Legacy behavior (18-rule catalog, existing context fields) unchanged
      when these are not configured/enabled.

## Out of Scope

| Item | Reason |
| --- | --- |
| Named/parameterized filter-chain instances (the "same filter class, multiple named chain positions, abstract-factory-style rule-set presets" design discussed with the user) | Real, wanted, but a chain/wiring/strategies.py architecture change under strict time pressure; explicitly deferred to a future story. Not touched here. |
| Any stop/exit/sizing rule from `book-only-material.md`'s "Money management and stops" section (half-way-point stop, gap-up two-stage stop, windfall partial-exit, scaling entry) | Touches F5/F6, explicitly out of Story 22's bounds too; needs its own separate scope decision per the existing out-of-scope convention. Not touched here. |
| SMA-based entry/stop system's stop half (the entry-trigger half is a natural future context field, not built here either — time) | Same reason. |
| Tweezer Top/Bottom | Two unresolved conventions (equality tolerance AND unbounded lookback window) — more assumption-heavy than the other three; deferred to keep this batch small and fast. Listed for a future amendment. |
| Any bearish mirror of Methods Rising | `book-mining` greped the full book and found zero hits for a symmetric bearish pattern; inventing one would not be sourced. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Meeting Line / Counterattack Line: "at or near the previous day's close" | Reuse the catalog's existing `doji_body_ratio`-style tolerance: `abs(close[t] - close[t-1]) <= 0.10 * range[t]` | No numeric bound is given in the book; this is the same convention already used for the catalog's other "near-equal" boundaries, not a new invented number. | Yes (user, 2026-09-28) |
| Fibonacci confluence: "a sustained trough and peak" | Reuse `candle_context.py`'s existing swing-level lookback (the same swing high/low the perception layer already computes for F6's stop distance) as the trend anchor | The book gives no swing-selection rule; reusing an already-tested swing calculation avoids a second, uncoordinated swing definition. | Yes (user, 2026-09-28) |
| Fibonacci confluence zone width | A price is "at" a level when within the same 0.10-of-range tolerance as the Meeting Line convention above | Keeps one tolerance convention across this batch instead of two different magic numbers. | Yes (user, 2026-09-28) |

Open questions: none unrecorded. The full table below (originally titled
"Assumptions & conventions") remains as the authoritative convention record
for this story:

| Rule | Convention chosen | Rationale |
| --- | --- | --- |
| Meeting Line / Counterattack Line: "at or near the previous day's close" | Reuse the catalog's existing `doji_body_ratio`-style tolerance: `abs(close[t] - close[t-1]) <= 0.10 * range[t]` (same 0.10 fraction the doji rule already uses) | No numeric bound is given in the book; this is the same convention already used for the catalog's other "near-equal" boundaries, not a new invented number. |
| Fibonacci confluence: "a sustained trough and peak" | Reuse `candle_context.py`'s existing swing-level lookback (the same `swing_lookback_bars`-derived high/low the perception layer already computes for F6's stop distance) as the trend anchor, rather than inventing a new swing-detection algorithm | The book gives no swing-selection rule; reusing an already-existing, already-tested swing calculation avoids introducing a second, uncoordinated swing definition into the codebase. |
| Fibonacci confluence zone width | A price is "at" a Fibonacci level when within the same 0.10-of-range tolerance as the Meeting Line convention above | Keeps one tolerance convention across this batch instead of two different magic numbers. |

## User Stories

### P1: Three new geometry rules

As a researcher, I want Meeting Line/Counterattack Line and Methods Rising
recognized alongside the existing 18 patterns, with the same stable-ID,
multilabel, warmup-aware contract, so the catalog stays internally consistent.

**Acceptance criteria**:
1. WHEN a bar sequence matches Methods Rising's five criteria (bullish bar,
   3–6 indecisive pullback bars each closing `>= open(B)`, a final bar
   opening above the prior close and closing above `close(B)`) THEN the
   catalog SHALL emit `methods_rising` with polarity 1 (BEXT-01).
2. WHEN a bar sequence matches the bearish Counterattack Line (prior bar
   continues a bullish trend, current bar gaps up beyond the prior close in
   the trend direction, then closes within the Meeting-Line tolerance of the
   prior close) THEN the catalog SHALL emit `bearish_counterattack_line`
   with polarity -1; the bullish mirror (`bullish_counterattack_line`)
   SHALL fire under the mirrored gap-down/prior-bearish-trend conditions
   (BEXT-02).
3. IF the Counterattack Line's close-back condition is not met (close moves
   past the piercing/dark-cloud midpoint threshold instead) THEN the catalog
   SHALL NOT double-classify the bar as both Counterattack Line and
   piercing_line/dark_cloud_cover — the mutually exclusive geometry
   boundaries from the existing rules apply unchanged (BEXT-03).
4. WHILE a recognizer lacks its required history (Methods Rising needs up to
   7 bars: 1 signal + up to 6 pullback bars) THE catalog SHALL report WARMUP
   for that rule specifically, not NO_PATTERN, consistent with CND-04
   (BEXT-04).
5. WHEN two histories share the same prefix THEN both new rules SHALL emit
   identical evidence for that prefix regardless of either future suffix,
   consistent with CND-05 (BEXT-05).
6. WHERE legacy/existing catalog configuration omits these new rule IDs THE
   engine SHALL reproduce prior 18-rule catalog output exactly, on frozen
   regression fixtures, consistent with CND-09 (BEXT-06).

**Independent test**: hand-built OHLC fixtures for one positive, one
negative and one boundary example per new rule (per the convention table
above), plus a prefix-invariance fixture and a legacy-catalog regression
fixture using the existing candle_catalog.feature's frozen inputs.

### P1: Fibonacci confluence context field

As a researcher, I want a Fibonacci-retracement confluence flag alongside
the existing T-line/stochastic/SMA context fields, so I can test whether it
adds anything to entry eligibility without changing existing context fields.

**Acceptance criteria**:
1. WHEN the causal swing high/low over the configured lookback gives a
   nonzero range THEN the context evaluator SHALL compute the 38.2/50/61.8%
   retracement levels between them and report whether the current close is
   within tolerance of any level (BEXT-07).
2. IF the swing high equals the swing low (zero range) THEN the confluence
   field SHALL report an explicit degenerate/undefined status, never a
   division by zero or a fabricated level (BEXT-08).
3. WHILE the context evaluator's swing-level history has not yet reached its
   configured lookback THE confluence field SHALL report WARMUP, consistent
   with the other context fields' warmup handling (BEXT-09).
4. WHERE Fibonacci confluence is not configured/enabled THE existing context
   fields (T-line, stochastic, SMA distances) SHALL be byte-identical to
   their current output (BEXT-10).

**Independent test**: a hand-calculated rising-trend and falling-trend swing
pair with known 38.2/50/61.8% levels, one price within tolerance and one
clearly outside, plus a zero-range degenerate fixture and a warmup fixture.

## Edge cases

Methods Rising's pullback count is variable (3–6); test both boundaries (3
and 6) and one rejected case (2 pullback bars, and 7). Counterattack Line's
gap direction must match the prior trend direction (a gap the *wrong* way is
a different, unnamed formation and must not fire). Fibonacci's swing anchor
must use only causal (already-closed) bars — no future-bar leakage, same
prefix-invariance discipline as every other perception module in this
codebase.

## Implicit requirement dimensions

| Dimension | Coverage |
| --- | --- |
| Input validation and bounds | BEXT-04, BEXT-08, BEXT-09; invalid OHLC/UTC handling reuses candle_contract.py's existing validation, untouched by this story. |
| Idempotency / prefix invariance | BEXT-05, BEXT-09 and the general prefix-invariance discipline. |
| Legacy compatibility | BEXT-06, BEXT-10 — the two "byte-identical when disabled" criteria. |
| Observability | Every new hit/field carries its rule ID, polarity, and (for Fibonacci) the level/status, same shape as existing evidence. |

## Requirement Traceability

| Requirement ID | Story | Design component | Tasks | Status |
| --- | --- | --- | --- | --- |
| BEXT-01 | P1 patterns | candle_catalog.py | T1, T2 | Implemented (T2) |
| BEXT-02 | P1 patterns | candle_catalog.py | T1, T2 | Implemented (T2) |
| BEXT-03 | P1 patterns | candle_catalog.py | T2 | Implemented (T2) |
| BEXT-04 | P1 patterns | candle_catalog.py | T1, T2 | Implemented (T2) |
| BEXT-05 | P1 patterns | candle_catalog.py | T2 | Implemented (T2) |
| BEXT-06 | P1 patterns | candle_catalog.py | T2 | Implemented (T2) |
| BEXT-07 | P1 context | candle_context.py | T3 | Pending |
| BEXT-08 | P1 context | candle_context.py | T3 | Pending |
| BEXT-09 | P1 context | candle_context.py | T3 | Pending |
| BEXT-10 | P1 context | candle_context.py | T3 | Pending |

Coverage: 10 requirements, 10 mapped to tasks (T1–T3), 0 unmapped.

## Success criteria

- [ ] All 10 requirements have passing Gherkin evidence.
- [ ] Legacy 18-rule catalog and existing context fields byte-identical when
      the new items are absent/disabled.
- [ ] Each new rule's source citation (book PDF page + line range) is
      recorded in the ledger addendum, same convention as the original 18.
