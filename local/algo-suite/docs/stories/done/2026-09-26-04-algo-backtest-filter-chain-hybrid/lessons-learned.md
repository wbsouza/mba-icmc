# Lessons learned — Spec 04 (parent: order-execution engine + filter chain + hybrid)

This is the umbrella story for lanes 04a-04h; each lane's own `lessons-learned.md`
(under its `done/` folder) has the concrete detail for its own scope. This file covers
only what's true at the parent level.

## What actually happened

The lane split (04a order-execution engine, 04b filter-chain mechanics, 04c price
filters F1-F3, 04d risk/capital filters F5/F6, 04e news filter F4, 04f audit trail, 04g
meta-learner F7, 04h hybrid integration) worked as designed: each lane landed
independently, mergeable in isolation, with 04h as the final integration point that
actually drives the whole chain against a real LEAN container. The real risk of a
lane-split design — that the pieces don't actually fit together until the very end — did
materialize, but only as expected: 04h's own closure found three real cross-cutting bugs
(a `duckdb` import eagerness in `algo_core`, a pyarrow childless-struct write failure, a
missing `algo_score` container copy) that no single lane's own tests could have caught,
because each is a boundary issue between two lanes' code, not a bug inside either lane.

## Vs. the spec

The parent spec's own Definition of Done (§7) — the order-execution engine running
against the real pinned LEAN container with all its Gherkin scenarios green, both
price-only algos migrated off inline order code, `baseline`/`hybrid` running through the
same chain engine, Experiment 0 landing, `decisions.parquet` persisted and joinable to
`trades.json` by `trade_id`, every strategy directory documented with a Mermaid diagram,
`make check`/`make audit` green, and the design docs updated — is now met exactly as
specified, with 04h as the lane that closed the final two items (the real LEAN run and
the `trade_id` join). No amendment to the parent spec was needed; every lane's own
found-gap was scoped and documented at the lane level (TD-48/49/50/51/52/56/57/58).

## What would be done differently

The lane-split approach itself worked well and would be repeated — the main
recommendation is narrower: **reserve real end-to-end integration testing (a real
container run, not a synthetic fixture) as its own explicit late lane**, not an
afterthought inside the "final" lane. 04h's own two-session gap (baseline wired and
proven; hybrid + the trade_id join deferred, then picked up a session later) shows this
naturally — the pure-Python lanes (04b-04g) all landed cleanly and quickly because they
could be fully proven with fixtures, while the two items that needed a real container
(the LEAN wiring itself, and the `decisions.parquet` join) both took longer and
surfaced the real bugs. A future multi-lane story with a similar shape should budget
the "real integration run" lane's time closer to the sum of all the pure-Python lanes
combined, not as a small tail item.
