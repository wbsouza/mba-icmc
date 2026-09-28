# Story 19: Adaptive training with rolling and exponential memory

Status: planned draft, September 28, 2026. No implementation or new experiment.
Number 19 was assigned after checking remote main on September 28: Story 18
belongs to market context (merged PR 77). This story is independent of the
candlestick plan in merged PR 76. Other story numbers are unchanged.

## User story

As a researcher, I want the engine to consume newly available data, wait for
labels to mature, train from recent evidence and load validated models on demand,
so that future decisions can adapt without altering earlier decisions or resetting
the account.

The user's final instruction is to create this story and plan with
tlc-spec-driven, not implement or execute it yet.

## Canonical plan

- [Requirements and acceptance criteria](../../../../../.specs/features/recency-weighted-retraining/spec.md): 28 traceable requirements.
- [Architecture and proposed experiment](../../../../../.specs/features/recency-weighted-retraining/design.md): lifecycle, temporal boundaries, controls and risks.
- [Implementation tasks](../../../../../.specs/features/recency-weighted-retraining/tasks.md): 19 tasks with tests, gates and dependencies.
- [Decisions and proposed defaults](../../../../../.specs/features/recency-weighted-retraining/context.md).
- [Progress and takeover instructions](progress.md).

This file is the story entry, not a second competing requirement specification.

## Proposed adaptive cycle

```text
Consume local data -> validate/persist watermark -> await mature labels
  -> train at registered boundary -> validate -> publish immutable model
  -> load on demand for future transactions -> record decisions -> repeat
```

Exponential forgetting means weighting observations by
w = 2^(-age_days / half_life_days), not averaging model parameters. Normalize
weights separately within family-model and combiner fitting. The proposed
half-life is 60 calendar days; it is not an empirically selected optimum.

## Proposed controlled comparison

| Policy | Update rule |
| --- | --- |
| F: frozen | Keep initial model, combiner and thresholds. |
| Q: threshold-only | Same model as F; update thresholds monthly. |
| R: rolling | Monthly refit with uniform trailing 180-day family history. |
| U: expanding | Monthly refit with uniform expanding history. |
| E: exponential | Same history as U, with exponential sample weights. |
| D60: daily, 60-day window | Fit daily on the trailing 60 days (combiner on its last 5 days), thresholds from the same window; bundle loaded on demand at the first decision after a trade closes (amendment 2026-09-28, user proposal). Trial done the same day: no improvement over F at either clock, models at coin-flip log-loss; kept as the short-window control, see `review.md`. |

Primary comparison E-U isolates weighting; D60-F (daily short window vs frozen) is the second registered contrast, motivated by the monthly pre-check in `review.md` (rolling 3-month refit 0.529 vs frozen 0.502 on the cut bars). Keep existing H1 q10 price-only
features, filters, costs, sizing and exits fixed. The candlestick/Laya extension
is independent and must not be introduced into this comparison.

All policies run one continuous account across updates. Cash, equity, open
orders, entry plans, indicator history and risk anchors never reset at month
boundaries. Every result includes all effective filter and training parameters.
Failed attempts stay in the ledger.

## Research and monograph boundaries

The inspected 2016-03 through 2017-02 period is exploratory. A new registration
does not turn previously viewed data into an untouched holdout. Report prediction
quality separately from trade profitability; a smaller dollar win alone is not
proof of drift. Report sample counts and dependence-aware paired daily inference.

Planned monograph deliverables:

1. Chapter 3: lifecycle, temporal purge, weight formula, controls and limitations
   before the registered comparison.
2. Chapter 4: actual parameter/result tables, uncertainty, failures and evidence
   references after execution and validation.

There are no new empirical findings to add now. Live deployment and adaptive
risk/exit changes are out of scope.

## Source baseline

The current F7 uses LightGBM family models and a logistic combiner; both fitting
stages lack sample weights in the inspected implementation. LEAN loads one model
at initialization. See the source-backed design for exact integration points.

[Session-2 registration at 4be718a](https://forge.wiseprax.ai/wellington.souza/mba-ai-capstone/src/commit/4be718aabd6b0f1036964a301d771a02d1a1f595/algo-suite/docs/stories/in-progress/15-session-2-clean-rerun/registration.md)
documents the frozen training/calibration timeline that motivated this hypothesis.
That experiment is historical context, not evidence for adaptive retraining.
