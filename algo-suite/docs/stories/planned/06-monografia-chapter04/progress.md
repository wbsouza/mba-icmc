# Progress — Spec 06 (monografia Chapter 4)

**Do not start until Specs 01–05 (all lanes) and Spec 04h are landed.**

**Update 2026-09-26: the tooling prerequisites are now met.** Specs 01–05 and every required Spec 04
lane (04a–04h, plus 04i/04j) are in `docs/stories/done/`. The optional 04k F1 perception candidate is also done, with a frozen-model smoke ablation. `algos/{baseline,hybrid}` run in the
LEAN container. TD-56 lets experiments start on the 2015-02..2015-07 GDELT window without
waiting for the full backfill. **Not started:** `monografia/chapters/04-experimental-evaluation.tex`
still has `\textit{To be added in the final version.}` in §sec:coverage-results through
§sec:experimental-threats. No run-id-traceable baseline or hybrid result has been written
yet. The next input still missing is real out-of-sample runs. Those need the GDELT event
features for the run months (see `../../in-progress/08-news-event-data-materialization/progress.md`).
The spec's §sec:coverage-results row is missing from the checklist below and is added here.

- [ ] §sec:experimental-setup rewritten with accurate, current pipeline description
- [ ] §sec:coverage-results written (Spec 02 coverage matrix + derived window)
- [ ] §sec:baseline-results written with real price-only numbers
- [ ] §sec:hybrid-results written with real hybrid numbers (needs Spec 04h)
- [ ] §sec:ablations written (needs Spec 05c)
- [ ] §sec:zhang-comparison written
- [ ] §sec:experimental-threats written
- [ ] `make verify` + `make pt-scan` clean (from `monografia/`)
