# Candlestick context design

Status: proposed, planning only. The user explicitly deferred implementation.
Read [spec.md](spec.md) and [context.md](context.md) before execution. No new
architecture decision is approved by the existence of this document.

## Architecture

Use one causal deterministic rule producer for offline preparation and LEAN.
Keep the old single-label mode intact. Laya is DEFERRED; no learned-provider
adapter, training pipeline or inference cache belongs to the active design.

```text
Canonical closed UTC bars
  -> versioned multilabel geometry
  -> causal context + next-bar confirmation
  -> F3 advisory / required-entry policy -> existing chain and risk protection
                   |
                   +-> decision evidence -> results database -> viewer

Reviewed sequences -> purged chronological evaluation partitions
  -> registered rules-only comparisons -> recognition and trading evidence
```

Reviewed recognition data and leakage checks remain active independently of
learned models. Existing F7 retains normal model provenance and compatibility.

## Reuse and proposed boundaries

Paths in this table are relative to `algo-suite/`. New modules are proposals,
not claims that those files exist today.

| Component | Existing integration point | Change |
| --- | --- | --- |
| Pattern contracts/catalog | `algo-backtest/src/algo_backtest/perception/candlestick.py` | Retain legacy implementation; add separate immutable evidence and expanded detector modules. |
| Context/sequence | New pure modules in `perception/` | Evaluate only available closed bars; keep geometry separate from confirmation. |
| Decision policy | `algo-backtest/src/algo_backtest/chain/filters/f3_pattern.py` | Explicit legacy/advisory/required-entry configuration. |
| Native signal production | `algo-backtest/src/algo_backtest/chain/market_signals.py` | Shared producer and independently scoped state per stream. |
| Compatibility | `algo-backtest/src/algo_backtest/signal_contract.py` | Hash the complete resolved signal contract, not only detector name. |
| F7 feature encoding | `algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py` | Versioned ordered pattern/context features; retain old encoding. |
| Training rows | `algo-backtest/src/algo_backtest/training.py` | Consume identical evidence with identical availability times. |
| Recording | `algo-backtest/src/algo_backtest/chain/decision_recorder.py` | Serialize evidence independently of recommendation/action. |
| Analysis ingestion | `algo-analyze/src/algo_analyze/resultsdb/decisions.py` | Additive, versioned ingestion; historical omissions remain null. |
| Viewer | `algo-viewer/src/model/patterns.ts`, `algo-viewer/src/views/TradeDrawer.tsx` | Catalog metadata and explicit decision evidence. |
| Reviewed recognition dataset | New `algo-backtest/src/algo_backtest/candle_evaluation/dataset.py` | Validate reviewed/weak/excluded labels and causal evaluation partitions without model fitting. |
| Rules experiment runner | New `tools/candlestick_experiments.py` | Execute the registered deterministic matrix and produce recognition metrics plus separate trading evidence. |

## Parallel ownership and handoff gates

The coordinator owns the [shared Stories 19/21/22 plan](../../../algo-suite/docs/stories/parallel-19-21-22.md).
Main owns coordination and Story 19; a separate agent owns Story 21; lane C owns
Story 22. This is future implementation planning, not a worker/worktree launch.

| Surface | Future owner and handoff |
| --- | --- |
| Rule ledger, new candle perception modules, `f3_pattern.py` | Lane C (Story 22), with co-located Gherkin tests. |
| `chain/filters/f7_meta_learner.py` | Story 19 owns fitting changes first; after its tested contract handoff, Story 22 T9 integrates the encoder serially. No simultaneous edits. |
| `training.py`, `signal_contract.py`, `chain/market_signals.py`, `chain/decision_recorder.py` | Coordinator integration lease before T7/T8/T10/T11; record agreed interfaces, base revision and regression evidence in the shared plan. |
| Results schema/ingestion and viewer | Coordinator integration lease before T12–T14; agree additive fields and old-artifact behavior with Stories 19/21. |
| Monograph | One coordinator-designated editor; T24 supplies verified prose/tables to that editor. |

Before Phase 1, the coordinator records lane boundaries and evidence/availability
contracts in the shared plan. Before Phase 2, confirm signal contracts, F3/chain
semantics and protection scheduling with Story 21, then acquire each shared-file
lease. Story 19's fitting handoff is a required gate before T9. After T14, the
coordinator accepts legacy, native/offline parity and old/new audit/viewer evidence
before Phase 3. T22 requires T16 and a registered rules-only matrix; no deferred
task gates execution. T24 waits for the single monograph editor's handoff window.

## Evidence contract

An observation carries schema/catalog versions, pair, UTC close, timeframe,
history count, provider status and stable ordered pattern hits. Each hit records
ID, polarity (including neutral), rule version and its own readiness status.
Overall readiness must not hide a short-lookback hit while a longer recognizer
warms up. Context fields include readiness, EMA(8), configured stochastic
definition, causal trend/level evidence, and normalized distance where defined.

Exact stochastic smoothing, level proximity, trend lookback, gap definition,
kicker correspondence and equality boundaries are T1 outputs, not implied by
the names. Do not equate a TA-Lib function with an author's definition without
boundary examples. The maximum history proposal is 256 bars; reject configurations
requiring more and never silently shorten a window.

Configuration separates detector mode, enabled catalog, context parameters,
sequence rules and decision policy, with deterministic rule provenance. Canonical
serialization and a versioned hash cover these fields plus feature order and
existing F7 model/calibration identity where enabled; these are not Laya artifacts.
Old artifacts without these fields use only the explicit legacy compatibility
path; they cannot be admitted to a new feature schema.

## Timing and state

Validate a complete bar before advancing any recognizer. Duplicate, reversed,
non-UTC, malformed or incomplete observations fail explicitly. Scheduled market
closures are not fabricated candles; the manifest records the calendar policy.
Unexplained missing expected bars invalidate the stream. Confirmation refers to
the next valid closed bar under that policy, never a future open retrospectively.

For the initial sequence: IDLE -> doji candidate -> confirmed or expired at the
next closed bar. Confirmation belongs to the later bar. A bar may expire an old
candidate and create a new one, but cannot confirm itself. Opposing simultaneous
signals remain visible and cannot satisfy an exactly-one-direction entry rule.

All feature values have an availability timestamp. Offline labels may use a
future outcome for evaluation, but that outcome and its horizon never enter the
input at the earlier decision time. Prefix invariance tests enforce this boundary.

## Policy and risk separation

Legacy mode preserves existing six-label behavior. Advisory mode can recommend
or abstain but never veto. Required mode grants entry eligibility only to one
confirmed direction satisfying registered context; warmup, neutral-only and
conflicting evidence reject entry with distinct reasons.

Entry eligibility must not bypass F5/F6 or interrupt existing protective order
management. Native integration must test a held position while new entries are
vetoed. No Bigalow-inspired exit orders or stop changes are part of this slice.
If the current callback order cannot preserve protection, stop for design review
before enabling required mode; do not silently widen the risk-policy scope.

## Reviewed dataset and evaluation lifecycle

T15 retains reviewed labels, weak rule labels and ambiguous exclusions with
separate provenance and adjudication. Purge overlapping input windows and outcome
horizons across chronological development, reserved threshold-calibration and
final-evaluation partitions. Rules derived from source definitions are frozen
before final evaluation; any data-derived normalization uses development only.
Calibration here means rule-threshold review in a reserved partition, not learned
probability calibration. Do not tune on the final evaluation set. CND-18/19 apply
even when no model is fitted.

T16 registers label support, costs, windows, metrics, feasible dependence-aware
statistical inference, trial budget and stop criteria. T22 validates that registration, calculates per-label recognition and
coverage metrics and records every rules experiment attempt before execution.
Run collisions and incomplete/failed attempts remain visible without overwriting
earlier evidence. Metrics belong to the bounded runner's attempt bundle and its
co-located tests; a separately reusable metric component requires a task split
and plan revalidation. Existing F7 provenance follows the shared integration contract.

## Deferred design archive

The earlier Laya proposal covered a pinned local adapter (T17), specialization
(T18), learned recognition/calibration/repeatability (T19), immutable output cache
(T20) and replay provider (T21). All five are DEFERRED with CND-20–24, outside
active components, dependencies, tests and rollout. Its historical reference links
remain in the Story 22 brief. Reactivation requires a separate scope amendment.

## Experiments and reporting

Register exact windows, costs, seeds, thresholds and trial budget before
launching. Compare legacy, expanded geometry and geometry-plus-context under the same other
filters. Quote activity is a separately registered factor, not a bundled change.
Use recognition metrics (per-label precision/recall, multilabel errors and coverage)
separately from cost-adjusted return, drawdown and trade-count metrics.

Report every attempt with all resolved filter settings, including disabled
filters, dataset/config/code/protocol hashes, existing F7 model provenance when
enabled, failures and exclusions. Previously inspected periods remain exploratory;
a new registration cannot turn them into an untouched holdout.
No book anecdote, accuracy score or profitable backtest authorizes live trading.

## Verification and rollout

Use Gherkin-first tests alongside each component, frozen legacy fixtures,
synthetic boundary fixtures, prefix invariance and native/offline parity. Extend
the existing architecture/coverage/CRAP/mutation gates to the new pure modules.
Viewer acceptance tests cover both old and new artifacts and a detection whose
direction differs from the final action. Synthetic data proves mechanics only.

The active rollout consists of Phase 1 T1–T6, Phase 2 T7–T14 and Phase 3
T15–T16 plus T22–T24: reviewed dataset, protocol, runner, evidence and monograph.
No active task depends on T17–T21. Final completion requires the skill's independent
Verifier and discrimination sensor, after implementation is separately authorized.
