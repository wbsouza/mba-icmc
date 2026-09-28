# Confluence Chain Specification

Status: approved for implementation on 2026-09-28 (D1–D11 resolved by the user;
D5 follows the source's bar-open timing). Planning baseline: `main` at `35a0dc9`
(merged PR #87), 2026-09-28. Story: 21.

The user-supervised Claude story at
`algo-suite/docs/stories/in-progress/21-confluence-chain/spec.md` is the primary
contract. This planning companion does not supersede or edit it. Its EARS criteria
make proposed clarifications testable; D1–D11 must be accepted or revised before
dependent implementation. In particular, the source's bar-open exit wording and
this draft's next-event semantics differ; neither a timing change nor a new
reversal rule is silently authorized. The source spec, progress and evidence
remain byte-identical to `35a0dc9`.

## Problem Statement

Session-2 rule cells were effectively one-sided. The already-inspected H1 decision
log motivates testing whether context, a relative intensity trigger, optional F2
confirmation, and a shorter exit behave differently from drift controls. It does
not establish profitability, an untouched validation period, or a four-pip effect.
The archived forward-return statistic is `(close[t+k]/close[t]-1)/1e-4`, not an FX
price change in pips. The merged archive's bytes remain evidence of the exploration.
PR #87 already records the calibration-month outlier analysis. This plan preserves
that work and its checked progress item; remaining gates concern population,
row-level completeness and point-in-time availability, not redoing that analysis.

## Goals

- [ ] Specify and validate exactly seven arms on H1 and H4, totaling 14 cells.
- [ ] Reuse the current chain and execution contracts with causal history and exits.
- [ ] Report positive, null, negative, and unavailable outcomes without changing cells.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Implementation, models, backtests or deployments during this turn | Documentation planning only; planning-document publication is separately authorized |
| Candlestick or support/resistance arms | Story 22 is a separate experiment; none enters these 14 cells |
| Story 19 adaptive models, F7 retraining or adaptive-model integration | Story 21 is a deterministic rule experiment |
| Additional clocks, threshold searches or new confirmatory datasets | Requires a separately authorized protocol |
| Shared-file edits by concurrent Story 21 workers | Integration lane owns wiring, engine, strategy loader, recorder, schemas and manuscript |
| Changes to the user-supervised story spec, progress, evidence or historical run artifacts | Preserve source files; qualify only in this companion and new reports |

## Assumptions & Open Questions

All defaults below are proposals for review, not approved implementation choices.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| D1: trailing month | Fixed 30 calendar days before each UTC month start; freeze for the entire month, including a mid-month run start | Preserves the existing 30-day proposal while distinguishing it from a previous calendar month | Yes (user, 2026-09-28) |
| D2: quantile sample and availability | One intensity observation per completed signal bar; linear quantile interpolation; close time and availability time both strictly before cutoff | Avoids minute-grid overweighting and prevents late/current observations entering calibration | Yes (user, 2026-09-28) |
| D3: trigger sign | `intensity_sign: -1`; high q90 crossing means SELL, low q10 crossing means BUY; equal cutoffs mean HOLD | Makes the reversed original rule explicit without searching outcomes | Yes (user, 2026-09-28) |
| D4: agreement | Nonempty named required-voter set; all required votes directional and identical; other directional voters cannot disagree; explicit HOLD blocks, optional ABSTAIN/NEUTRAL do not | Gives absent, abstaining and conflicting votes precise outcomes | Yes (user, 2026-09-28) |
| D5: bar-count exit | Source timing accepted by the user on 2026-09-28: close at the open of signal bar t+N, where t is the signal bar during which the entry filled (the bar after the decision bar). Expiry is due when bar t+N-1 closes; the engine submits one market closure on the first tradable event whose timestamp is at or after the start of bar t+N (the open), using actual fill prices. N=4 spans the four closes of the horizon check. The earlier draft (strictly-later event after the Nth fully held close) is rejected. | Matches the supervised story wording; the open of t+N is the first real quote of that bar, so no price is fabricated | Yes (user, 2026-09-28) |
| D6: exit precedence and re-entry | Reconcile stop fills first, then expiry, then configured veto closure, then entry/reversal; no re-entry on the expiry-submission event; same-side signals do not reset age | Prevents duplicate closures and off-by-one extensions | Yes (user, 2026-09-28) |
| D7: evidence protocol | H1 A versus T-only is the primary exploratory comparison on Nov–Feb; H4 and other contrasts secondary; block 4, sensitivity 2, 999 resamples, seed 42, alpha .05 | The year and Nov–Feb were inspected; H4's four bars span 16 scheduled hours, not the H1 four-hour evidence | Yes (user, 2026-09-28) |
| D8: completeness and warmup | Require a full registered 30-day history and L+1 complete closes; documented market closures excluded; missing expected data hard-fails; normal initial collection emits WARMUP/HOLD | Separates insufficient initial collection from broken history | Yes (user, 2026-09-28) |
| D9: controls and risk | Explicit constant-direction control filter; same F5 caps and F6 time plan as A; no artificial intensity thresholds | Keeps both drift controls independent of news coverage and bounded to the existing arms | Yes (user, 2026-09-28) |
| D10: audit compatibility | Preserve decisions/trade-plan schemas; add a versioned exit-event sidecar through integration-owned audit/recorder code | Existing recorder clears the current trade ID on close; retain the closing trade link without breaking consumers | Yes (user, 2026-09-28) |
| D11: entry and expiry interaction | Register `min_hold_bars: 4` for time-exit arms; A-plan uses its pinned existing template; preserve explicit `close_on_veto` value | Avoids accidental early reversals while disclosing that A-plan compares complete exit policies | Yes (user, 2026-09-28) |

Open questions: none. The user resolved D1–D11 on 2026-09-28 (implementation
handoff): D1–D4 and D6–D11 accepted as drafted; D5 replaced by the source's
bar-open timing. Implementation of Stories 19, 21 and 22 is authorized by the
handoff in `algo-suite/docs/stories/claude-implement-19-21-22.md`.

## User Stories

### P1: Deterministic confluence decisions

As a researcher, I want reproducible named votes so that an entry identifies the
context and trigger that justified it. This slice is independently testable with
Gherkin examples against the pure chain, without a model or LEAN run.

**Acceptance Criteria**:
1. WHEN every configured required voter has exactly one identical BUY or SELL vote and no other directional voter disagrees or explicitly votes HOLD, THEN the agreement terminal SHALL return that direction (CC-01).
2. WHEN any required voter abstains, is neutral, votes HOLD, or disagrees with another vote, THEN the agreement terminal SHALL return HOLD (CC-02).
3. WHEN all voting results abstain or are neutral, THEN the agreement terminal SHALL return HOLD (CC-03).
4. IF the required-voter list is empty, duplicated, unknown, names a gate, or a required result is missing or duplicated, THEN configuration or terminal validation SHALL fail with the offending name and remediation (CC-04).
5. WHEN F5 or F6 vetoes, THEN the chain SHALL return NO_TRADE before consulting the agreement terminal (CC-05).
6. WHEN L+1 valid completed closes are available, THEN the F1 momentum variant SHALL vote BUY for `close[t]/close[t-L]-1 > 0`, SELL for a negative value, and NEUTRAL for zero, without vetoing (CC-06).
7. WHILE valid initial price history contains fewer than L+1 completed closes, the momentum component SHALL expose WARMUP with no directional vote (CC-07).
8. IF required price history is missing, nonfinite, nonpositive, duplicated, or out of order after its coverage contract applies, THEN the momentum component SHALL raise an explained error (CC-08).

### P1: Causal monthly intensity thresholds

As a researcher, I want thresholds reproducible from information available at the
cutoff. This slice is independently testable by changing future/late rows and
asserting that prior snapshots and decisions stay identical.

**Acceptance Criteria**:
1. WHEN the first decision of UTC month M is evaluated, THEN the history component SHALL freeze q10 and q90 from one observation per completed signal bar in `[M-30 calendar days, M)`, requiring both close time and availability time strictly before M (CC-09).
2. WHILE month M remains active, the history component SHALL reuse the same snapshot regardless of newly arriving or revised data (CC-10).
3. WHEN q10 is below q90, THEN relative F4 with the proposed sign -1 SHALL emit SELL at intensity greater than or equal to q90, BUY at intensity less than or equal to q10, and NEUTRAL between them (CC-11).
4. WHEN q10 equals q90, THEN relative F4 SHALL emit HOLD for every current intensity (CC-12).
5. IF required intensity history is absent, nonfinite, malformed, duplicated, out of order, or lacks verifiable availability provenance, THEN the data gate SHALL fail with the affected interval and remediation (CC-13).
6. WHILE a declared initial collection is valid but not yet complete, the relative trigger SHALL expose WARMUP/HOLD without substituting fixed thresholds (CC-14).

### P1: Causal exit and legacy compatibility

As a researcher, I want the holding horizon to count completed bars and actual
fills. This slice is testable against pure lifecycle examples and, later, native
event-order scenarios using the existing execution engine.

**Acceptance Criteria**:
1. WHEN a time-exit position whose entry filled during signal bar t observes the close of completed signal bar t+N-1, THEN its lifecycle SHALL mark expiry due at that close, which is the open of bar t+N (CC-15).
2. WHEN an expiry is due and a tradable event with a timestamp at or after the open of bar t+N arrives for a still-open position, THEN the engine SHALL submit one closure through its existing executor at that event, using actual fill prices (CC-16).
3. WHEN a stop fill and expiry compete for the same position, THEN the engine SHALL reconcile the stop before deciding whether any expiry quantity remains (CC-17).
4. WHEN a position closes, reverses, or receives repeated events, THEN the lifecycle SHALL retain at most one pending expiry per trade and reset age only for a new filled trade (CC-18).
5. WHEN expiry submission occurs, THEN the engine SHALL suppress new entry on that same event (CC-19).
6. WHERE a strategy omits the new options, the system SHALL retain its existing F1, F4, terminal, F6 and `close_on_veto` behavior (CC-20).
7. WHEN a time-exit arm is resolved, THEN its F6 plan SHALL specify 3% risk, ATR(14) times 2 base stop, empty targets and trail steps, and N=4 with broker floors and OANDA economics still applied (CC-21).
8. IF N is a boolean, noninteger, zero or negative, THEN F6 configuration parsing SHALL reject it with a remediation message (CC-22).

### P1: Bounded exploratory protocol and evidence

As a researcher, I want an auditable 14-cell comparison whose claims match the
information actually observed. The manifest and reporting contracts can be
validated independently before any cell runs.

**Acceptance Criteria**:
1. WHEN the manifest is generated, THEN it SHALL contain exactly A, B, A-plan, T-only, M-only, always-short and always-long on each of H1 and H4 (CC-23).
2. WHEN preflight evaluates the manifest, THEN it SHALL require a verified input-population ledger distinguishing calendar-expanded rows, valid completed decision bars, excluded market closures, warmup and missing expected data before any cell is launched (CC-24).
3. WHEN the horizon evidence is re-derived, THEN its new report SHALL distinguish normalized-return units from `(close[t+k]-close[t])/0.0001` EUR/USD price pips using timestamp-matched source prices (CC-25).
4. The evidence report SHALL preserve the original signal-horizon archive byte-for-byte (CC-26).
5. WHEN any result or registration describes the study, THEN it SHALL label the whole year and Nov–Feb exploratory and already inspected (CC-27).
6. WHEN a clock is reported, THEN its protocol SHALL state momentum L=480 H1 or L=120 H4 closed bars and a four-bar horizon of four or sixteen scheduled hours respectively, with market gaps able to extend elapsed time (CC-28).
7. WHEN the primary comparison is computed, THEN analysis SHALL use paired UTC calendar-day net portfolio returns for H1 A minus T-only on Nov–Feb with the registered stationary-bootstrap parameters (CC-29).
8. WHEN a prediction endpoint is computed, THEN analysis SHALL report next-four-completed-bar directional hit rate on entry-eligible decisions, counting zero returns as misses and reporting incomplete forward horizons separately (CC-30).
9. WHEN a decision or exit is recorded, THEN its artifacts SHALL retain named votes, threshold cutoff and sample provenance, bar age, due/submission/fill times, exit reason and the actual trade link through the versioned audit contract (CC-31).
10. IF a cell, required input, or inference contract is unavailable, THEN reporting SHALL state the failure explicitly without silently dropping that cell or manufacturing an estimate (CC-32).

## Edge Cases

Month rollover on a weekend uses the fixed UTC cutoff, not first-trade time.
Mid-month start rebuilds that month's frozen snapshot. A source corrected after
cutoff cannot rewrite it. Market closures do not count as bars. Unexpected missing
minutes prevent a complete candle and fail registered coverage, rather than being
filled with synthetic quotes. End-of-run pending expiry remains unresolved/open
in the report if no later event exists. A partially filled stop reduces expiry
quantity to the remaining position. Rejected expiry orders remain visibly pending;
retry waits for terminal rejection/cancellation and another real event, never while
an order is live. A-plan's longer holding policy remains distinct and disclosed.

## Implicit Requirement Dimensions

| Dimension | Coverage |
| --- | --- |
| Input validation and bounds | CC-04, CC-08, CC-13, CC-22, CC-24 |
| Failure and partial failure | CC-17, CC-18, CC-32; rejected orders and partial stops above |
| Idempotency and retries | CC-10, CC-18, CC-19 |
| Auth boundaries and rate limits | N/A because offline local artifacts, no new service or credentials |
| Concurrency and ordering | CC-09, CC-15–CC-19; integration-owned shared files |
| Data lifecycle and expiry | CC-10, CC-15, CC-26, CC-31 |
| Observability | CC-31, CC-32; explained boundary errors |
| External dependency failure | CC-13, CC-24, CC-32; no assumed NAS/Docker availability |
| State-transition integrity | CC-05, CC-15–CC-20 |

## Requirement Traceability

| Requirement ID | Story | Design component | Tasks | Phase | Status |
| --- | --- | --- | --- | --- | --- |
| CC-01 | P1 votes | Agreement | T1, T11, T12 | 1, 3 | Implemented (T1) |
| CC-02 | P1 votes | Agreement | T1 | 1 | Implemented (T1) |
| CC-03 | P1 votes | Agreement | T1 | 1 | Implemented (T1) |
| CC-04 | P1 votes | Agreement/config | T1, T11, T12 | 1, 3 | Implemented (T1) |
| CC-05 | P1 votes | Existing chain veto | T1, T12, T13 | 1, 3 | Implemented (T1) |
| CC-06 | P1 votes | Momentum | T2, T12 | 1, 3 | Implemented (T2) |
| CC-07 | P1 votes | Momentum | T2 | 1 | Implemented (T2) |
| CC-08 | P1 votes | Momentum/coverage | T2, T9 | 1, 2 | Implemented (T2) |
| CC-09 | P1 thresholds | History snapshot | T3, T4, T9 | 1, 2 | Implemented (T3, T4) |
| CC-10 | P1 thresholds | History snapshot | T3, T4 | 1 | Implemented (T3, T4) |
| CC-11 | P1 thresholds | Relative F4 | T4 | 1 | Implemented (T4) |
| CC-12 | P1 thresholds | Relative F4 | T4 | 1 | Implemented (T4) |
| CC-13 | P1 thresholds | History/coverage | T3, T9 | 1, 2 | Implemented (T3) |
| CC-14 | P1 thresholds | Relative F4 | T3, T4 | 1 | Implemented (T3, T4) |
| CC-15 | P1 exits | Exit lifecycle | T6, T13 | 2, 3 | In Tasks |
| CC-16 | P1 exits | Exit lifecycle/engine | T6, T13 | 2, 3 | In Tasks |
| CC-17 | P1 exits | Stop precedence | T6, T13 | 2, 3 | In Tasks |
| CC-18 | P1 exits | Trade lifecycle | T6, T13, T14 | 2, 3 | In Tasks |
| CC-19 | P1 exits | Entry suppression | T6, T13 | 2, 3 | In Tasks |
| CC-20 | P1 compatibility | Legacy contracts | T1, T2, T4, T5, T11, T12, T13, T15, T22 | 1–4 | Implemented (T1, T2, T4) |
| CC-21 | P1 exits | F6/config | T5, T10, T11 | 1–3 | In Tasks |
| CC-22 | P1 exits | F6/config | T5 | 1 | In Tasks |
| CC-23 | P1 protocol | Manifest/controls | T7, T10, T16, T17 | 2, 4 | In Tasks |
| CC-24 | P1 protocol | Availability gate | T9, T17 | 2, 4 | In Tasks |
| CC-25 | P1 evidence | Re-derivation | T8, T19, T20 | 2, 4 | In Tasks |
| CC-26 | P1 evidence | Archive preservation | T8, T19 | 2, 4 | In Tasks |
| CC-27 | P1 evidence | Registration/report | T16, T18, T19, T20, T21 | 4 | In Tasks |
| CC-28 | P1 protocol | Clock contract | T2, T6, T10, T16, T20 | 1, 2, 4 | Implemented (T2) |
| CC-29 | P1 inference | Comparison | T16, T18 | 4 | In Tasks |
| CC-30 | P1 inference | Prediction endpoint | T18 | 4 | In Tasks |
| CC-31 | P1 audit | Audit/recorder | T3, T4, T6, T14, T15, T19, T22 | 1–4 | Implemented (T3, T4) |
| CC-32 | P1 failures | Preflight/report | T9, T17, T18, T19 | 2, 4 | In Tasks |

Coverage: 32 total requirements, 32 mapped to tasks, 0 unmapped. All remain
unimplemented; “In Tasks” records planning coverage, not verification.

## Success Criteria

- [ ] All 32 requirements have passing Gherkin evidence at the appropriate future gate.
- [ ] Exactly 14 outcomes, including explicit unavailable/failed outcomes, are reported.
- [ ] No claim of untouched validation, proven four-pip effect, or H4 horizon confirmation.
- [ ] Integration owner accepts contracts before shared files change or runs begin.
