# Retraining experiment context

Status: draft, September 28, 2026. Story 19; Story 18 is market context.

## Feature Boundary

The user proposed sliding windows and exponential forgetting after observing
declining performance in graphs. They then explicitly replaced the execution
request with story/task planning using tlc-spec-driven. No run is authorized now.
They then confirmed that the engine must consume data, train in a full cycle,
and load models on demand for future transactions. This lifecycle is in scope;
it does not authorize implementation or live trading in this turn.

## Implementation Decisions

Keep entry features, costs, F1–F6 and execution settings fixed. Preserve continuous
account state across model refreshes. Publish full filter settings with results.
Document methodology before execution and verified findings afterward.

## Proposed architecture alternatives

Recommended: a host-side adaptive-cycle coordinator consumes validated batches,
tracks label maturity, triggers registered fits, validates and publishes immutable
bundles, and makes them available to LEAN's on-demand loader. Backtest mode uses
an explicit simulated availability clock and a retraining synchronization barrier.
This reuses portable model IO and avoids a trainer in the LEAN container. The
barrier and local request/response mechanism need a bounded feasibility task.
Replaying a previously materialized cycle is a reproducibility mode, not evidence
that the adaptive coordinator itself works.

Alternative: fit at each simulated boundary inside LEAN. It can deliver the same
causal schedule but adds runtime dependencies, training latency and failure
handling inside the executor. Do not adopt it without a new design review.

## Declined / Undiscussed Gray Areas → Assumptions

Monthly cadence, 60-day half-life, 180-day rolling fit, 30+30-day separated
calibration spans, one-day embargo, five H1 price-only policies and the existing
trading-year dates are proposed defaults in spec.md, not user approvals.
Failure blocks a candidate rather than silently retaining its prior model.
No fresh holdout data is claimed available.

## Parallel delivery and review

The September 28 request now plans Stories 19, 21 and 22 concurrently; it does
not authorize implementation in this turn. Follow the
[parallel delivery plan](../../../algo-suite/docs/stories/parallel-19-21-22.md).
Story 19 keeps its fixed legacy feature contract during its own comparison;
Story 22's encoder must not silently enter these five policies. Story 21's
relative-intensity thresholds are a separate rule, not F7 probability thresholds.

The later review is preserved with a
[decision-by-decision disposition](../../../algo-suite/docs/stories/in-progress/19-adaptive-recency-retraining/review-disposition.md).
Precomputed-first replay, an exact session-2 frozen control and the H4 extension
are alternatives for approval, not changes implicitly authorized by parallelism.

## Deferred Ideas

Half-life tuning, H4/news/hybrid replications, dynamic drift triggers, online
learning, prediction smoothing and new candle/volume combinations require a
separate registered extension. Session 2 is now archived as Story 20.
