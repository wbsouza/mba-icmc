# Candlestick context implementation plan

**Status**: Draft for review. Planning only, explicitly confirmed by the user.
All 19 active tasks (T1–T16, T22–T24) are pending. T17–T21 are DEFERRED.
No engine changes, dependency installation, training, experiments or agents are
authorized by this planning amendment.

**Design**: [design.md](design.md). **Requirements**: [spec.md](spec.md).
This is the canonical task checklist for Story 22; Story 13 is historical.
Active scope: deterministic rules only, with reviewed recognition/evaluation data.
Laya is explicitly DEFERRED, not an optional active implementation path.

## Execution Protocol

For future implementation, activate **tlc-spec-driven** by name and follow its
Execute flow and Critical Rules. If unavailable, STOP and tell the user.
Read its implementation reference and revalidate this plan before starting.
The current user request stops at planning; do not enter Execute now.

Before any future execution, obtain scope/design approval and confirm tool and
skill preferences. Proposed tools for every task: CodeGraph for code discovery,
shell for checks, apply_patch for edits; skill tlc-spec-driven, plus docs-writer
for documentation tasks. Check installed capabilities rather than invent APIs.
Future Stories 19/21/22 implementation can proceed in parallel under the
[coordinator-owned plan](../../../algo-suite/docs/stories/parallel-19-21-22.md).
Within lane C, phases and tasks stay sequential. No worker or implementation
worktree is created now. Main owns coordination and Story 19; a separate agent
owns Story 21.

Write Gherkin first, implement one component, run its gate, then mark its checkbox
and update requirement traceability in the same atomic Conventional Commit.
Record actual scenario counts, commands, exit codes, artifact paths and commit
hashes in the story progress file. Never mark a task done for unrun tests.
Remote publication requires authorization applicable at execution time.

After the last implementation commit, run a fresh independent Verifier:
spec-anchored expected outcomes plus behavioral fault injection in isolated
copies/worktree, no stash. It writes validation.md with per-requirement file:line
evidence, diff range and PASS/FAIL. Run the skill completion validator. Surviving
faults become fix tasks; at most three fix/reverify iterations before escalation.
No validation.md is created during planning.

## Parallel ownership and handoff gates

The [shared plan](../../../algo-suite/docs/stories/parallel-19-21-22.md) owns
cross-story contracts, integration leases and acceptance of each handoff.

| Surface / tasks | Ownership and prerequisite |
| --- | --- |
| Rules/perception/F3, T1–T6 | Lane C owns Story 22. Freeze evidence schema and closed-bar availability contract with the coordinator before implementation. |
| `market_signals.py` (T7), `signal_contract.py` (T8) | Coordinator integration lease; agree F3/Story 21 chain semantics and independent protection before editing. |
| `f7_meta_learner.py` (T9) | Story 19 owns fitting changes first; Story 22 integrates its encoder serially after Story 19's tested fitting/feature-contract handoff. |
| `training.py` (T10), `decision_recorder.py` (T11) | Coordinator integration lease over the agreed point-in-time and provenance contracts. |
| Results schema/ingestion (T12), viewer (T13–T14) | Coordinator integration lease; shared old/new fixtures and additive schema agreed across the three stories. |
| T15–T16, T22–T23 | Lane C rules evaluation; after T14, coordinator accepts legacy/parity/protection/audit evidence; T22 requires T16's registered matrix. |
| Monograph (T24) | One coordinator-designated editor; lane C hands over verified tables/prose and source evidence after T23. |

Each lease records the base revision, exact files, integration owner, agreed
contract and regression evidence in the shared plan; release it before another
lane edits those files. These are cross-story gates, not deferred-task dependencies.
The canonical `Depends on` fields below describe only this story's active DAG.

## Test Coverage Matrix

Generated from `algo-suite/CLAUDE.md`, `algo-suite/Makefile`,
`algo-suite/algo-backtest/Makefile`, `algo-suite/pyproject.toml`,
`algo-suite/algo-viewer/package.json` and `monografia/Makefile`; confirm before
Execute. Sampled features under `algo-suite/algo-backtest/tests/features/`:
`candlestick_detector.feature`, `f3_pattern.feature`, `closed_signal_parity.feature`,
`training_family_contract.feature`, `signal_configuration.feature`; also
`algo-suite/algo-viewer/tests/features/patterns.feature` and representative
pytest-bdd steps. Existing tests are a floor; no implementation tests were run
while preparing this amendment.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain | Gherkin/pytest-bdd unit | All branches and applicable AC/edge cases; core 100% line coverage, CRAP <=8 | algo-backtest/tests/features + tests/steps | Quick; Pure for new perception modules |
| Native | Gherkin/pytest-bdd integration | Happy/error/boundary cases, closed-bar parity and protection regression | algo-backtest/tests/steps | Full |
| Artifacts | Gherkin/pytest-bdd integration | Round-trip, old/new schema, corrupt/partial/colliding records; hand-calculated rules metrics and leakage rejection | owning package tests/features + tests/steps | Artifacts |
| Viewer | Cucumber acceptance | Old/new rendering, every new state, semantic distinction and malformed data | algo-viewer/tests | Viewer |
| Documentation | Documentation checks | Source/requirement/parameter completeness, links and evidence reconciliation | story documents / Chapter 4 | Docs, Evidence or Monograph |

Scenario counts below are proposed minima, not execution results. Before each
task, collect the existing scenario baseline; require all existing scenarios plus
the task's new cases, without silent deletions. Parametrized rows count separately.
Every code task owns its feature and steps in the same commit. Register new pure
modules in quality/mutation gates when introduced, not as an afterthought.
Documentation tasks require review/check evidence, not invented runtime tests.

## Gate Check Commands

Commands below are taken from project manifests. Run in algo-suite unless noted.
Future new test files must be collected explicitly and have nonzero scenario
counts; the workspace test target's no-tests behavior is not sufficient evidence.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Unit component | `uv run pytest algo-backtest/tests` and `make lint type` |
| Pure | Perception component | Quick plus `make check-perception` after registering its new modules |
| Full | Native wiring | `make check`; `uv run pytest algo-backtest/tests/steps/test_closed_signal_parity.py algo-backtest/tests/steps/test_minute_pnl_anchors.py -m integration`; explicitly select new native scenarios with `-m integration` |
| Artifacts | Persistence/runner | `make check`; explicitly select owning package's new BDD files, including integration marker where used |
| Viewer | UI component | `make viewer-check` |
| Docs | Planning/source/protocol | `git diff --check`; strict skill spec/tasks validators; source/Markdown-link checks |
| Evidence | Experimental report | Docs plus reconciliation with each immutable run manifest and metric artifact |
| Monograph | Chapter update | Evidence plus `make verify` from monografia |
| Build | End of each applicable phase | `make check`; Viewer for UI changes; Pure/Full for numerical/native changes; `make audit` and debt review before advancing to the next implementation task per CLAUDE.md |

Strict planning validators, from repository root:

```sh
python3 /home/wellington/.agents/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/candlestick-context/spec.md --strict
python3 /home/wellington/.agents/skills/tlc-spec-driven/scripts/validate_tasks.py .specs/features/candlestick-context/tasks.md --strict
```

Resolve the installed skill directory anew in another environment. Missing Docker,
market data, dependency wheels or network is a recorded blocked gate, not PASS.
The Monograph gate must inspect the citation scan: `make verify` prints warnings
but does not itself reject every undefined citation. Record zero undefined citations.
Do not install or download anything during this planning turn.

## Execution Plan

Three sequential phases in lane C: rules (6 tasks), integration (8), then
rules evaluation/reporting (5). Other story lanes may progress independently;
shared-file work is serialized through the coordinator's integration leases.
These phase boundaries also define the lane's future handoff units.

```text
T1 -> T2 -> T3 -> T4 -> T5 -> T6
T6 -> T7 -> T8 -> T9 -> T10 -> T11 -> T12 -> T13 -> T14
T14 -> T15 -> T16 -> T22 -> T23 -> T24
```

Release checkpoint after T14: deterministic rules and evidence UI, with coordinator
acceptance of legacy parity and independent protection. Phase 3 has five tasks:
reviewed rules dataset, registered protocol, runner, evidence and monograph.
T22 depends on T16, with no learned-provider feasibility gate. No active task
depends on T17–T21. Historical backtests do not authorize live deployment.

## Task Breakdown

### Phase 1: Source-backed explicit rules

### T1: Review and freeze the source-rule ledger

**What**: Record book PDF/printed pages, slide numbers and video times, exact geometry/context/confirmation rules, TA-Lib equivalence or differences, and optional EarnForex license/source review. Mark unsupported or ambiguous definitions deferred, including broader chart formations.

**Where**: `algo-suite/docs/stories/in-progress/22-candlestick-context-extension/candlestick-rule-ledger.md`
**Depends on**: None
**Requirement**: CND-01
**Reuses**: Source brief and timestamped video notes.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Documentation checks. One positive, one negative and one equality-boundary example for every admitted rule; each contextual threshold and Forex gap/calendar adaptation explicit.
**Gate**: Docs (commands above); record baseline and final collected/passed counts.
**Done when**:

- [x] The component meets the cited ACs and all listed cases pass its Docs gate; no existing scenarios are removed or silently skipped.
- [x] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `docs(candles): review and freeze the source-rule ledger`

### T2: Define immutable pattern evidence and configuration

**What**: Create the bounded, versioned observation/configuration component, with per-recognizer readiness, stable IDs, UTC availability times and atomic validation.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/perception/candle_contract.py`
**Depends on**: T1
**Requirement**: CND-02, CND-03
**Reuses**: Existing candlestick validation and chain model.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd unit. At least 10 BDD examples: OHLC validity, booleans, non-finite values, UTC, duplicates, ordering, bounds, unknown IDs and immutable state on rejection.
**Gate**: Quick (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Quick gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): define immutable pattern evidence and configuration`

### T3: Implement the expanded geometry catalog

**What**: Implement only T1-admitted geometry rules with multilabel output; preserve the existing detector unchanged for legacy mode. Register this pure module in the quality gate as part of its delivery.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/perception/candle_catalog.py`
**Depends on**: T2
**Requirement**: CND-01, CND-02, CND-04, CND-05, CND-09
**Reuses**: Legacy candlestick detector and TA-Lib fixture conventions.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd unit. At least three cases per admitted rule plus six shared cases for warmup, simultaneous hits, opposing hits, stable ordering, prefix invariance and frozen legacy equality.
**Gate**: Pure (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Pure gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): implement the expanded geometry catalog`

### T4: Implement causal context evaluation

**What**: Produce separately typed trend, EMA, stochastic and level/distance evidence using T1 definitions and bounded history; never infer context from future bars.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/perception/candle_context.py`
**Depends on**: T3
**Requirement**: CND-03, CND-04, CND-05, CND-06
**Reuses**: Canonical signal preparation and T2 evidence contract.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd unit. At least 10 BDD examples covering hand-calculated values, exact boundaries, warmup by indicator, flat/zero-range data, invalid configuration and unchanged prefixes.
**Gate**: Pure (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Pure gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): implement causal context evaluation`

### T5: Implement next-bar confirmation state machine

**What**: Implement the initial doji-to-engulfing sequence with candidate, confirmed and expired states; timestamp only at the confirming close.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/perception/candle_sequence.py`
**Depends on**: T4
**Requirement**: CND-05, CND-07, CND-08
**Reuses**: T2 immutable evidence and T3 catalog.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd unit. At least 8 BDD examples: both directions, failed confirmation, expiry, replacement candidate, no self-confirmation, missing expected bar and suffix invariance.
**Gate**: Pure (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Pure gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): implement next-bar confirmation state machine`

### T6: Implement explicit F3 policy modes

**What**: Add explicit legacy/advisory/required-entry policy modes and validated configuration without changing default behavior.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/filters/f3_pattern.py`
**Depends on**: T5
**Requirement**: CND-09, CND-11, CND-12
**Reuses**: Existing PatternConfig and FilterResult.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd unit. At least 10 BDD examples including advisory abstain without veto, required warmup/neutral/conflict rejection, eligible long/short and frozen legacy decisions.
**Gate**: Quick (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Quick gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): implement explicit f3 policy modes`

### Phase 2: Engine, training and evidence integration

### T7: Integrate shared closed-bar evidence into native signals

**What**: Wire the shared producer into canonical closed-bar consumption, preserving legacy and quote-activity behavior; verify protection remains independent of entry vetoes.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/market_signals.py`
**Depends on**: T6
**Requirement**: CND-03, CND-05, CND-09, CND-10, CND-13
**Reuses**: Existing closed_signal_parity and minute_pnl_anchors integration fixtures.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 8 BDD scenarios including M1/H1/H4 native parity, invalid-bar state integrity, independent streams, prefix equality and a held position whose protection runs during an entry veto.
**Gate**: Full (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Full gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): integrate shared closed-bar evidence into native signals`

### T8: Fingerprint the complete signal contract

**What**: Canonicalize and verify catalog, timeframe, context, feature order and existing F7 model/calibration identity when F7 is enabled; retain explicit legacy compatibility only. Acquire the coordinator lease; no Laya artifact identity is added.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/signal_contract.py`
**Depends on**: T7
**Requirement**: CND-14
**Reuses**: Existing require_signal_contract.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd unit. At least 9 BDD cases: equivalent serialization, each mismatch dimension, missing historical contract and actionable startup rejection before loading market data.
**Gate**: Quick (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Quick gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): fingerprint the complete signal contract`

### T9: Version the F7 pattern feature encoder

**What**: Add an ordered expanded feature schema while preserving old signed-polarity encoding for old model families. Story 19 completes its fitting changes first; accept its tested handoff in the shared plan before serial T9 integration.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py`
**Depends on**: T8
**Requirement**: CND-09, CND-14
**Reuses**: Existing FeatureFamily.PATTERN and family contract tests.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd unit. At least 7 BDD cases covering feature order, neutral/opposing hits, missing/warmup distinctions, unknown IDs, incompatible models and legacy vector equality.
**Gate**: Quick (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Quick gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): version the f7 pattern feature encoder`

### T10: Integrate evidence into training rows

**What**: Use the same producer and feature contract as native replay, recording feature availability rather than outcome-label time.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/training.py`
**Depends on**: T9
**Requirement**: CND-10, CND-14
**Reuses**: Existing training_family_contract and signal_configuration tests.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 6 BDD scenarios for native/offline equality, window edges, unavailable history, changed context hash, changed feature order and no future-label leakage.
**Gate**: Full (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Full gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): integrate evidence into training rows`

### T11: Serialize decision evidence

**What**: Record geometry, context, confirmation, provider, recommendation, veto and final action independently in a versioned decision record.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/decision_recorder.py`
**Depends on**: T10
**Requirement**: CND-15
**Reuses**: Existing decision_trail record format.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 6 BDD cases: round-trip, opposing hits, unavailable context, deterministic rule provenance, veto and bullish detection with final SELL.
**Gate**: Artifacts (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Artifacts gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): serialize decision evidence`

### T12: Ingest old and new evidence in results database

**What**: Extend the decision-ingestion component with additive schema migration if necessary; preserve old fields and represent historical omissions explicitly.

**Where**: `algo-suite/algo-analyze/src/algo_analyze/resultsdb/decisions.py`
**Depends on**: T11
**Requirement**: CND-15, CND-17
**Reuses**: Existing resultsdb schema and build conventions.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 6 BDD cases covering old/new fixtures, unknown version, missing optional historical data, corrupt new data and migration preserving prior rows.
**Gate**: Artifacts (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Artifacts gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): ingest old and new evidence in results database`

### T13: Extend viewer catalog metadata

**What**: Expose versioned IDs, source references, geometry/context explanations and correct bullish/bearish/neutral card metadata for T1-admitted rules.

**Where**: `algo-suite/algo-viewer/src/model/patterns.ts`
**Depends on**: T12
**Requirement**: CND-16
**Reuses**: Existing PatternsPage and PatternCard component conventions.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Cucumber acceptance. At least 5 Cucumber scenarios: legacy six cards, expanded catalog, unknown ID, neutral label and correct source/geometry rendering.
**Gate**: Viewer (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Viewer gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): extend viewer catalog metadata`

### T14: Render separate pattern and decision evidence

**What**: Display multiple hits, context, confirmation, provider and policy separately from final action; old runs visibly lack new evidence.

**Where**: `algo-suite/algo-viewer/src/views/TradeDrawer.tsx`
**Depends on**: T13
**Requirement**: CND-16, CND-17
**Reuses**: Existing trade drawer and T13 catalog metadata.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Cucumber acceptance. At least 6 Cucumber scenarios: historical omission, multiple/opposing hits, veto, warmup, rule provenance and detection-direction/final-action disagreement.
**Gate**: Viewer (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Viewer gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): render separate pattern and decision evidence`

### Phase 3: Rules evaluation and reporting

### T15: Validate reviewed rules-recognition data and split boundaries

**What**: Create a rules-recognition dataset validator with reviewed/weak/ambiguous provenance, label adjudication and chronological input-window/outcome-horizon overlap checks across development, reserved threshold-calibration and final evaluation; no learned model is required.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/candle_evaluation/dataset.py`
**Depends on**: T14
**Requirement**: CND-18, CND-19
**Reuses**: Existing timestamp validation and training-family conventions.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd unit. At least 9 BDD cases covering label provenance, ambiguous exclusions, duplicate sequences, overlaps on both sides of boundaries, missing lineage and a valid purged split.
**Gate**: Quick (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Quick gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): validate reviewed sequence labels and split boundaries`

### T16: Register bounded recognition and trading protocol

**What**: Register exact rules-evaluation splits, costs, seeds, label minimums, per-label precision/recall and coverage metrics, acceptance thresholds, feasible dependence-aware statistical inference, trial budget and stop criteria before final-outcome inspection. Freeze legacy/geometry/geometry-plus-context comparisons; no Laya feasibility or training gate.

**Where**: `algo-suite/docs/stories/in-progress/22-candlestick-context-extension/candlestick-method-design.md`
**Depends on**: T15
**Requirement**: CND-19, CND-26
**Reuses**: Existing method-design approach and T15 validated dataset inventory.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Documentation checks. Document checks cover every protocol field, frozen baseline matrix, embargo/purge calculation, sample support and feasibility of the registered statistical inference, and no use of speaker performance claims as acceptance evidence.
**Gate**: Docs (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Docs gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `docs(candles): register bounded recognition and trading protocol`

### T22: Record complete experiment attempts and parameters

**What**: Create one bounded evaluation runner for T16's rules-only matrix, producing one auditable attempt bundle with recognition metrics, separate trading outcomes, enabled/disabled filter settings, costs and code/data/protocol hashes plus ordinary F7 provenance when enabled. Metric calculation is internal to this runner's registered output, with its BDD checks in this task; no independently shippable metric service is included.

**Where**: `algo-suite/tools/candlestick_experiments.py`
**Depends on**: T16
**Requirement**: CND-25, CND-26
**Reuses**: Existing experiment scripts, analysis conventions and run manifests; production backtests occur only after separate execution authorization. If implementation requires a separately reusable metric component, split and revalidate the plan before proceeding rather than hiding that component or its tests in runner wiring.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 13 BDD scenarios: full manifest, disabled filters, failed run, interrupted run, existing run collision, bounded trial count, dry-run command generation, config/result identity, hand-calculated per-label precision/recall, no positives, readiness/abstention coverage, weak-label separation and recognition/trading metric separation.
**Gate**: Artifacts (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Artifacts gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): record complete experiment attempts and parameters`

### T23: Publish comparison evidence with parameters beside results

**What**: Publish the registered comparisons and recognition results with complete per-filter parameter tables, costs, sample sizes, uncertainty, exclusions and artifact links; report negative/inconclusive outcomes.

**Where**: `algo-suite/docs/stories/in-progress/22-candlestick-context-extension/candlestick-results.md`
**Depends on**: T22
**Requirement**: CND-25, CND-26
**Reuses**: T16 frozen protocol and T22 experiment artifacts.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Documentation checks. Document checks reconcile every T22 attempt, hashes, all settings and reported metrics to artifacts; no omitted failure or unregistered favorable subset.
**Gate**: Evidence (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Evidence gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `docs(candles): publish comparison evidence with parameters beside results`

### T24: Update the monograph from verified evidence

**What**: Add an evidence-backed extension section separating rules recognition and trading results, exploratory-data limitations and remaining live-readiness prerequisites. Hand the verified contribution to the single monograph editor under the shared plan.

**Where**: `monografia/chapters/04-experimental-evaluation.tex`
**Depends on**: T23
**Requirement**: CND-25, CND-26
**Reuses**: Existing Chapter 4 style and T23 report.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Documentation checks. Document checks verify every numeric claim against T23, source attribution and absence of unsupported live-readiness claims; compile and citation checks pass.
**Gate**: Monograph (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Monograph gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `docs(candles): update the monograph from verified evidence`

## Deferred task history

These stable IDs preserve the earlier Laya proposal. All are DEFERRED, outside
the active DAG, phase counts, co-location table and completion criteria. Historical
prerequisites below are archival only. Reactivation requires a new scope amendment;
no active task waits for a deferred result. CND-18/19 remain active in T15/T16.

| ID | Historical deliverable and proposed location | Historical prerequisites / requirements | Historical checks (inactive) | Status |
| --- | --- | --- | --- | --- |
| T17 | Pinned Laya adapter: verify upstream interface/license, revision and bounded I/O; `candle_learning/laya_adapter.py`. | T16; CND-20/21 | Token overflow, invalid schema/labels/scores, missing weights, manifest completeness; real pinned-checkpoint smoke. | DEFERRED |
| T18 | Frozen specialization, train-only preprocessing and reserved calibration; `candle_learning/train.py`. | T17; CND-19/21 | Split overlap, forbidden test access, seed/lineage, failed fit and tiny training smoke. CND-19 is now independently covered by active T15/T16. | DEFERRED |
| T19 | Learned recognition/calibration/repeatability; `candle_learning/evaluate.py`. | T18; CND-21/22/26 | Per-label metrics, no positives, weak labels, lineage, 100-repeat labels and probability tolerance 0.000001. Rules metrics now belong to active T22/T23. | DEFERRED |
| T20 | Immutable per-bar learned-output cache with atomic publication; `candle_learning/cache.py`. | T19; CND-23/24 | Identical reuse, collisions, interrupted publication, absent/duplicate/stale/corrupt rows. | DEFERRED |
| T21 | Cache-backed replay provider; `chain/candle_provider.py`. | T20; CND-10/11/13/14/24 | Native/offline parity, preflight, advisory abstention, no fallback/network and protection. Active rule-path coverage remains in T6–T10. | DEFERRED |

Historical paths above are relative to `algo-suite/algo-backtest/src/algo_backtest/`;
they are not proposed active modules. No optional Laya adapter, cache, training,
token-budget check or checkpoint-smoke gate is part of the active plan.

## Task Granularity Check

Each task owns one component or document; necessary wiring, feature/step tests,
and gate registration belong to that component, not separate untested work.
If implementation reveals a second independently shippable component, split and
revalidate before proceeding. Do not disguise broad rewrites as wiring.

| Task | Scope | Planning check |
| --- | --- | --- |
| T1 | One document | Atomic outcome defined |
| T2 | One define immutable pattern evidence and configuration component | Atomic outcome defined |
| T3 | One implement the expanded geometry catalog component | Atomic outcome defined |
| T4 | One implement causal context evaluation component | Atomic outcome defined |
| T5 | One implement next-bar confirmation state machine component | Atomic outcome defined |
| T6 | One implement explicit f3 policy modes component | Atomic outcome defined |
| T7 | One integrate shared closed-bar evidence into native signals component | Atomic outcome defined |
| T8 | One fingerprint the complete signal contract component | Atomic outcome defined |
| T9 | One version the f7 pattern feature encoder component | Atomic outcome defined |
| T10 | One integrate evidence into training rows component | Atomic outcome defined |
| T11 | One serialize decision evidence component | Atomic outcome defined |
| T12 | One ingest old and new evidence in results database component | Atomic outcome defined |
| T13 | One extend viewer catalog metadata component | Atomic outcome defined |
| T14 | One render separate pattern and decision evidence component | Atomic outcome defined |
| T15 | One validate reviewed sequence labels and split boundaries component | Atomic outcome defined |
| T16 | One document | Atomic outcome defined |
| T22 | One record complete experiment attempts and parameters component | Atomic outcome defined |
| T23 | One document | Atomic outcome defined |
| T24 | One document | Atomic outcome defined |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | None | Match |
| T2 | T1 | T1 | Match |
| T3 | T2 | T2 | Match |
| T4 | T3 | T3 | Match |
| T5 | T4 | T4 | Match |
| T6 | T5 | T5 | Match |
| T7 | T6 | T6 | Match |
| T8 | T7 | T7 | Match |
| T9 | T8 | T8 | Match |
| T10 | T9 | T9 | Match |
| T11 | T10 | T10 | Match |
| T12 | T11 | T11 | Match |
| T13 | T12 | T12 | Match |
| T14 | T13 | T13 | Match |
| T15 | T14 | T14 | Match |
| T16 | T15 | T15 | Match |
| T22 | T16 | T16 | Match |
| T23 | T22 | T22 | Match |
| T24 | T23 | T23 | Match |

## Test Co-location Validation

| Task | Code Layer | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Documentation | Documentation checks | Documentation checks | Co-located in task |
| T2 | Domain | Gherkin/pytest-bdd unit | Gherkin/pytest-bdd unit | Co-located in task |
| T3 | Domain | Gherkin/pytest-bdd unit | Gherkin/pytest-bdd unit | Co-located in task |
| T4 | Domain | Gherkin/pytest-bdd unit | Gherkin/pytest-bdd unit | Co-located in task |
| T5 | Domain | Gherkin/pytest-bdd unit | Gherkin/pytest-bdd unit | Co-located in task |
| T6 | Domain | Gherkin/pytest-bdd unit | Gherkin/pytest-bdd unit | Co-located in task |
| T7 | Native | Gherkin/pytest-bdd integration | Gherkin/pytest-bdd integration | Co-located in task |
| T8 | Domain | Gherkin/pytest-bdd unit | Gherkin/pytest-bdd unit | Co-located in task |
| T9 | Domain | Gherkin/pytest-bdd unit | Gherkin/pytest-bdd unit | Co-located in task |
| T10 | Native | Gherkin/pytest-bdd integration | Gherkin/pytest-bdd integration | Co-located in task |
| T11 | Artifacts | Gherkin/pytest-bdd integration | Gherkin/pytest-bdd integration | Co-located in task |
| T12 | Artifacts | Gherkin/pytest-bdd integration | Gherkin/pytest-bdd integration | Co-located in task |
| T13 | Viewer | Cucumber acceptance | Cucumber acceptance | Co-located in task |
| T14 | Viewer | Cucumber acceptance | Cucumber acceptance | Co-located in task |
| T15 | Domain | Gherkin/pytest-bdd unit | Gherkin/pytest-bdd unit | Co-located in task |
| T16 | Documentation | Documentation checks | Documentation checks | Co-located in task |
| T22 | Artifacts | Gherkin/pytest-bdd integration | Gherkin/pytest-bdd integration | Co-located in task |
| T23 | Documentation | Documentation checks | Documentation checks | Co-located in task |
| T24 | Documentation | Documentation checks | Documentation checks | Co-located in task |
