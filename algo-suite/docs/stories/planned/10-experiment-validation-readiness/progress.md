# Experiment validation readiness

Status: planned, added September 26, 2026 after the user identified missing
workflow stages. This is a required review before promoting pilot outputs to
methodology results, not a claim that the missing capabilities have been built.
The [workflow](../../../experimental-workflow.md) defines each exit gate.

- [ ] Register the final protocol, pair(s), dates, feature families, label,
  model/threshold search, trial count, and development/test separation.
- [ ] Reconcile BigQuery coverage, missing days, quarantine, GPR, and text-data
  status. Record the supported window and any pilot exception.
- [ ] Verify train/serve feature/config parity for every promoted variant and
  record absent features, including F3 patterns and text sentiment.
- [ ] Review label suitability and GDELT late-reporting leakage.
- [ ] Implement and exercise rolling refits, CPCV, and embargo, or explicitly
  record their deferral and limit the resulting claims. No unimplemented CLI
  flags or unexecuted folds may be described as results.
- [ ] Run known-answer engine controls and audit execution-cost/risk assumptions
  (spread, slippage, stops, pip value, margin, leverage).
- [ ] Inspect Task 09 model manifests, successful run exits, actual dates,
  decision/trade joins, and model hashes. Freeze models for subsequent windows.
- [ ] Generate paired metrics/figures, applicable significance and ablations,
  and replication evidence. A completed tool does not satisfy this checkbox.
- [ ] Complete [Story 11](../11-statistical-inference-corrections/spec.md):
  correct DSR semantics, consistent return frequency, paired time-series
  inference, and legacy-output migration before making significance claims.
- [ ] Reproduce reported results from recorded commands and artifacts, then
  update Chapter 4 and the limitations/future-work account in Chapter 5.

Dependencies: source readiness (Task 08), pilot execution (Task 09), and the
existing tool implementations. Task 06 may draft setup and limitations now;
empirical claims depend on this review. Task 07 performs final manuscript QA.
