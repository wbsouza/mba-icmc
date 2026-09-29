# Lessons learned — Story 19 (adaptive recency-weighted retraining)

The original spec assumed a full five-policy comparison would fit in one
session alongside Stories 21/22/23 and the monograph. Under real deadline
pressure the honest choice was a minimum-viable engine slice (one bundle,
one pinned load path) proven with a real backtest, rather than a five-arm
comparison built partly on assumption. That's the right call under time
pressure: a real, disclosed result for one policy beats an untested claim
about five.

Two real correctness gaps were found during implementation that the spec
didn't anticipate: bundle identity was originally scoped to the ingestion
ledger's global watermark instead of each epoch's own cutoff (a future-tail
leak into a supposedly-frozen bundle), and the cycle coordinator's watermark
check originally rejected two independent policies replaying the same
already-consumed batches as a false conflict. Both are the kind of bug that
only shows up once you actually try to run multiple policies against the
same data, not from reading the spec alone.

What would be done differently: register the full five-policy study's exact
cells and dates *before* touching engine code, the same discipline this
session's other stories (21, the candlestick sweep) applied — that would
have made "run all five, not just one" the default plan from the start
rather than a fallback under pressure.
