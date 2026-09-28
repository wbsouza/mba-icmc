# Candlestick context decisions

Gathered: September 28, 2026. Status: draft for review.

## Feature Boundary

Consolidate the Story 13 candlestick expansion into testable engine tasks. User
requested Bigalow book/presentation/video, an optional EarnForex port, and Laya
as an open-weight bounded-decision complement to TA-Lib. No implementation or
new experiment was requested in this planning turn.
The user subsequently confirmed explicitly: planning only, no implementation yet.

## Implementation Decisions

- Preserve the existing filter-combination approach; no single book is assumed
  to supply a complete successful strategy.
- Record full per-filter parameters beside every run's result.
- Freeze model behavior per experiment; allow versioned retraining afterward.
- Keep book and presentation sources read-only; source typos matter only when
  they alter a rule, threshold, or timing relationship.
- Keep one canonical requirement/task plan linked from Story 13. Registered
  worktrees were searched; no second Bigalow/Laya story was found. An unseen
  draft cannot be claimed merged; obtain its path before reconciling it.

## Declined / Undiscussed Gray Areas → Assumptions

The spec records proposed defaults for rollout, advisory behavior, bounded
catalog/sequence scope, inference cache, and input bounds. They are not user
approvals. An asynchronous rollout question was offered during planning.
Research thresholds and ambiguous source rules are explicit prerequisite tasks.

## Architecture options for approval

Recommended: one shared explicit-rule feature producer plus a local Laya cache
adapter. It supports both backtest and offline training without embedding Torch
inside LEAN. Cost: materialization and strict cache identity must be maintained.

Alternative: embed Laya directly in both runtimes using the same provider
interface. It removes the cache but increases container, dependency, memory,
and reproducibility obligations. Both options deliver the same scoped evidence;
the current design/tasks draft uses the cache option pending approval.

## Deferred Ideas

Visual YOLO training, live services, online adaptation, and new exit-order
policies remain outside this slice. Broader Bigalow formations remain in the
source ledger until their causal definitions and label quality are established.
