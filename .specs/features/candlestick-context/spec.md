# Candlestick catalog and context Specification

Status: draft for approval, September 28, 2026. Story 13 extension, not a new
numbered story. Planning only; no task is implemented by this specification.

## Problem Statement

The engine represents candlesticks as one of six labels. This loses simultaneous
formations and does not express the trend/context/confirmation distinctions in
the supplied Bigalow material. Laya is a proposed learned complement, not a
validated detector or a substitute for deterministic risk protection.

Source inventory and historical findings remain in the
[Story 13 research brief](../../../algo-suite/docs/stories/planned/22-candlestick-context-extension/candlestick-extension.md).
This file owns requirements; [design.md](design.md) owns the proposed design;
[tasks.md](tasks.md) owns implementation status and test mapping. The story's
progress file owns handoff history. Do not maintain a competing task checklist.

## Goals

- [ ] Deliver a versioned multilabel rule/context filter without changing legacy runs.
- [ ] Compare a frozen Laya context model with explicit rules on reviewed data.
- [ ] Reproduce signals in offline preparation and LEAN with auditable settings.
- [ ] Publish negative, inconclusive, and positive outcomes with equal traceability.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Live trading or paper-account promotion | Requires separate readiness authorization and Story 17 risk review. |
| Online learning during a replay | Invalidates frozen-run reproducibility. |
| New GPU service or mandatory Torch inside LEAN | Local precomputed inference is the proposed first deployment. |
| YOLO training, Jev integration, or new news-data acquisition | Separate ideas, not required for candle/context evaluation. |
| Rewriting F5/F6 or introducing Bigalow exit orders now | Story 17 owns risk; exit-policy experiments require a separate explicit scope decision. |
| Every named chart formation at once | Ambiguous formations require definition and labels before executable tasks. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Complement versus replacement | Keep explicit rules; evaluate Laya as a separate optional context provider. | User explicitly requested coverage beyond TA-Lib. | Yes |
| Adaptive behavior | Retrain between experiments; freeze every evaluated artifact. | User wants repeatable bounded decisions. | Yes |
| Rollout | Rules first, then Laya in advisory/shadow mode. | Isolates integration risk from model quality. | Proposed; user can override |
| Deployment | Precompute per-bar Laya results locally; LEAN consumes a verified immutable cache. | No runtime network or heavy model dependency in LEAN. | Proposed |
| Catalog slice | Preserve six legacy labels; add doji variants, spinning tops, harami, hanging man, inverted hammer, piercing, dark cloud, and kicker candidates after source review. | Bounded major-signal expansion; exact label/function mapping is a T1 deliverable. | Proposed |
| Sequence slice | Implement doji then engulfing with next-closed-bar confirmation; broader J-hook/fry-pan/dumpling/cradle/scoop/crunch forms remain ledger candidates. | Provides a testable first sequence without inventing subjective geometry. | Proposed |
| Timing | Closed bars only, explicit UTC decision timeframe; no intrabar opening/stop tactics in this slice. | Existing canonical clock supports this contract. | Proposed |
| Input bounds | Maximum context history 256 closed bars; model input window configured within that bound; reject token truncation. | Accommodates SMA(200) context while bounding storage; token budgets differ by checkpoint. | Proposed |
| Model acceptance | Register task-specific recognition/calibration criteria before fitting; no automatic profit or accuracy target derived from speaker anecdotes. | We lack independently labeled data and a justified universal threshold. | Proposed |
| Bigalow formulas | T1 resolves definitions or marks them deferred; unresolved rules cannot enter training or execution. | OCR/transcript ambiguities must not become guessed labels. | Proposed |
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
4. IF a model, feature order, catalog, timeframe, context policy, or calibration contract mismatches the strategy THEN startup SHALL reject it with a retraining or rematerialization instruction before replay. (CND-14)
5. WHEN an observation is persisted THEN the audit SHALL record pattern IDs, context, confirmation time, mode, provider provenance, recommendation, veto, and final action separately. (CND-15)
6. WHEN the viewer renders a new observation THEN it SHALL distinguish detected patterns from the filter recommendation and final trade action. (CND-16)
7. WHEN the viewer renders an old artifact THEN it SHALL identify unavailable new fields as historical omissions rather than fabricated detections. (CND-17)

**Independent Test**: A bullish detection with a final SELL remains visibly three
distinct facts; a required-mode veto never cancels or delays an existing stop.

### P2: Frozen learned context and controlled experiments

As a researcher, I want to specialize Laya on reviewed sequences and compare it
with rules while keeping reproducibility and outcome claims independently tested.

**Acceptance Criteria**:
1. WHEN labels are prepared THEN the dataset manifest SHALL distinguish reviewed labels, ambiguous exclusions, and rule-generated weak labels. (CND-18)
2. WHEN a training split is validated THEN the validator SHALL reject any shared input window or outcome horizon across its train/calibration/test boundaries. (CND-19)
3. IF a Laya input exceeds its pinned token budget or its output violates the bounded schema THEN inference SHALL fail explicitly without silent truncation or rule fallback. (CND-20)
4. WHEN a model artifact is published THEN its manifest SHALL record weight/tokenizer/schema hashes, runtime/device settings, seed, split hashes, and calibration provenance. (CND-21)
5. WHEN identical input is evaluated 100 times in the pinned environment THEN the repeatability check SHALL require identical labels and maximum absolute probability difference of 0.000001. (CND-22)
6. WHEN a cache key is reused with different content THEN materialization SHALL refuse replacement rather than overwrite the prior artifact. (CND-23)
7. IF an enabled learned provider has a missing, corrupt, mismatched, duplicate, or stale cache row THEN replay SHALL stop with a diagnostic rather than substitute a rule output. (CND-24)
8. WHEN a backtest is reported THEN its result SHALL include the complete resolved filter parameters and input/code/model/protocol hashes, including disabled filters and failed attempts. (CND-25)
9. WHEN recognition results are published THEN the report SHALL separate per-label recognition/calibration/coverage metrics from cost-adjusted trading outcomes and label modern-checkpoint historical replay as retrospective. (CND-26)

**Independent Test**: A fixed reviewed dataset yields a reproducible recognition
report; tampering with one cache row prevents replay. Laya may fail the research
acceptance criteria: that is a valid reported outcome, not a reason to tune on test.

## Edge Cases

All require Gherkin acceptance examples in the producing task: flat bars,
zero-range normalization, missing bars, duplicate/out-of-order timestamps,
overlapping opposite-polarity patterns, neutral-only hits, token overflow,
unknown IDs, stale confirmation, cache collision/partial write, and legacy data.
No production input is silently repaired. Synthetic fixtures prove mechanics
only; they are never presented as market-performance evidence.

## Implicit requirement dimensions

| Dimension | Resolution |
| --- | --- |
| Input validation and bounds | CND-03/04/20; max 256 bars, finite positive valid OHLC, UTC closed bars. |
| Failure and partial failure | CND-20/23/24; temporary artifact plus atomic publication; invalid row stops run. |
| Idempotency and duplicates | CND-23/24; content-addressed key, identical reuse allowed, conflicting bytes rejected. |
| Auth and rate limits | N/A: no new server, broker, or remote API in the scoped runtime. |
| Concurrency and ordering | CND-03/05/23; state isolated by run/pair/timeframe, ordered bars, single writer per artifact. |
| Lifecycle and expiry | CND-08/24; next-bar sequence expires; immutable artifacts retained, no automatic deletion. |
| Observability | CND-15/25; decisions, rejection reason, manifests, and failed attempts recorded. |
| External failure | CND-20/24; installation/download is preparation, not an automatic replay fallback. |
| State integrity | CND-03/07/08/13; invalid data does not consume state; deterministic expiry; independent protection. |

## Requirement Traceability

| Requirement ID | Story | Tasks | Status |
| --- | --- | --- | --- |
| CND-01 | P1 evidence | T1, T3 | In Tasks |
| CND-02 | P1 evidence | T2, T3 | In Tasks |
| CND-03 | P1 evidence | T2, T4, T7 | In Tasks |
| CND-04 | P1 evidence | T3, T4 | In Tasks |
| CND-05 | P1 evidence | T3, T4, T5, T7 | In Tasks |
| CND-06 | P1 evidence | T4 | In Tasks |
| CND-07 | P1 evidence | T5 | In Tasks |
| CND-08 | P1 evidence | T5 | In Tasks |
| CND-09 | P1 evidence | T3, T6, T7, T9 | In Tasks |
| CND-10 | P1 evidence | T7, T10, T21 | In Tasks |
| CND-11 | P1 decisions | T6, T21 | In Tasks |
| CND-12 | P1 decisions | T6 | In Tasks |
| CND-13 | P1 decisions | T7, T21 | In Tasks |
| CND-14 | P1 decisions | T8, T9, T10, T21 | In Tasks |
| CND-15 | P1 decisions | T11, T12 | In Tasks |
| CND-16 | P1 decisions | T13, T14 | In Tasks |
| CND-17 | P1 decisions | T12, T14 | In Tasks |
| CND-18 | P2 research | T15 | In Tasks |
| CND-19 | P2 research | T15, T16, T18 | In Tasks |
| CND-20 | P2 research | T17 | In Tasks |
| CND-21 | P2 research | T17, T18, T19 | In Tasks |
| CND-22 | P2 research | T19 | In Tasks |
| CND-23 | P2 research | T20 | In Tasks |
| CND-24 | P2 research | T20, T21 | In Tasks |
| CND-25 | P2 research | T22, T23, T24 | In Tasks |
| CND-26 | P2 research | T16, T19, T23, T24 | In Tasks |

Coverage: 26 requirements mapped; zero unmapped; zero implemented or verified.

## Success Criteria

- [ ] Every requirement has exact behavioral evidence and an atomic task commit.
- [ ] Legacy regression and native/offline parity pass before new runs launch.
- [ ] All attempted variants and parameters are reported without test-set tuning.
- [ ] Independent final verifier passes the outcome review and fault sensor.

Software success does not require a profitable strategy. Deployment promotion is
not implied by either model accuracy or completion of this plan.
