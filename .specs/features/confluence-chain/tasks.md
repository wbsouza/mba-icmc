# Confluence Chain Tasks

Status: approved for implementation 2026-09-28 (D1–D11 resolved; D5 = source bar-open timing). Baseline: main `35a0dc9`, PR #87.
Design: [design.md](design.md). Requirements: [spec.md](spec.md).
Coordinator: [parallel delivery plan](../../../algo-suite/docs/stories/parallel-19-21-22.md).

## Execution Protocol

Use `tlc-spec-driven` for future execution, with its per-task evidence and
independent verification flow. Its planning references have been read for this
plan. User scope takes precedence: this turn writes planning docs only and runs
documentation validators. No runtime tests, models, market replay, experiments,
commits, pushes or additional helper dispatch by this worker.

The user-supervised Claude Story 21 spec/progress/evidence are primary and must
remain byte-identical to `35a0dc9` during this planning work. These tasks do not
silently supersede that contract. Resolve D1–D11, especially bar-open versus
completed-bar/next-event timing, before dependent implementation. The user has
authorized publication of planning docs; main owns it and reports the existing
read-only Git/Forgejo approval block. Planning helpers already exist; no
implementation worktrees have been created by this lane.

Task IDs T1–T22 are stable. T15 executes before T14 because the recorder needs
the schema; T20 executes before T19 because the source requires a Chapter 4
registration paragraph before runs. Every task has one production component or
document as its primary deliverable, with its required tests in the same task.
Future generated configs, job artifacts and the result fragment are outputs of
those components, not additional concurrent source-file ownership.

Before future execution, main approves contracts, tools and path leases, and
records actual regression counts. Existing source/test/fixture ownership remains
with its assigned lane. Shared paths are never edited by a concurrent Story 21
worker. CodeGraph precedes code navigation. Use Gherkin first, then steps and
implementation; no plain pytest test functions. After each code task, complete
the applicable gate, `make check`, `make audit` and debt review; record a blocked
gate as blocked. Atomic commits and progress updates belong to the future
authorized execution workflow, not this planning worker. A fresh independent
Verifier and isolated discrimination sensor close future implementation; no
implementation `validation.md` is created now.

## Test Coverage Matrix

Generated from `algo-suite/CLAUDE.md`, workspace `Makefile`, `mk/tool.mk`,
`pyproject.toml`, and sampled Gherkin/steps: filter_chain_mechanics, f1_trend,
f4_news_context, f6_capital_mgmt, chain_wiring, strategy_explain, bar_clock and
portfolio_inference. Commands below run from `algo-suite/` unless stated.
New `confluence_*.feature` and step paths are proposed artifacts, not existing
tests or claims of completed checks.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Pure terminal/history/filter/lifecycle | Gherkin unit | Every mapped AC and listed failure/boundary; independent expected outputs | `algo-backtest/tests/features/confluence_*.feature` and `tests/steps/test_confluence_*.py` | Quick, explicit task selection |
| Config/factories/serialization | Gherkin component | Happy, invalid, omitted-option compatibility and round-trip paths | Same pair layout; existing regression features retained | Quick plus existing selected regressions |
| Native engine lifecycle | Gherkin integration | Actual timestamp/order/stop behavior, complete bars and legacy mode | `confluence_engine.feature`, integration-tagged steps | Native |
| Experiment/data/report scripts | Gherkin component | Input population, causal boundaries, output counts, unavailable paths; fake runner for harness | Same pair layout under algo-backtest tests; analyzer regressions reused | Quick; explicit script mypy check at Build |
| Protocol and public docs | Document contract review | All linked IDs, parameters, paths and provenance agree with accepted artifacts | Task document and cross-reference review | Docs |
| Manuscript | Document build/review | English prose, cited protocol/results and no unsupported claims | Existing chapter and generated result inclusion | Thesis |
| Study evidence | Artifact acceptance | Exactly 14 accounted outcomes; valid inputs, immutable source and audit links | New job/report outputs | Evidence |

Small deterministic examples in Gherkin are test fixtures, not fabricated market
evidence. Production re-derivation and study reports require actual source data.
Existing tests are not deleted, weakened or marked skipped to meet a count.

## Gate Check Commands

These are future commands inferred from current manifests; only Docs validators
run in this planning turn. A missing runtime/data/dependency is a blocked gate,
not permission to claim pass. New selections must collect a nonzero count.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick | Pure/component task | `uv run pytest algo-backtest/tests/steps/test_confluence_NAME.py`, with NAME specified per task |
| Native | T13 | `uv run pytest algo-backtest/tests/steps/test_confluence_engine.py -m integration`; also `uv run pytest algo-backtest/tests/steps/test_closed_signal_parity.py -m integration` |
| Regression | Integration compatibility | `uv run pytest algo-backtest/tests/steps/test_filter_chain_mechanics.py algo-backtest/tests/steps/test_f1_trend.py algo-backtest/tests/steps/test_f4_news_context.py algo-backtest/tests/steps/test_f6_capital_mgmt.py algo-backtest/tests/steps/test_chain_wiring.py algo-backtest/tests/steps/test_strategy_explain.py algo-backtest/tests/steps/test_decision_recorder.py algo-backtest/tests/steps/test_audit.py algo-backtest/tests/steps/test_bar_clock.py algo-backtest/tests/steps/test_order_executor.py algo-backtest/tests/steps/test_trade_plan.py algo-analyze/tests/steps/test_portfolio_inference.py` |
| Build | Every code phase and task handoff | `make check`; `uv run ruff format --check .`; `make audit`; for each new experiment script also `uv run mypy --strict <exact script path from task>` |
| Docs | Planning closure, later document tasks | From repo root: `python3 /home/wellington/.agents/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/confluence-chain/spec.md --strict` and `python3 /home/wellington/.agents/skills/tlc-spec-driven/scripts/validate_tasks.py .specs/features/confluence-chain/tasks.md --strict`; review links/trace map and source preservation |
| Thesis | T20/T21 and installed result fragment | From repo root: `make -C monografia`, `make -C monografia verify`, `make -C monografia pt-scan`; review surfaced language findings |
| Evidence | T19, later separately authorized study | All prior gates pass; run T17's frozen registered command recorded by T16, then T18 reporter; reconcile exactly 14 manifest statuses and hash-preserved source; execute no guessed current CLI |

The existing Makefile may tolerate pytest exit 5; this plan does not. Record
collected/pass/fail counts from explicit selections. Scenario counts below are
minimum planned new examples, not invented baseline counts. Capture baseline
counts at execution start and require baseline plus the task's new examples.
`make check` excludes native/network tests, so it cannot replace Native.

## Execution Plan

Four sequential Story 21 phases: **5 + 5 + 5 + 7 = 22 tasks**. Independent Stories
19/22 can advance alongside phases 1–2 under main's leases. Phase 3 is serialized
integration. Phase 4 contains preparation before any separately authorized study.
Within-lane arrows are completion gates; not every ordering is a code dependency.

```text
T1 -> T2 -> T3 -> T4 -> T5
T5 -> T6 -> T7 -> T8 -> T9 -> T10
T10 -> T11 -> T12 -> T13 -> T15 -> T14
T14 -> T16 -> T17 -> T18 -> T20 -> T19 -> T21 -> T22
```

## Task Breakdown

### Phase 1: Chain contracts (5 tasks)

#### T1: Add the named agreement terminal

**What**: One terminal collaborator implementing the approved named-vote contract beside the existing terminals.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/terminal.py`
**Owner**: Story 21 private lease.
**Depends on**: None.
**Reuses**: TerminalDecision, FilterResult and FilterChain.run.
**Requirement**: CC-01, CC-02, CC-03, CC-04, CC-05, CC-20.
**Decision gate**: D4.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [x] BUY/SELL unanimity, required abstention, all-abstain, conflict, explicit HOLD, invalid names, absent/duplicate results and F5/F6 short-circuit match spec outcomes; legacy terminals retain their behavior.
- [x] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_agreement.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_agreement.py` in this task; at least 12 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_agreement.py`; Build and applicable Regression before handoff.

#### T2: Add F1 momentum context

**What**: One selectable momentum component with a bounded L+1 completed-close history.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/filters/f1_trend.py`
**Owner**: Story 21 private lease.
**Depends on**: T1.
**Reuses**: F1TrendFilter, ExecutionState and the existing F1 scenario style.
**Requirement**: CC-06, CC-07, CC-08, CC-20, CC-28.
**Decision gate**: D8.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [x] Positive/negative/zero return votes match independent prices at L=480 and L=120; warmup is distinct from missing/malformed data; duplicates, nonfinite/nonpositive closes and bad ordering fail; original F1 still vetoes its original conflict cases.
- [x] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_momentum.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_momentum.py` in this task; at least 10 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_momentum.py`; Build and applicable Regression before handoff.

#### T3: Calculate immutable monthly intensity snapshots

**What**: One pure history-snapshot component implementing the approved sampling and availability contract.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/intensity_history.py`
**Owner**: Story 21 private lease; new module.
**Depends on**: T2.
**Reuses**: NewsContextIndex boundary and ClosedBarClock timestamps without changing their shared contracts.
**Requirement**: CC-09, CC-10, CC-13, CC-14, CC-31.
**Decision gate**: D1, D2, D8.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [x] Linear q10/q90 match independent examples; exact month boundary, mid-month start, late arrivals, revised suffix and repeated lookup preserve prior snapshots; missing/invalid rows fail; valid initial collection reports WARMUP; provenance fields round-trip through plain values.
- [x] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_history.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_history.py` in this task; at least 12 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_history.py`; Build and applicable Regression before handoff.

#### T4: Add F4 relative intensity mode

**What**: One optional direction mode consuming T3 snapshots through explicit injection.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/filters/f4_news_context.py`
**Owner**: Story 21 private lease.
**Depends on**: T3.
**Reuses**: NewsContextConfig, F4NewsContextFilter and existing intensity_sign behavior.
**Requirement**: CC-09, CC-10, CC-11, CC-12, CC-14, CC-20, CC-31.
**Decision gate**: D1, D2, D3.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [x] Approved sign maps high to SELL and low to BUY, including equality boundaries; interior is NEUTRAL; equal quantiles always HOLD; warmup does not fall back to static cuts; late current input fails; legacy static and sentiment modes remain unchanged.
- [x] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_relative_intensity.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_relative_intensity.py` in this task; at least 10 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_relative_intensity.py`; Build and applicable Regression before handoff.

#### T5: Define the optional F6 bar-count plan

**What**: One optional exit_after_bars configuration extension to the existing F6 plan.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/filters/f6_capital_mgmt.py`
**Owner**: Story 21 private lease.
**Depends on**: T4.
**Reuses**: CapitalMgmtConfig, parse_capital_mgmt_config and capital_mgmt_mapping.
**Requirement**: CC-20, CC-21, CC-22.
**Decision gate**: D5, D6, D11.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [x] Omitted option round-trips legacy defaults; bool/fraction/zero/negative N fail; explicit time plan has no targets/trail or target-based reward-risk veto; existing ATR, stop floors, spread and sizing remain in effect. Record the accepted timing contract before adding this field.
- [x] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_capital_plan.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_capital_plan.py` in this task; at least 8 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_capital_plan.py`; Build and applicable Regression before handoff.

### Phase 2: Independent helpers and study inputs (5 tasks)

#### T6: Model causal expiry as a pure lifecycle

**What**: One event-driven lifecycle that returns expiry intents without inventing fills.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/time_exit.py`
**Owner**: Story 21 private lease; new module.
**Depends on**: T5.
**Reuses**: Existing trade identity and completed-bar conventions; no LEAN imports.
**Requirement**: CC-15, CC-16, CC-17, CC-18, CC-19, CC-28, CC-31.
**Decision gate**: D5, D6, D11.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [x] Accepted bar-open timing (D5: exit at the open of bar t+N, t = the bar during which the entry filled, due at the close of t+N-1, submit at the first event at or after that open) handles exact and mid-bar fills, H1/H4, gaps, partial bars, repeated events, same-side votes, reversal, full/partial stop fills, rejection/retry and end-of-stream pending state; never requests a second live close; no same-event re-entry.
- [x] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_time_exit.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_time_exit.py` in this task; at least 14 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_time_exit.py`; Build and applicable Regression before handoff.

#### T7: Provide explicit drift-control votes

**What**: One constant-direction filter for the two already-scoped drift-control arms.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/filters/constant_direction.py`
**Owner**: Story 21 private lease; new module.
**Depends on**: T6.
**Reuses**: Filter protocol and Recommendation.
**Requirement**: CC-23.
**Decision gate**: D9.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] BUY and SELL configurations emit only their named vote; invalid direction fails; both remain subject to real F5/F6 vetoes; neither reads news or an F7 model.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_controls.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_controls.py` in this task; at least 4 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_controls.py`; Build and applicable Regression before handoff.

#### T8: Build a separate evidence-unit re-derivation tool

**What**: One report tool that calculates normalized returns and price pips from timestamp-matched sources without modifying them.
**Where**: `algo-suite/experiments/confluence-chain/rederive_horizon.py`
**Owner**: Story 21 private lease; new script.
**Depends on**: T7.
**Reuses**: Archived decision-log join keys and current instrument pip convention.
**Requirement**: CC-25, CC-26.
**Decision gate**: No new numeric result until source-backed execution is separately authorized.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] An independent example distinguishes a 1e-4 return from a 0.0001 price change; bad joins, missing future horizon and missing prices are explicit; original archive hash is checked before/after; outputs use a new caller-specified path. Do not rerun the PR #87 outlier analysis.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_horizon_units.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_horizon_units.py` in this task; at least 5 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_horizon_units.py`; Build and applicable Regression before handoff.

#### T9: Gate data population and point-in-time availability

**What**: One preflight report binding actual input coverage, population counts and availability to each arm.
**Where**: `algo-suite/experiments/confluence-chain/preflight.py`
**Owner**: Story 21 private lease; new script.
**Depends on**: T8.
**Reuses**: news_coverage_problems, ClosedBarClock and recorded PR #87 outlier findings.
**Requirement**: CC-08, CC-09, CC-13, CC-24, CC-32.
**Decision gate**: D2, D8; availability source/approved conservative lag must be resolved before runs.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Ledger separates calendar-expanded rows (January 744 is not assumed tradable), expected valid closed bars, closures, warmup and missing days/minutes; reconciles H1/H4 and monthly cutoffs; file sizes/.done alone cannot pass completeness or availability; absent sources fail with remediation; M-only and drift controls do not demand news.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_preflight.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_preflight.py` in this task; at least 10 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_preflight.py`; Build and applicable Regression before handoff.

#### T10: Generate the fixed fourteen-cell manifest

**What**: One deterministic generator of the seven arms times two clocks and their effective configuration manifest.
**Where**: `algo-suite/experiments/confluence-chain/make_cells.py`
**Owner**: Story 21 private lease; new generator.
**Depends on**: T9.
**Reuses**: Existing experiments/heikin-ashi-signals strategy layout and pinned template resolution.
**Requirement**: CC-21, CC-23, CC-28.
**Decision gate**: D3, D7, D9, D11.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Exactly 14 unique IDs; A/B/T-only/M-only named-voter lists are correct; controls need no news; time plans explicitly disable targets/trail; A-plan pins every inherited exit setting; costs, caps and clocks are invariant; F3/F7/adaptive/candlestick/SR arms cannot enter the manifest.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_cells.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_cells.py` in this task; at least 8 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_cells.py`; Build and applicable Regression before handoff.

### Phase 3: Serialized shared integration (5 tasks)

#### T11: Register configuration and provenance contracts

**What**: One strategy-loader extension registering approved new options and the control filter.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/strategies.py`
**Owner**: Integration lane only.
**Depends on**: T10.
**Reuses**: StrategyChainConfig, loader validation, inheritance and provenance mapping.
**Requirement**: CC-01, CC-04, CC-20, CC-21.
**Decision gate**: D1–D11 accepted for affected keys.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Reject contradictory terminal/F7 combinations, unknown or duplicate required voters and gates named as voters; reject bad new values before IO; explain-strategy exposes source/default provenance; legacy configs resolve identically.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_strategy_contract.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_strategy_contract.py` in this task; at least 9 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_strategy_contract.py`; Build and applicable Regression before handoff.

#### T12: Wire approved collaborators and runtime voter names

**What**: One factory integration for the new terminal, F1/F4/F6 options and explicit controls.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/wiring.py`
**Owner**: Integration lane only.
**Depends on**: T11.
**Reuses**: build_filters, terminal_decision and existing filter factories.
**Requirement**: CC-01, CC-04, CC-05, CC-06, CC-20.
**Decision gate**: D4 plus approved configuration schema.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Canonical YAML names map explicitly to runtime F1_trend/F2_indicator identities; snapshots are injected; A/B/ablations build without F7; F5/F6 remain gates; absent required collaborators fail; legacy factory output remains compatible.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_wiring.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_wiring.py` in this task; at least 7 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_wiring.py`; Build and applicable Regression before handoff.

#### T13: Integrate closed history and actual-event expiry

**What**: One engine lifecycle integration connecting the tested helpers to delivered quotes and actual fills.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/engine/chain_algorithm.py`
**Owner**: Integration lane only.
**Depends on**: T12.
**Reuses**: ClosedBarClock, _closed_signal_bar, on_data, on_order_event, _close_open and the existing executor.
**Requirement**: CC-05, CC-15, CC-16, CC-17, CC-18, CC-19, CC-20.
**Decision gate**: D5, D6, D11 explicitly resolved; main's shared-engine lease.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Native scenarios prove the approved event order, stop priority, residual quantity, no synthetic open fills, no duplicate closure/re-entry and unchanged close_on_veto when options are absent. Count completed bars independently of indicator-ready decision indices; exercise a month rollover with an open position. No shared model activation code is added by this task.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin integration; write `algo-suite/algo-backtest/tests/features/confluence_engine.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_engine.py` in this task; at least 10 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Native + Regression + Build; native selection must collect at least 10 new cases.

#### T15: Define the additive exit-audit schema

**What**: One versioned exit-sidecar schema/serializer preserving the current decision-row schema.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/audit.py`
**Owner**: Integration lane only.
**Depends on**: T13.
**Reuses**: DecisionRow, FilterResultRow and current serialization conventions.
**Requirement**: CC-20, CC-31.
**Decision gate**: D10; coordinate field names with Stories 19/22.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Version 1 serializes trade identity, due/submission/fill times, count, reason and order state; unknown future fields/version policy is explicit; malformed timestamps or missing observed fields fail; pending values remain null with status; old decisions still read unchanged.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_exit_schema.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_exit_schema.py` in this task; at least 6 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_exit_schema.py`; Build and applicable Regression before handoff.

#### T14: Record expiry evidence against the closing trade

**What**: One recorder extension retaining closing identity and idempotent lifecycle evidence.
**Where**: `algo-suite/algo-backtest/src/algo_backtest/chain/decision_recorder.py`
**Owner**: Integration lane only.
**Depends on**: T15.
**Reuses**: DecisionRecorder.on_fill, record and current_trade_id plus T15 serializer.
**Requirement**: CC-18, CC-31.
**Decision gate**: D10; recorder shared-file lease.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Capture the actual closing trade ID before flat clears it; round-trip entries, pending/rejected expiry, partial/full stops and reversal; duplicate event callbacks do not duplicate records; existing decision Parquet and trade-plan consumers still work.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_exit_recorder.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_exit_recorder.py` in this task; at least 7 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_exit_recorder.py`; Build and applicable Regression before handoff.

### Phase 4: Registration, bounded evidence and manuscript (7 tasks)

#### T16: Freeze the review-approved registration README

**What**: One registration document copied byte-for-byte into each new job before execution.
**Where**: `algo-suite/experiments/confluence-chain/README.md`
**Owner**: Story 21 protocol owner; new document.
**Depends on**: T14.
**Reuses**: T10 manifest and current producer-bound inference conventions.
**Requirement**: CC-23, CC-27, CC-28, CC-29.
**Decision gate**: User review resolves all protocol defaults before runtime.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Record accepted D1–D11, exact 14 IDs/config hashes, exploratory labels for every cell/window, H1/H4 horizons, main and secondary contrasts, bootstrap settings, population source, costs, no model dependency, one initial attempt per cell and no automatic outcome-based retry. Record main's global resource cap/timeout and source revision; no invented approval or resource values.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Document contract review; one recorded checklist covering each mapped requirement, referenced parameter/path and unsupported-claim check; not runtime-test deferral.
**Gate**: Docs as defined above; record actual outcomes before task completion.

#### T17: Build a bounded fourteen-cell launch harness

**What**: One explicit-run-ID harness that enforces registration, data and integration gates before launching registered cells.
**Where**: `algo-suite/experiments/confluence-chain/run_cells.py`
**Owner**: Story 21 private lease; new script; shared CLI changes go to main.
**Depends on**: T16.
**Reuses**: Current backtest invocation contract and T9/T10 artifacts, not old latest-directory globs.
**Requirement**: CC-23, CC-24, CC-32.
**Decision gate**: Main coordinator provides global slot cap and experiment authorization.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Gherkin fake-runner fixtures prove exactly 14 allowed IDs, distinct output roots, bounded attempts, no model fitting, preflight failure launches zero cells, nonzero child exits persist failure and resume never overwrites an existing attempt. Record per-cell statuses and actual code/config/source hashes. Harness development launches no research cells.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_run_contract.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_run_contract.py` in this task; at least 7 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_run_contract.py`; Build and applicable Regression before handoff.

#### T18: Implement the registered comparison report

**What**: One report component emitting paired equity, prediction endpoints and a manuscript result fragment from explicit run IDs.
**Where**: `algo-suite/experiments/confluence-chain/compare.py`
**Owner**: Story 21 private lease; new reporter.
**Depends on**: T17.
**Reuses**: algo_analyze.portfolio.load_portfolio_returns and significance.paired_block_test.
**Requirement**: CC-27, CC-29, CC-30, CC-32.
**Decision gate**: D7 and frozen registration.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Check independent sign/paired-grid examples, 999 resamples/seed 42/block 4 and sensitivity 2; use strict producer contracts; zero returns are misses and incomplete four-bar horizons are counted exclusions; overlapping horizons are not treated as independent; missing/failed/zero-trade cells remain visible; all 14 cells remain exploratory.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Gherkin unit/component; write `algo-suite/algo-backtest/tests/features/confluence_comparison.feature` first and `algo-suite/algo-backtest/tests/steps/test_confluence_comparison.py` in this task; at least 9 new scenario/example cases. Retain relevant existing regression cases.
**Gate**: Quick: `uv run pytest algo-backtest/tests/steps/test_confluence_comparison.py`; Build and applicable Regression before handoff.

#### T20: Place the registered Chapter 4 protocol

**What**: One confluence subsection with the pre-run registration paragraph and a declared inclusion location for the later result fragment.
**Where**: `monografia/chapters/04-experimental-evaluation.tex`
**Owner**: Integration manuscript lane only.
**Depends on**: T18.
**Reuses**: Existing chapter structure and T16 registration.
**Requirement**: CC-25, CC-27, CC-28.
**Decision gate**: Approved registration and sole manuscript lease.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Before any T19 run, chapter states source units, inspected Nov–Feb, 480H1/120H4 lookbacks and secondary 16-hour H4 extrapolation; it cites the fixed protocol and names the T19 result artifact without asserting results. The inclusion remains an explicit unavailable placeholder until the integration owner installs the validated generated fragment.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Document contract review; one recorded checklist covering each mapped requirement, referenced parameter/path and unsupported-claim check; not runtime-test deferral.
**Gate**: Thesis as defined above; record actual outcomes before task completion.

#### T19: Produce the fourteen-cell evidence report

**What**: One source-backed evidence report from the registered attempts, with separate generated tables for the existing viewer and Chapter 4.
**Where**: `algo-suite/experiments/confluence-chain/results.md`
**Owner**: Main-controlled experiment/evidence lane; integration owns manuscript fragment installation.
**Depends on**: T20.
**Reuses**: T8/T9/T17/T18 tools and T20 manuscript inclusion contract.
**Requirement**: CC-25, CC-26, CC-27, CC-31, CC-32.
**Decision gate**: Runtime authorization plus data, native, registration and resource gates; not authorized this turn.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Only after separate run authorization, execute the bounded manifest; preserve all 14 outcomes, exact commands/exit counts and actual durations; report control behavior and paired/prediction endpoints or explicit unavailability. Save new re-derived units report, validate trade/exit joins and read current viewer decisions. Verify the preserved story evidence hash. Main installs the validated generated manuscript fragment without rewriting the user-supervised Story 21 source.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Artifact acceptance; 14 manifest outcomes, source-hash assertion, report/audit/viewer joins and manuscript fragment verification against actual artifacts; report unavailable inputs explicitly.
**Gate**: Evidence as defined above; record actual outcomes before task completion.

#### T21: Write the qualified Chapter 5 conclusion

**What**: One evidence-supported confluence conclusion with the horizon lesson qualified by the actual outcome.
**Where**: `monografia/chapters/05-conclusion.tex`
**Owner**: Integration manuscript lane only.
**Depends on**: T19.
**Reuses**: T19 evidence report and current thesis conclusion structure.
**Requirement**: CC-27.
**Decision gate**: Verified T19 evidence and sole manuscript lease.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Positive, null, negative or unavailable findings follow the report; no untouched/confirmatory claim or inferred H4 four-hour effect; no broader candlestick/adaptive-model conclusion is introduced.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Document contract review; one recorded checklist covering each mapped requirement, referenced parameter/path and unsupported-claim check; not runtime-test deferral.
**Gate**: Thesis as defined above; record actual outcomes before task completion.

#### T22: Document the accepted public tool contract

**What**: One public-contract update describing only the approved and implemented options.
**Where**: `algo-suite/algo-backtest/SPEC.md`
**Owner**: Integration lane only.
**Depends on**: T21.
**Reuses**: Existing tool spec configuration and audit sections.
**Requirement**: CC-20, CC-31.
**Decision gate**: Implemented and validated contracts; no draft defaults promoted without review.
**Tools**: CodeGraph first for code lookup; shell and apply_patch; tlc-spec-driven. No additional service dependency.

**Done when**:

- [ ] Match final resolved defaults and explicit expiry/availability semantics; explain legacy compatibility, errors and versioned audit fields; link passing Gherkin evidence and reproduction instructions. Hand any additional shared README/schema/viewer changes to main with exact paths, rather than silently editing them.
- [ ] Same-task verification below passes; record actual commands, counts, exit status and artifact paths. No completion claim while a gate is blocked.

**Tests**: Document contract review; one recorded checklist covering each mapped requirement, referenced parameter/path and unsupported-claim check; not runtime-test deferral.
**Gate**: Docs as defined above; record actual outcomes before task completion.

## Task Granularity Check

| Tasks | Single deliverable | Status |
| --- | --- | --- |
| T1–T7 | One named terminal/filter/history/lifecycle/config component per task | Atomic; tests co-located |
| T8–T10 | One re-derivation, preflight or cell-generator component per task | Atomic; tests co-located |
| T11–T15 | One loader/factory/engine/schema/recorder integration component per task | Integration-owned; tests co-located |
| T16–T18 | One registration document, harness or report component per task | Atomic; fixture runner prevents research during harness tests |
| T19 | One bounded evidence report and its generated presentation outputs | Single registered study; requires separate runtime authorization |
| T20–T22 | One Chapter 4, Chapter 5 or tool-spec document per task | Manuscript/tool-doc owner only |

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | Start | Match |
| T2 | T1 | T1 → T2 | Match |
| T3 | T2 | T2 → T3 | Match |
| T4 | T3 | T3 → T4 | Match |
| T5 | T4 | T4 → T5 | Match |
| T6 | T5 | T5 → T6 | Match |
| T7 | T6 | T6 → T7 | Match |
| T8 | T7 | T7 → T8 | Match |
| T9 | T8 | T8 → T9 | Match |
| T10 | T9 | T9 → T10 | Match |
| T11 | T10 | T10 → T11 | Match |
| T12 | T11 | T11 → T12 | Match |
| T13 | T12 | T12 → T13 | Match |
| T15 | T13 | T13 → T15 | Match |
| T14 | T15 | T15 → T14 | Match |
| T16 | T14 | T14 → T16 | Match |
| T17 | T16 | T16 → T17 | Match |
| T18 | T17 | T17 → T18 | Match |
| T20 | T18 | T18 → T20 | Match |
| T19 | T20 | T20 → T19 | Match |
| T21 | T19 | T19 → T21 | Match |
| T22 | T21 | T21 → T22 | Match |

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T2 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T3 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T4 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T5 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T6 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T7 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T8 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T9 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T10 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T11 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T12 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T13 | Native lifecycle | Gherkin integration | Gherkin integration, in task | Match |
| T15 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T14 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T16 | Document | Document review | Document review, in task | Match |
| T17 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T18 | Pure/component | Gherkin unit/component | Gherkin unit/component, in task | Match |
| T20 | Document | Document review | Document review, in task | Match |
| T19 | Study evidence | Artifact acceptance | Artifact acceptance, in task | Match |
| T21 | Document | Document review | Document review, in task | Match |
| T22 | Document | Document review | Document review, in task | Match |

## Integration Handoff and Approval Gaps

T11–T15 are handed to the main integration owner with exact paths in
[design.md](design.md#exact-integration-handoffs); they are not concurrent worker
edits. Main alone connects shared signal/training contracts, schema migrations,
CLI/packaging, fixtures and viewer ingestion if needed, following the coordinator.
T20/T21 use the sole manuscript owner; T22 uses the shared tool-document owner.
No Story 19 adaptive model or Story 22 candlestick/SR arm enters the 14 cells.
Combined-feature compatibility fixtures do not create an extra research cell.

T15 precedes T14 despite numeric IDs. T20 precedes T19 to honor the primary
story's pre-run Chapter 4 paragraph. T18's generated result fragment is installed
only by integration during T19; it fills T20's declared inclusion point and does
not introduce a second writer to Chapter 4. Shared patches are implemented once,
with their own tests, and synchronized by main after acceptance.

D1–D11 remain draft. The material decision is the source's t+N-open timing versus
D5's N-completed-bars/next-event submission, including entry-age and reversal
policy. Also resolve the sampling population, availability provenance, strict
voter handling, sign, audit sidecar and analysis hierarchy. Quantile corruption
cannot be disguised as warmup. Calendar-expanded counts cannot stand in for
tradable bars. PR #87's outlier finding and checked item are retained; no claim
of causal event attribution is made from file sizes. If source availability
cannot be established, report the affected study unavailable.

Planning completion means strict spec/tasks validators and source-preservation
checks pass; it does not mean any of T1–T22 is implemented or approved.

