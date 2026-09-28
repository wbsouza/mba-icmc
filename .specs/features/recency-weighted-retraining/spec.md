# Rolling and exponentially weighted retraining specification

Status: draft, September 28, 2026. Story 19 (remote allocation checked).
Planning only. The user replaced the request to execute an experiment with a
request to create this story and implementation plan.
The user subsequently confirmed a full adaptive cycle: consume data, train from
newly available evidence, and load the resulting models for future transactions.

## Problem Statement

The user observed declining trade performance over time and proposed sliding
training windows with smoothly fading historical influence. That observation
does not establish model drift or guarantee that retraining will help. Session 2
used a fixed 2015 model and January 2016 calibration across the following trading
year. This story tests retraining policy independently of new candlestick rules.

As a researcher, I want causal, reproducible model refreshes so I can compare
frozen, rolling and exponentially weighted training without resetting the
account or selecting only successful trades.

## Goals

- [ ] Implement sample weighting and scheduled model/threshold replacement.
- [ ] Compare five registered policies on identical historical market inputs.
- [ ] Report parameters, uncertainty, failures and limitations in the monograph.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Running or implementing now | Current authorization is planning only. |
| New candlestick/volume rules or Laya | Separate Story 22; would confound this comparison. Laya is deferred by the user. |
| Live-account deployment | Backtest evidence cannot authorize live trading. |
| Averaging model parameters or smoothing predictions | Exponential weights apply to training observations. |
| Online per-tick learning or drift-triggered schedules | Fixed monthly schedule keeps the initial study bounded. |
| Tuning exits, sizing, risk limits or costs | Hold these fixed across policies. |
| Fixing TD-71 in this story | Existing execution defect has its own owner; affected runs must fail visibly. |
| Exhaustive half-life/window search | Five policies and one proposed half-life, not an optimization campaign. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Deliverable | Story, design, test-backed tasks; no execution | Latest user instruction | Yes |
| Exponential meaning | Observation weights, not parameter/prediction averaging | Matches preceding discussion | Proposed |
| Market/cell | EUR/USD H1 q10 price-only configuration from session 2, frozen by hash | One low-cost comparison without news-provider changes | Proposed |
| Policies | F frozen; Q thresholds only; R rolling uniform; U expanding uniform; E expanding exponential | U versus E isolates weighting on identical row support | Proposed |
| Cadence | UTC month starts; one-day preparation embargo | Deterministic timing and label availability buffer | Proposed |
| Fit/calibration spans | R uses 180-day family fit; other fresh fits expand from 2015-03-02; separate 30-day combiner and 30-day threshold spans | Keeps stacking and threshold selection apart | Proposed |
| Exponential half-life | 60 elapsed calendar days in both fitting stages, independently normalized to mean one | Smooth forgetting without changing total sample-weight scale | Proposed, not optimality claim |
| Failure | Reject the complete candidate before replay; no last-good-model fallback | Avoid silently changing the assigned policy | Proposed |
| Initial support thresholds | Family fit >=1000 rows, >=50/class and effective N >=200; combiner >=100 rows, >=20/class and effective N >=50; threshold >=100 rows | Conservative feasibility checks, not a power calculation | Proposed |
| Study dates | 2016-03-01 through 2017-02-28, exploratory only | Already inspected; fresh confirmation requires other data | Proposed |
| Lifecycle | Consume -> mature labels -> fit -> validate -> publish -> load on demand -> future decisions | User requested an adaptive full cycle | Yes |
| Compute | Host-side cycle coordinator and trainer; portable bundles loaded on demand by LEAN | Keeps training dependencies outside the container | Proposed |
| Publication | Plan now; methodology and verified results later | Never present proposed execution as empirical evidence | Yes |

**Open questions:** none unrecorded. All proposed defaults require review.
The [review disposition](../../../algo-suite/docs/stories/in-progress/19-adaptive-recency-retraining/review-disposition.md)
records conflicting review requests explicitly; T1 must approve those choices
before freezing the protocol. Planning this lane does not approve the defaults.
T1 freezes exact resolved configuration, data availability, inference settings
and run budget before any new fitting. If these defaults are infeasible, amend
the protocol with reasons before examining comparative outcomes.

## User Stories

### P1: Causal and reproducible training

**Acceptance Criteria**:
1. WHEN an epoch is prepared THEN the splitter SHALL admit only observations available in its assigned span whose non-null label_time is strictly before that span's end. (RWT-01)
2. IF timestamps, row ordering, duplicate keys, half-life, window bounds or configuration are invalid THEN preparation SHALL reject them before fitting or writing an artifact. (RWT-02)
3. WHEN the monthly schedule is created THEN its half-open deployment intervals SHALL cover the registered evaluation span without gaps or overlaps. (RWT-03)
4. WHEN exponential weights are requested THEN raw weights SHALL equal 2^(-age_days/half_life_days), with age measured from feature availability to the stage cutoff in elapsed UTC days. (RWT-04)
5. WHEN weights are passed to a fitting stage THEN they SHALL be normalized independently within that stage to sum to its row count. (RWT-05)
6. IF row counts, per-class counts or effective N violate registered minima THEN preparation SHALL reject the epoch with measured and required counts. (RWT-06)
7. WHEN weighted family models are fitted THEN each LightGBM fit SHALL receive the row-aligned family-stage weights. (RWT-07)
8. WHEN the logistic combiner is fitted THEN it SHALL receive only out-of-sample family predictions and the row-aligned combiner-stage weights. (RWT-08)
9. WHEN training observations are selected THEN their eligibility SHALL be independent of trade execution, veto status and realized trade profit. (RWT-09)
10. WHEN q10 thresholds are computed THEN they SHALL use unweighted 0.10/0.90 linear quantiles from the separate prior threshold span and reject non-finite or non-increasing thresholds. (RWT-10)

**Independent Test**: Tiny dated fixtures yield raw weights 1, 0.5 and 0.25
at ages 0, h and 2h, mean-one normalized weights 12/7, 6/7 and 3/7,
and effective N 7/3. Future-label and inverted train/combiner fixtures expose
look-ahead and in-sample stacking leakage.

### P1: Scheduled replay without account resets

**Acceptance Criteria**:
1. WHEN a bundle is published THEN its immutable manifest SHALL bind policy, epoch spans, row/input/config hashes, weight summaries, seed, dependency versions, model and threshold identities. (RWT-11)
2. WHEN a decision selects an epoch THEN the selector SHALL return only the bundle whose deployment interval contains that decision timestamp. (RWT-12)
3. WHEN a new epoch activates THEN the engine SHALL preserve equity, positions, order IDs, entry plans, indicator state and daily/weekly risk anchors. (RWT-13)
4. WHEN a position spans an epoch boundary THEN its original protection SHALL continue at minute granularity without an artificial close or reopening. (RWT-14)
5. IF a required bundle is missing, corrupt, conflicting or incompatible THEN replay SHALL fail explicitly without substituting another epoch or policy. (RWT-15)
6. WHEN a decision is recorded THEN it SHALL identify the active model/threshold epoch separately from any open trade's entry epoch. (RWT-16)
7. WHERE no retraining schedule is configured the engine SHALL preserve existing single-model predictions and decisions on frozen regression fixtures. (RWT-17)
8. WHEN new source data is consumed THEN the cycle SHALL advance a recorded availability watermark only after the batch has been validated and persisted. (RWT-23)
9. WHILE an observation's outcome is not yet available the cycle SHALL retain it as pending and exclude it from supervised fitting. (RWT-24)
10. WHEN a registered retraining boundary is reached THEN the coordinator SHALL run the consume-to-publish cycle exactly once for that policy and boundary. (RWT-25)
11. WHEN a validated replacement becomes eligible THEN the loader SHALL activate it only for subsequent decision events and leave earlier recorded decisions unchanged. (RWT-26)
12. IF an adaptive cycle fails THEN the coordinator SHALL record its failed stage and prevent replay from silently advancing with an unregistered fallback. (RWT-27)
13. WHEN an eligible bundle is requested THEN the loader SHALL deserialize it on demand with a configurable bounded cache that retains the currently active bundle. (RWT-28)
14. WHEN the complete cycle is repeated with identical pinned inputs and runtime THEN it SHALL produce identical semantic model payload hashes and decision payloads, excluding only separately recorded volatile telemetry. (RWT-30)

**Independent Test**: A native LEAN fixture crosses a month boundary while
holding a trade; the model changes once, protective orders and risk anchors do
not reset, and an unscheduled run reproduces its legacy fixture.

### P2: Controlled comparison and monograph evidence

**Acceptance Criteria**:
1. WHEN experimental fitting or replay begins THEN the runner SHALL require a frozen registration with all five policy definitions, exact dates, costs, seed, analysis contrasts and finite trial budget. (RWT-18)
2. WHEN an attempt finishes or fails THEN its ledger SHALL retain the status, reason, full resolved filter parameters and code/data/config/model/threshold/protocol identities. (RWT-19)
3. WHEN policies are compared THEN analysis SHALL use paired UTC-daily equity over the same dates rather than treating trades, epochs or repeated seeds as independent market replications. (RWT-20)
4. WHEN previously inspected dates are reported THEN the report SHALL label their findings exploratory even if the new protocol was registered before its own runs. (RWT-21)
5. WHEN the monograph describes this study THEN it SHALL distinguish proposed methodology from completed results and trace every reported numerical result to an immutable artifact. (RWT-22)
6. WHEN prediction quality is reported THEN analysis SHALL compare E and U on identical mature evaluation-row keys and publish log-loss, Brier score, directional accuracy and sample counts separately from trading returns. (RWT-29)

**Independent Test**: A miniature report includes a failed candidate, every
policy's settings and the exploratory label; an unavailable inferential result
remains unavailable and cannot be converted into a favorable claim.

## Edge Cases

Cover weekend/month/year boundaries, missing initial history, incomplete bars,
features available after bucket start, labels exactly at a cutoff, duplicate
rows, one-class spans, extreme finite half-lives, weight underflow, threshold
ties, partial bundle publication, missing epochs, trades crossing updates,
risk-limit vetoes, bankruptcy and flat equity. Fixtures demonstrate mechanics,
not profitability. Do not fabricate market or training data.

## Implicit requirement dimensions

| Dimension | Resolution |
| --- | --- |
| Input validation and bounds | RWT-01/02/06; explicit UTC bounds and sample feasibility. |
| Partial failure | RWT-11/15/19; atomic publication, failed-run records, no fallback. |
| Retry/idempotency | Identical bundle reuse allowed; same identity with different bytes rejected. |
| Auth/rate limits | N/A: local offline preparation/replay, no new service or broker access. |
| Concurrency/order | One writer per artifact, sequential epoch activation; bounded preparation workers. |
| Lifecycle | Retain bundles and ledgers; no deletion or overwrite of historical runs. |
| Observability | RWT-16/19; epoch-aware decisions and all attempted configurations. |
| External dependency failure | Missing library/data/container blocks the gate; no network in replay. |
| State transitions | RWT-12/13/14; atomic model/threshold switch without engine-state reset. |

## Requirement Traceability

| Requirement ID | Story | Tasks | Status |
| --- | --- | --- | --- |
| RWT-01 | P1 training | T3, T9 | In Tasks |
| RWT-02 | P1 training | T3, T4 | In Tasks |
| RWT-03 | P1 training | T3, T11 | In Tasks |
| RWT-04 | P1 training | T4 | In Tasks |
| RWT-05 | P1 training | T4, T5, T6 | In Tasks |
| RWT-06 | P1 training | T4, T9 | In Tasks |
| RWT-07 | P1 training | T5 | In Tasks |
| RWT-08 | P1 training | T6 | In Tasks |
| RWT-09 | P1 training | T3, T9 | In Tasks |
| RWT-10 | P1 training | T8 | In Tasks |
| RWT-11 | P1 replay | T7, T9, T14 | In Tasks |
| RWT-12 | P1 replay | T11, T12 | In Tasks |
| RWT-13 | P1 replay | T12 | In Tasks |
| RWT-14 | P1 replay | T12 | In Tasks |
| RWT-15 | P1 replay | T7, T11, T14 | In Tasks |
| RWT-16 | P1 replay | T13 | In Tasks |
| RWT-17 | P1 replay | T5, T6, T12 | In Tasks |
| RWT-18 | P2 evidence | T1, T15, T18 | Implemented (T1) |
| RWT-19 | P2 evidence | T14, T15, T16, T18 | In Tasks |
| RWT-20 | P2 evidence | T16 | In Tasks |
| RWT-21 | P2 evidence | T1, T16, T17, T18, T19 | Implemented (T1) |
| RWT-22 | P2 evidence | T17, T19 | In Tasks |
| RWT-23 | P1 replay | T2, T10 | Implemented (T2) |
| RWT-24 | P1 replay | T2, T9 | Implemented (T2) |
| RWT-25 | P1 replay | T10, T15 | In Tasks |
| RWT-26 | P1 replay | T10, T11, T12 | In Tasks |
| RWT-27 | P1 replay | T10, T15 | In Tasks |
| RWT-28 | P1 replay | T11 | In Tasks |
| RWT-29 | P2 evidence | T1, T16 | Implemented (T1) |
| RWT-30 | P1 replay | T9, T12 | In Tasks |

Coverage: 30 requirements, all mapped; the Status column tracks each task. RWT-29/30
make the review's prediction and repeatability evidence explicit; original IDs
are retained.

## Success Criteria

- [ ] All applicable behavioral gates and independent verification pass.
- [ ] Five policies produce audited results or explicit failed/unavailable outcomes.
- [ ] Monograph reports actual evidence and limitations without a profit guarantee.

A negative or inconclusive experiment is a valid research outcome.
