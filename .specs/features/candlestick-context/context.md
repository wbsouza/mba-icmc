# Candlestick context decisions

Gathered and amended: September 28, 2026. Status: planning only; implementation
remains unstarted. Story 22 owns the extension originating in historical Story 13.

## Feature Boundary

The active plan covers deterministic candlestick geometry, closed-bar context,
confirmation, F3 policy, compatible evidence and rules-only evaluation. The user
explicitly DEFERRED Laya now; it is not an optional active provider or release gate.
Keep 19 active tasks (T1–T16, T22–T24) and 21 active requirements (CND-01–19,
CND-25, CND-26). Preserve T17–T21 and CND-20–24 in deferred historical tables.

## Implementation Decisions

- Preserve frozen six-label legacy behavior and existing filter combinations.
- Keep geometry, point-in-time context, later confirmation, recommendation and
  final action distinct. Confirmation is available only at its actual closed bar.
- Entry vetoes never disable or delay existing position protection or F5/F6.
- Retain reviewed recognition labels and leakage-free evaluation under CND-18/19
  independently of any learned model. Separate weak labels and ambiguous exclusions.
- Record full per-filter parameters beside every result, including disabled
  filters, failures and ordinary F7 model provenance where enabled.
- Keep the book, presentation, webinar transcript and EarnForex references.
  Source typos matter when they change rule geometry, thresholds or timing.
- Use three sequential Story 22 phases: T1–T6, T7–T14, then T15–T16 plus T22–T24.
  T22 depends on T16. No active task depends on a deferred task.

## Parallel implementation boundaries

Follow the coordinator-owned [Stories 19/21/22 plan](../../../algo-suite/docs/stories/parallel-19-21-22.md).
Main owns coordination and Story 19; a separate agent owns Story 21; lane C owns
rules/perception/F3. This amendment creates no implementation worker or worktree.

Story 19 owns `f7_meta_learner.py` fitting changes first; Story 22's T9 encoder
integration follows its tested handoff serially. `training.py`,
`signal_contract.py`, `market_signals.py`, `decision_recorder.py`, schema/ingestion
and viewer changes require a coordinator integration lease. One editor owns
monograph changes. Shared-plan contract, integration and evidence gates must be
accepted before the corresponding lane handoff; they do not activate Laya.

## Assumptions and source-definition review

The spec retains proposed bounded catalog/sequence definitions and a maximum
history of 256 closed bars. T1 must resolve source ambiguity with positive,
negative and equality-boundary examples or leave that rule explicitly deferred.
T16 registers rules-recognition metrics and evaluation boundaries before outcomes
are inspected. Historical session-2 findings stay exploratory.

## Deferred history

The initial proposal combined rules with a local Laya adapter, specialization,
repeatability evaluation and immutable per-bar cache consumed by LEAN. Direct
runtime inference was also discussed. The current user amendment supersedes both
options: T17–T21 and CND-20–24 are DEFERRED, including model training, token budgets
and real-checkpoint smoke checks. Reactivation needs a separate scope decision.

Visual YOLO training, live services, online adaptation, new exit-order policies
and broader undefined Bigalow formations remain outside this slice. Normal F7
compatibility and Story 19 fitting work remain distinct from the deferred Laya work.
