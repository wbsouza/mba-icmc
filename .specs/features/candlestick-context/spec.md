# Candlestick catalog and context Specification

Status: amended planning draft, September 28, 2026. Story 22 owns this extension;
Story 13 is historical. Planning only; no task is implemented by this specification.

## Problem Statement

The engine represents candlesticks as one of six labels. This loses simultaneous
formations and does not express the trend/context/confirmation distinctions in
the supplied Bigalow material. The active scope is deterministic rules and their
evaluation. Laya is explicitly DEFERRED, not an optional active provider.

Source inventory and historical findings remain in the
[Story 22 research brief](../../../algo-suite/docs/stories/in-progress/22-candlestick-context-extension/candlestick-extension.md).
This file owns requirements; [design.md](design.md) owns the proposed design;
[tasks.md](tasks.md) owns implementation status and test mapping. The story's
progress file owns handoff history. Do not maintain a competing task checklist.

Future parallel work follows the coordinator-owned
[Stories 19/21/22 plan](../../../algo-suite/docs/stories/parallel-19-21-22.md).
Lane C owns rules/perception/F3. Shared integration and monograph handoffs follow
that plan; no worker or implementation worktree is created by this amendment.

## Goals

- [ ] Deliver a versioned multilabel rule/context filter without changing legacy runs.
- [ ] Evaluate explicit rules on a reviewed recognition dataset with leakage-free splits.
- [ ] Reproduce signals in offline preparation and LEAN with auditable settings.
- [ ] Publish negative, inconclusive, and positive outcomes with equal traceability.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Live trading or paper-account promotion | Requires separate readiness authorization and Story 17 risk review. |
| Online learning during a replay | Invalidates frozen-run reproducibility. |
| Laya and other learned candlestick providers | DEFERRED: CND-20–24 and T17–T21; no adapter, training, cache, token-budget or checkpoint-smoke gate in active scope. |
| New GPU service or Torch runtime | No learned candlestick runtime in the active design. |
| YOLO training, Jev integration, or new news-data acquisition | Separate ideas, not required for candle/context evaluation. |
| Rewriting F5/F6 or introducing Bigalow exit orders now | Story 17 owns risk; exit-policy experiments require a separate explicit scope decision. |
| Every named chart formation at once | Ambiguous formations require definition and labels before executable tasks. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Active scope | Deterministic catalog, context, confirmation, F3 policy and rules-only evaluation; Laya explicitly DEFERRED. | User's planning amendment supersedes the earlier learned-provider proposal. | Yes |
| Existing F7 | Preserve normal F7 model provenance and compatibility; Story 19 owns fitting changes first, Story 22 encoder integration follows. | Rules feed an existing model family; this does not reactivate Laya. | Proposed |
| Rollout | Frozen legacy, expanded geometry, then geometry plus context under registered advisory/required-entry modes. | Separates incremental rule effects. | Proposed |
| Deployment | Shared deterministic producer for offline rows and native replay. | Closed-bar parity without a learned-provider lifecycle. | Proposed |
| Catalog slice | Preserve six legacy labels; add doji variants, spinning tops, harami, hanging man, inverted hammer, piercing, dark cloud, and kicker candidates after source review. | Bounded major-signal expansion; exact label/function mapping is a T1 deliverable. | Proposed |
| Sequence slice | Implement doji then engulfing with next-closed-bar confirmation; broader J-hook/fry-pan/dumpling/cradle/scoop/crunch forms remain ledger candidates. | Provides a testable first sequence without inventing subjective geometry. | Proposed |
| Timing | Closed bars only, explicit UTC decision timeframe; no intrabar opening/stop tactics in this slice. | Existing canonical clock supports this contract. | Proposed |
| Input bounds | Maximum context history 256 closed bars; reject larger requested history. | Accommodates SMA(200) context while bounding state. | Proposed |
| Rules acceptance | Register per-label recognition/coverage criteria before inspecting final evaluation outcomes; no speaker-derived accuracy or profit target. | Reviewed labels and a justified protocol are necessary independently of learned models. | Proposed |
| Bigalow formulas | T1 resolves definitions or marks them deferred; unresolved rules cannot enter the recognition dataset or execution. | OCR/transcript ambiguities must not become guessed labels. | Proposed |
| Volume | Existing quote activity stays optional and is named accurately. | Spot-FX quote counts are not centralized traded volume. | Yes |

**Open questions:** none unrecorded; proposed defaults above require plan review.
Source-definition uncertainties are explicit blocking outputs of T1, not silent
implementation choices. Formal approval is not claimed.

## User Stories

### P1: Reproducible explicit candlestick evidence

As a researcher, I want candle shapes and context separately so I can compare
their incremental contribution instead of silently changing strategy semantics.

**Acceptance Criteria**:
1. WHEN a rule enters the catalog THEN the catalog SHALL record its stable ID, source page/time, version, geometry/context distinction, and exact positive/negative/boundary examples. (CND-01)
2. WHEN a closed candle is processed THEN the detector SHALL preserve every active configured pattern in a stable ordered result rather than select one by lexical priority. (CND-02)
3. IF prices, timestamps, ordering, configuration, or requested history bounds are invalid THEN the producer SHALL reject the input before advancing its state. (CND-03)
4. WHILE a recognizer lacks its required history the producer SHALL report WARMUP rather than NO_PATTERN. (CND-04)
5. WHEN two histories share the same prefix THEN the producer SHALL emit identical evidence for that prefix regardless of either future suffix. (CND-05)
6. WHEN the context evaluator runs THEN it SHALL keep geometry, causal trend/level evidence, and confirmation status as distinct fields. (CND-06)
7. WHEN a doji candidate is followed by a qualifying engulfing on the next closed bar THEN the sequence evaluator SHALL date confirmation at that later bar's close. (CND-07)
8. IF the next closed bar does not qualify THEN the sequence evaluator SHALL expire that doji candidate without emitting a confirmed sequence. (CND-08)
9. WHERE the legacy detector mode is selected the engine SHALL reproduce the original six-label selection and downstream decisions on frozen regression fixtures. (CND-09)
10. WHEN offline and native replay process identical canonical bars THEN they SHALL emit equal IDs, statuses, and timestamps with numeric differences no greater than the registered tolerance. (CND-10)

**Independent Test**: Replay the same fixed fixture through legacy and new modes;
prove legacy equality, multilabel preservation, and confirmation timestamps.

### P1: Explicit decisions, compatible artifacts, and visible evidence

As a researcher, I want configuration and recorded evidence to explain how a
pattern influenced the final decision without confusing detection with execution.

**Acceptance Criteria**:
1. WHERE advisory mode is selected the pattern/context filter SHALL set veto to false, including on abstention. (CND-11)
2. WHERE required eligibility mode is selected the policy SHALL veto new entries unless exactly one candidate direction satisfies the registered confirmation/context rules. (CND-12)
3. WHILE an entry is vetoed existing position protection SHALL continue on its existing execution schedule. (CND-13)
4. IF an existing F7 model, feature order, catalog, timeframe, context policy, or F7 calibration contract mismatches the strategy THEN startup SHALL reject it with an F7 retraining or contract-correction instruction before replay. (CND-14)
5. WHEN an observation is persisted THEN the audit SHALL record pattern IDs, context, confirmation time, mode, provider provenance, recommendation, veto, and final action separately. (CND-15)
6. WHEN the viewer renders a new observation THEN it SHALL distinguish detected patterns from the filter recommendation and final trade action. (CND-16)
7. WHEN the viewer renders an old artifact THEN it SHALL identify unavailable new fields as historical omissions rather than fabricated detections. (CND-17)

**Independent Test**: A bullish detection with a final SELL remains visibly three
distinct facts; a required-mode veto never cancels or delays an existing stop.

### P2: Reviewed rule recognition and controlled experiments

As a researcher, I want to evaluate deterministic rules on independently reviewed
sequences while keeping recognition and trading claims separately tested.

**Acceptance Criteria**:
1. WHEN labels are prepared THEN the dataset manifest SHALL distinguish reviewed labels, ambiguous exclusions, and rule-generated weak labels. (CND-18)
2. WHEN a recognition/evaluation split is validated THEN the validator SHALL reject any shared input window or outcome horizon across development, reserved threshold-calibration, and final-evaluation boundaries, independently of whether a model is fitted. (CND-19)
3. WHEN a backtest is reported THEN its result SHALL include the complete resolved filter parameters and input/code/protocol hashes plus existing F7 model provenance where enabled, including disabled filters and failed attempts. (CND-25)
4. WHEN recognition results are published THEN the report SHALL separate per-label precision/recall, multilabel errors and readiness/abstention coverage from cost-adjusted trading outcomes and disclose previously inspected periods as exploratory. (CND-26)

**Independent Test**: A fixed reviewed dataset yields reproducible rule-recognition
metrics; an overlapping window or outcome horizon causes split validation to fail.
Negative or inconclusive results are valid outcomes, not reasons to tune on test.

## Deferred requirements archive

These IDs retain the earlier proposal for historical traceability. They are
DEFERRED, outside active acceptance and completion; reactivation requires a new
scope decision. They are not optional rollout gates or dependencies of active work.

| Requirement ID | Historical requirement | Historical tasks | Status |
| --- | --- | --- | --- |
| CND-20 | Pinned Laya token bounds and bounded output schema; reject overflow, truncation and silent rule fallback. | T17 | DEFERRED |
| CND-21 | Learned weights/tokenizer/schema hashes, runtime/device, seed, split and calibration lineage. | T17, T18, T19 | DEFERRED |
| CND-22 | Identical learned labels over 100 repeats; maximum absolute probability difference 0.000001 in a pinned environment. | T19 | DEFERRED |
| CND-23 | Immutable learned-output cache; reject key/content collisions rather than overwrite. | T20 | DEFERRED |
| CND-24 | Stop replay on missing, corrupt, mismatched, duplicate or stale learned-cache rows. | T20, T21 | DEFERRED |

## Edge Cases

All require Gherkin acceptance examples in the producing task: flat bars,
zero-range normalization, missing bars, duplicate/out-of-order timestamps,
overlapping opposite-polarity patterns, neutral-only hits, unknown IDs, stale
confirmation, overlapping evaluation splits, incomplete audit records and legacy data.
No production input is silently repaired. Synthetic fixtures prove mechanics
only; they are never presented as market-performance evidence.

## Implicit requirement dimensions

| Dimension | Resolution |
| --- | --- |
| Input validation and bounds | CND-03/04; max 256 bars, finite positive valid OHLC, UTC closed bars. |
| Failure and partial failure | CND-03/14/15/25; reject invalid inputs/contracts, preserve failed/interrupted attempt evidence. |
| Idempotency and duplicates | CND-03/18/25; reject duplicate bars/sequences and conflicting run identity; preserve prior evidence. |
| Auth and rate limits | N/A: no new server, broker, or remote API in the scoped runtime. |
| Concurrency and ordering | CND-03/05/25; state isolated by run/pair/timeframe, ordered bars, one writer per artifact; coordinator leases shared files. |
| Lifecycle and expiry | CND-08/25; next-bar sequence expires; run evidence retained, no automatic deletion. |
| Observability | CND-15/25; decisions, rejection reason, manifests, and failed attempts recorded. |
| External failure | N/A for a learned-provider service: active producer is local deterministic rules; missing required market data fails explicitly under CND-03. |
| State integrity | CND-03/07/08/13; invalid data does not consume state; deterministic expiry; independent protection. |

## Requirement Traceability

| Requirement ID | Story | Tasks | Status |
| --- | --- | --- | --- |
| CND-01 | P1 evidence | T1, T3 | Implemented (T1, T3) |
| CND-02 | P1 evidence | T2, T3 | Implemented (T2, T3) |
| CND-03 | P1 evidence | T2, T4, T7 | Implemented (T2, T4) |
| CND-04 | P1 evidence | T3, T4 | Implemented (T3, T4) |
| CND-05 | P1 evidence | T3, T4, T5, T7 | Implemented (T3, T4, T5) |
| CND-06 | P1 evidence | T4 | Implemented (T4) |
| CND-07 | P1 evidence | T5 | Implemented (T5) |
| CND-08 | P1 evidence | T5 | Implemented (T5) |
| CND-09 | P1 evidence | T3, T6, T7, T9 | Implemented (T3, T6) |
| CND-10 | P1 evidence | T7, T10 | In Tasks |
| CND-11 | P1 decisions | T6 | Implemented (T6) |
| CND-12 | P1 decisions | T6 | Implemented (T6) |
| CND-13 | P1 decisions | T7 | In Tasks |
| CND-14 | P1 decisions | T8, T9, T10 | In Tasks |
| CND-15 | P1 decisions | T11, T12 | In Tasks |
| CND-16 | P1 decisions | T13, T14 | In Tasks |
| CND-17 | P1 decisions | T12, T14 | In Tasks |
| CND-18 | P2 research | T15 | In Tasks |
| CND-19 | P2 research | T15, T16 | In Tasks |
| CND-20 | Deferred archive | T17 (inactive) | DEFERRED |
| CND-21 | Deferred archive | T17, T18, T19 (inactive) | DEFERRED |
| CND-22 | Deferred archive | T19 (inactive) | DEFERRED |
| CND-23 | Deferred archive | T20 (inactive) | DEFERRED |
| CND-24 | Deferred archive | T20, T21 (inactive) | DEFERRED |
| CND-25 | P2 research | T22, T23, T24 | In Tasks |
| CND-26 | P2 research | T16, T22, T23, T24 | In Tasks |

Coverage: 21 active requirements (CND-01–19, CND-25, CND-26) mapped to 19 active
tasks (T1–T16, T22–T24); zero active requirements unmapped; five requirements
and five tasks DEFERRED. Zero implementation tasks completed or verified.

## Success Criteria

- [ ] Every active requirement has exact behavioral evidence and an atomic task commit.
- [ ] Legacy regression and native/offline parity pass before new runs launch.
- [ ] All attempted variants and parameters are reported without test-set tuning.
- [ ] Independent final verifier passes the outcome review and fault sensor.

Software success does not require a profitable strategy. Deployment promotion is
not implied by either model accuracy or completion of this plan.
