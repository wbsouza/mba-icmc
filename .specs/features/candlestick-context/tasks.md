# Candlestick context implementation plan

**Status**: Draft for review. Planning only, explicitly confirmed by the user.
All 24 tasks are pending. No engine changes, dependency installation, model
training, experiments or agents are authorized by this document.

**Design**: [design.md](design.md). **Requirements**: [spec.md](spec.md).
This is the canonical task checklist for the Story 13 extension.

## Execution Protocol

For future implementation, activate **tlc-spec-driven** by name and follow its
Execute flow and Critical Rules. If unavailable, STOP and tell the user.
Read its implementation reference and revalidate this plan before starting.
The current user request stops at planning; do not enter Execute now.

Before any future execution, obtain scope/design approval and confirm tool and
skill preferences. Proposed tools for every task: CodeGraph for code discovery,
shell for checks, apply_patch for edits; skill tlc-spec-driven, plus docs-writer
for documentation tasks. Check installed capabilities rather than invent APIs.
Offer sequential batch workers before dispatch; no worker is launched now.

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

## Test Coverage Matrix

Generated from algo-suite/CLAUDE.md, Makefile, pyproject.toml and viewer package
scripts; confirm before Execute. Samples: candlestick_detector, f3_pattern,
closed_signal_parity, training_family_contract, signal_configuration and viewer
patterns features and their step implementations. Existing tests are a floor.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Domain | Gherkin/pytest-bdd unit | All branches and applicable AC/edge cases; core 100% line coverage, CRAP <=8 | algo-backtest/tests/features + tests/steps | Quick; Pure for new perception modules |
| Native | Gherkin/pytest-bdd integration | Happy/error/boundary cases, closed-bar parity and protection regression | algo-backtest/tests/steps | Full |
| Artifacts | Gherkin/pytest-bdd integration | Round-trip, old/new schema, corrupt/partial/colliding records | owning package tests/features + tests/steps | Artifacts |
| Viewer | Cucumber acceptance | Old/new rendering, every new state, semantic distinction and malformed data | algo-viewer/tests | Viewer |
| Model | Gherkin/pytest-bdd + real local smoke | Contract failures plus pinned real-checkpoint evidence; doubles alone insufficient | algo-backtest/tests/features + tests/steps | Model |
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
| Model | Optional local model | Quick plus explicit new model-smoke BDD selection; resolve the optional environment in T17, record the exact command and pinned revision before running |
| Docs | Planning/source/protocol | `git diff --check`; strict skill spec/tasks validators; source/Markdown-link checks |
| Evidence | Experimental report | Docs plus reconciliation with each immutable run manifest and metric artifact |
| Monograph | Chapter update | Evidence plus `make verify` from monografia |
| Build | End of each applicable phase | `make check`; Viewer for UI changes; Pure/Full for numerical/native changes; `make audit` after dependencies change |

Strict planning validators, from repository root:

```sh
python3 /home/wellington/.agents/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/candlestick-context/spec.md --strict
python3 /home/wellington/.agents/skills/tlc-spec-driven/scripts/validate_tasks.py .specs/features/candlestick-context/tasks.md --strict
```

Resolve the installed skill directory anew in another environment. Missing Docker,
weights, data, dependency wheels or network is a recorded blocked gate, not PASS.
Do not install or download anything during this planning turn.

## Execution Plan

Four sequential phases: rules (6 tasks), integration (8), learned context (7),
then experiments/reporting (3). Conservative single-owner ordering avoids
overlapping contract edits; dependencies below include rollout gates as well as
direct code dependencies. Future batches may group consecutive whole phases near
the skill's task budget; confirm delegation before execution, never split a phase
between concurrent workers. No agents or extra worktrees exist for this plan.

```text
T1 -> T2 -> T3 -> T4 -> T5 -> T6
T6 -> T7 -> T8 -> T9 -> T10 -> T11 -> T12 -> T13 -> T14
T14 -> T15 -> T16 -> T17 -> T18 -> T19 -> T20 -> T21
T21 -> T22 -> T23 -> T24
```

Release checkpoint after T14: explicit rules and evidence UI. T15–T21 are optional
learned-context research, contingent on reviewed labels and a feasible protocol.
A negative feasibility result requires an explicit scope amendment; it does not
complete unperformed tasks. T22 may run rules-only after an approved amendment.
No historical backtest result alone permits live deployment.

## Task Breakdown

### Phase 1: Source-backed explicit rules

### T1: Review and freeze the source-rule ledger

**What**: Record book PDF/printed pages, slide numbers and video times, exact geometry/context/confirmation rules, TA-Lib equivalence or differences, and optional EarnForex license/source review. Mark unsupported or ambiguous definitions deferred, including broader chart formations.

**Where**: `algo-suite/docs/stories/planned/22-candlestick-context-extension/candlestick-rule-ledger.md`
**Depends on**: None
**Requirement**: CND-01
**Reuses**: Source brief and timestamped video notes.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Documentation checks. One positive, one negative and one equality-boundary example for every admitted rule; each contextual threshold and Forex gap/calendar adaptation explicit.
**Gate**: Docs (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Docs gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

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

**What**: Canonicalize and verify catalog, timeframe, context, feature order and optional model/calibration identity; retain explicit legacy compatibility only.

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

**What**: Add an ordered expanded feature schema while preserving old signed-polarity encoding for old model families.

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
**Tests**: Gherkin/pytest-bdd integration. At least 6 BDD cases: round-trip, opposing hits, unavailable context, learned provenance, veto and bullish detection with final SELL.
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
**Tests**: Cucumber acceptance. At least 6 Cucumber scenarios: historical omission, multiple/opposing hits, veto, warmup, learned provider and detection-direction/final-action disagreement.
**Gate**: Viewer (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Viewer gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): render separate pattern and decision evidence`

### Phase 3: Optional frozen learned context

### T15: Validate reviewed sequence labels and split boundaries

**What**: Create a dataset validator with reviewed/weak/ambiguous provenance, label adjudication records and chronological input-window/outcome-horizon overlap checks.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/candle_learning/dataset.py`
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

**What**: Register exact splits, costs, seeds, label minimums, calibration metrics, acceptance thresholds, trial budget, inference feasibility and stop criteria before fitting or outcome inspection.

**Where**: `algo-suite/docs/stories/planned/22-candlestick-context-extension/candlestick-method-design.md`
**Depends on**: T15
**Requirement**: CND-19, CND-26
**Reuses**: Existing method-design approach and T15 validated dataset inventory.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Documentation checks. Document checks cover every protocol field, frozen baseline matrix, embargo/purge calculation and no use of speaker performance claims as acceptance evidence.
**Gate**: Docs (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Docs gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `docs(candles): register bounded recognition and trading protocol`

### T17: Implement optional pinned Laya inference adapter

**What**: Verify upstream interface/license, pin revision and optional dependencies, then implement bounded input/output validation outside LEAN. Record environment and model identity.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/candle_learning/laya_adapter.py`
**Depends on**: T16
**Requirement**: CND-20, CND-21
**Reuses**: T2 schema and T16 protocol; primary upstream model documentation must be checked before coding.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 8 BDD contract cases for serialization, token overflow, unknown/extra fields, non-finite scores, label constraints, missing weights and manifest completeness; one real pinned-checkpoint smoke in addition to doubles.
**Gate**: Model (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Model gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): implement optional pinned laya inference adapter`

### T18: Implement frozen specialization pipeline

**What**: Train the optional context classifier using validated splits, train-only preprocessing and a separate calibration partition; publish immutable lineage metadata.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/candle_learning/train.py`
**Depends on**: T17
**Requirement**: CND-19, CND-21
**Reuses**: T15 dataset validator and T17 pinned adapter.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 7 BDD cases: forbidden overlap, test access rejection, seed/config persistence, train-only preprocessing, calibration provenance, failed-fit record and tiny real-training smoke.
**Gate**: Model (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Model gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): implement frozen specialization pipeline`

### T19: Evaluate recognition, calibration and repeatability

**What**: Produce per-label metrics, coverage, calibration and repeatability results versus rules and a registered simpler baseline; apply T16 acceptance without test tuning.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/candle_learning/evaluate.py`
**Depends on**: T18
**Requirement**: CND-21, CND-22, CND-26
**Reuses**: Existing analysis conventions, T16 protocol and T18 frozen artifact.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 8 BDD cases including hand-calculated metrics, no positives, abstention coverage, weak-label separation, manifest lineage, identical labels over 100 repeats and probability tolerance pass/fail boundaries.
**Gate**: Model (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Model gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): evaluate recognition, calibration and repeatability`

### T20: Materialize immutable learned-output cache

**What**: Publish validated per-bar output artifacts with complete identity, atomic publication and no conflicting overwrite; detect duplicate or incomplete rows.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/candle_learning/cache.py`
**Depends on**: T19
**Requirement**: CND-23, CND-24
**Reuses**: Existing source-hash artifact conventions and T19 accepted or explicitly experimental model.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 9 BDD cases: identical reuse, key/content collision, interrupted write, missing row, duplicates, stale window, corrupt bytes, mismatch and successful publication.
**Gate**: Artifacts (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Artifacts gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): materialize immutable learned-output cache`

### T21: Integrate cache-backed optional provider

**What**: Wire the optional provider at the signal boundary with complete preflight validation; replay the same records offline and in LEAN without model downloads. Keep learned mode advisory in this rollout.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/candle_provider.py`
**Depends on**: T20
**Requirement**: CND-10, CND-11, CND-13, CND-14, CND-24
**Reuses**: T7 integration and T20 immutable cache; small wiring changes belong to this component.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 10 native/host BDD scenarios covering parity, absent/corrupt/stale/duplicate data, startup contract mismatch, advisory abstention, no fallback, no replay network and unchanged protection scheduling.
**Gate**: Full (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Full gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): integrate cache-backed optional provider`

### Phase 4: Registered experiments and publication

### T22: Record complete experiment attempts and parameters

**What**: Create a bounded runner for the registered matrix that records every attempt, resolved settings for every enabled/disabled filter, costs and code/data/model/protocol hashes before execution.

**Where**: `algo-suite/tools/candlestick_experiments.py`
**Depends on**: T21
**Requirement**: CND-25
**Reuses**: Existing experiment scripts and run manifests; production backtests occur only after separate execution authorization.
**Tools**: Common Execution Protocol tools; no delegated execution yet.
**Tests**: Gherkin/pytest-bdd integration. At least 8 BDD scenarios: full manifest, disabled filters, failed run, interrupted run, existing run collision, bounded trial count, dry-run command generation and config/result identity.
**Gate**: Artifacts (commands above); record baseline and final collected/passed counts.
**Done when**:

- [ ] The component meets the cited ACs and all listed cases pass its Artifacts gate; no existing scenarios are removed or silently skipped.
- [ ] Evidence and requirement/task status are included in one atomic commit.

**Commit**: `feat(candles): record complete experiment attempts and parameters`

### T23: Publish comparison evidence with parameters beside results

**What**: Publish the registered comparisons and recognition results with complete per-filter parameter tables, costs, sample sizes, uncertainty, exclusions and artifact links; report negative/inconclusive outcomes.

**Where**: `algo-suite/docs/stories/planned/22-candlestick-context-extension/candlestick-results.md`
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

**What**: Add an evidence-backed extension section separating recognition and trading results, retrospective-model limitations and remaining live-readiness prerequisites.

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
| T17 | One implement optional pinned laya inference adapter component | Atomic outcome defined |
| T18 | One implement frozen specialization pipeline component | Atomic outcome defined |
| T19 | One evaluate recognition, calibration and repeatability component | Atomic outcome defined |
| T20 | One materialize immutable learned-output cache component | Atomic outcome defined |
| T21 | One integrate cache-backed optional provider component | Atomic outcome defined |
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
| T17 | T16 | T16 | Match |
| T18 | T17 | T17 | Match |
| T19 | T18 | T18 | Match |
| T20 | T19 | T19 | Match |
| T21 | T20 | T20 | Match |
| T22 | T21 | T21 | Match |
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
| T17 | Model | Gherkin/pytest-bdd integration + real smoke | Gherkin/pytest-bdd integration + real smoke | Co-located in task |
| T18 | Model | Gherkin/pytest-bdd integration + real smoke | Gherkin/pytest-bdd integration + real smoke | Co-located in task |
| T19 | Model | Gherkin/pytest-bdd integration + real smoke | Gherkin/pytest-bdd integration + real smoke | Co-located in task |
| T20 | Artifacts | Gherkin/pytest-bdd integration | Gherkin/pytest-bdd integration | Co-located in task |
| T21 | Native | Gherkin/pytest-bdd integration | Gherkin/pytest-bdd integration | Co-located in task |
| T22 | Artifacts | Gherkin/pytest-bdd integration | Gherkin/pytest-bdd integration | Co-located in task |
| T23 | Documentation | Documentation checks | Documentation checks | Co-located in task |
| T24 | Documentation | Documentation checks | Documentation checks | Co-located in task |

