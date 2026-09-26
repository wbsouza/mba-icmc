# Lessons learned — Spec 04e (news-context filter F4)

## What actually happened

The spec's own blocker check (confirm Spec 03's Parquet is real before writing any code
against a fixture) paid off by splitting cleanly in half: the **event** input
(`algo-score events --kind gdelt`) turned out fully real and buildable, but the
**sentiment** input turned out to be blocked by an order-of-magnitude data-volume fact
that wasn't visible until the check was actually run — a full month of GDELT Web News
NGrams raw text is ~500 GB / ~90 hours at the current adapter's throughput (TD-48), far
beyond this story's data-prep budget. Rather than stall on that, F4 was built so the
mandatory/best-effort split *is* the design: the event Parquet is fail-fast-mandatory,
the sentiment Parquet is best-effort and its absence is treated exactly like F1/F2/F3's
"no information yet" — ABSTAIN, recorded in `FilterResult.metadata["sentiment_source_present"]`
for audit, not a hard failure.

## Vs. the spec

- DoD asked for "reads real Spec 03 Parquet (not a synthetic fixture) in at least one
  integration scenario, VETO/ABSTAIN both covered" — met using real Jan-2020 GDELT
  `event_intensity` values (e.g. 2020-01-01 = -1.579, the month's real most-conflictual
  day), not synthetic numbers, which caught real formatting/type details a fixture
  would have hidden (the forward-filled per-minute grid, the base-minus-quote polarity
  differential sign convention).
- The spec didn't anticipate the sentiment/event split turning out this asymmetric —
  it reads as if both halves would land in the same story. TD-48 exists precisely
  because that assumption broke on contact with the real adapter's throughput.

## What would be done differently

The differential mutmut pass (`only_mutate = ["f4_news_context.py"]`) reached 144/148
(97.3%) only after a second look — the first pass left 18 "no tests at all" mutants in
`load_news_context_config()` and missed boundary conditions (`<=`/`<` on both
thresholds, `>=`/`>` on zero polarity) and a cross-symbol isolation case (a
`SymbolSentimentFeature` row for a different pair leaking into the queried pair's
lookup). Writing the boundary/isolation scenarios *before* running mutation testing,
not after, would have caught the same gaps without a second pass. The remaining 4
survivors are the same message-text-canary class already tracked project-wide
(TD-34/TD-36/TD-40) — recorded as TD-49 rather than chased individually, since fixing
them needs a project-wide exact-string-assertion decision, not a per-mutant patch.
