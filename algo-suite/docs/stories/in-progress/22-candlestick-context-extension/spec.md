# Story 22 — deterministic candlestick context extension

Status: planning amendment, 2026-09-28; moved to in-progress for coordination.
Drafted inside Story 13 and split into Story 22 when Story 13 closed. Future owner:
lane C, rules/perception/F3. No extension implementation, model or experiment has run.
Laya is explicitly DEFERRED, not optional active work.

## Entry points

- [Deterministic catalog and context brief](candlestick-extension.md): Bigalow book,
  CMT presentation and webinar, plus EarnForex review and an inactive Laya archive.
- [Timestamped webinar notes](bigalow-video-notes.md).
- [Canonical tlc-spec-driven plan](../../../../../.specs/features/candlestick-context/tasks.md):
  19 active tasks (T1–T16, T22–T24), five historical tasks DEFERRED (T17–T21);
  its task outputs (`candlestick-rule-ledger.md`, `candlestick-method-design.md`,
  `candlestick-results.md`) land in this directory.

## Evidence already in hand (from the 2026-09-28 offline checks, exploratory)

On the session-2 H1 decision log the six TA-Lib patterns read as continuation signals lean the wrong
way (bearish engulfing: next bar up 61 % of the time, n = 291); read in context (bullish after a fall,
bullish in an F1 downtrend, bullish near a 60-bar low) the bullish side shows 54–59 % at 4 hours on
small samples; the shooting star works as intended (63 % at 4 h, n = 41). Tables:
[Story 21 signal-horizon check](../21-confluence-chain/evidence/signal-horizon-check.md). This is why the extension's first
deliverable is the context-rule ledger, not more patterns.

## Boundaries

Active scope is deterministic rules, closed-bar context, confirmation and evidence.
Preserve frozen legacy behavior, point-in-time availability, detection/recommendation/
action separation and independent protection during entry vetoes. Retain reviewed
recognition data and leakage-free evaluation (CND-18/19) independently of learned
models. CND-01–19, CND-25/26 are active; CND-20–24 are DEFERRED.

The [parallel coordinator plan](../../parallel-19-21-22.md) owns cross-story gates.
Main owns [Story 19](../19-adaptive-recency-retraining/spec.md); a separate lane
owns [Story 21](../21-confluence-chain/spec.md). Story 19's F7 fitting changes
precede Story 22 T9's encoder integration. Coordinator leases cover training,
signal contracts/production, recording, schema and viewer; the monograph has one
editor. Normal F7 model provenance remains active and is unrelated to Laya.

Phases: T1–T6 (6), T7–T14 (8), T15–T16 plus T22–T24 (5). T22 depends on T16,
never on a deferred task. After T14, shared-plan compatibility/protection acceptance
precedes rules evaluation. Keep each story's study separate; the inspected session-2
period remains exploratory. Main owns link checks and final planning validation.
No implementation worker or worktree is created by this amendment.
