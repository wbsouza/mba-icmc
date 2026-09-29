# Story 21 planning companion

Status: draft for review, 2026-09-28. Planning baseline: `main` at `35a0dc9`,
merged PR #87. No implementation, model fitting or experiment has run for this plan.

The user-supervised Claude [story spec](spec.md), [progress](progress.md) and
[signal-horizon evidence](evidence/signal-horizon-check.md) are the primary source
documents. This companion does not supersede, restore or edit them. The checked
outlier-analysis item and PR #87's added monthly table remain intact.

## Planning documents

| Document | Purpose |
| --- | --- |
| [EARS specification](../../../../../.specs/features/confluence-chain/spec.md) | 32 requirements, traceability and 11 draft decisions |
| [Context](../../../../../.specs/features/confluence-chain/context.md) | User constraints, merged-source provenance and unresolved availability |
| [Design](../../../../../.specs/features/confluence-chain/design.md) | Current terminal/F1/F4/F6 reuse and exact integration handoffs |
| [Tasks](../../../../../.specs/features/confluence-chain/tasks.md) | 22 actual task bodies with co-located tests, owners, dependencies and gates |
| [Parallel coordinator](../../parallel-19-21-22.md) | Main-agent ownership, parallel lanes, shared-file leases and publication |

## Source and proposal disposition

The source contract remains primary. The following companion qualifications and
proposed alternatives must be reviewed before dependent implementation. A draft
EARS criterion is a testable proposal, not permission to change Claude's contract.

| Topic | Preserved source context | Companion disposition |
| --- | --- | --- |
| Calibration outlier | PR #87 records January's unusual intensity distribution and coverage check | Consume that finding; do not redo the completed analysis or uncheck its progress item |
| Population | Monthly table labels counts as H1 decision bars; January has 744 | T9 reconciles calendar-expanded hours with actual complete tradable bars, closures, warmup and missing days; do not assume 744 valid trading decisions |
| Coverage and availability | Report cites partition sizes and `.done` markers and names geopolitical events | These alone do not establish row completeness, point-in-time availability or causal event attribution; T9 requires separate provenance |
| Return units | Archived normalized return divided by 1e-4 is described as pips | This companion calls it normalized-return units; T8 later derives true EUR/USD price pips from matched closes into a new artifact, leaving the archive unchanged |
| Evaluation window | Source retains earlier validation-window wording | All 14 proposed cells and Nov–Feb remain exploratory because the year was inspected; later registration cannot undo that inspection |
| Momentum and horizon | Source names 480 H1 / 120 H4 and four-bar exits | Use explicit completed-bar units; four H1 bars span four scheduled hours, four H4 bars sixteen, with gaps extending elapsed time; H4 extrapolation is secondary |
| Exit timing | Source specifies the open of t+N | D5 proposes N fully held completed bars after actual entry fill, then next real event submission; this changes semantics and requires approval, with no synthetic open fill |
| Voting and intensity | Source specifies agreement and relative quantiles | D1–D4 propose exact availability cutoffs, high→SELL/low→BUY sign, equal-cutoff HOLD and named required votes; F5/F6 keep veto priority |
| Other implementation choices | Source does not settle every reversal/audit detail | D6–D11 record pending precedence, re-entry, analysis, warmup, controls and audit decisions; no silent defaults |

If a proposal is rejected, reconcile its requirements, task acceptance criteria
and tests before implementation. None of these decision gaps blocks writing this
plan. Actual unavailable or malformed history blocks future affected runs; valid
initial warmup is a separate state.

## Bounded task order

| Phase | Order | Count |
| --- | --- | ---: |
| 1: Chain contracts | T1, T2, T3, T4, T5 | 5 |
| 2: Helpers and study inputs | T6, T7, T8, T9, T10 | 5 |
| 3: Shared integration | T11, T12, T13, T15, T14 | 5 |
| 4: Registration and evidence | T16, T17, T18, T20, T19, T21, T22 | 7 |

Total: **22 tasks**, IDs T1–T22, four phases. T15 defines serialization before
T14 records it. T20 places the Chapter 4 registration before T19 can run the
study. T17 builds the harness with fixture-based tests; only separately authorized
T19 executes research cells. Numeric IDs remain stable despite these two ordering
exceptions. The plan has no dependency on a later phase.

Main owns integration of `strategies.py`, `chain/wiring.py`,
`engine/chain_algorithm.py`, recorder/schema changes and manuscript edits.
Concurrent Story 21 workers receive only exclusive component/test leases.
Stories 19/22 do not add adaptive-model, candlestick or support/resistance inputs
to these fourteen cells. The coordinator owns combined compatibility fixtures,
global resource limits and shared publication.

## Preservation and authorization

The current evidence preservation hash is
`6c6544a7426b530ef1c0d682f37397fbcb3ba7d82efa4f3c184855fc5ff7f8f6`.
The earlier `6568120` hash is historical provenance in context.md, not a restore
target. The three primary files must remain byte-identical to `35a0dc9`.

The user authorized committing/pushing/opening a PR for planning docs. Main owns
publication; this worker does not publish. The reported planning-publication
attempt was blocked by read-only `.git` and denied Forgejo branch approval;
this worker claims no publication. That historical blocker does not deny the
already-merged user-supervised PR #87. Peirce/Erdos are planning helpers; no
implementation worktrees or additional helper agents are created by this plan.

Strict spec/tasks validation, link/trace checks and source-preservation checks
are documentation gates only. No task is marked implemented, no runtime gate
is claimed passed, and all new implementation choices remain drafts.
