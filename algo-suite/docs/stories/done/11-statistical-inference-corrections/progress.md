# Progress — Story 11: statistical inference corrections

**Status:** done, September 27, 2026. Implementation, independent statistical
validation, gauntlet and final acceptance gates passed. See [quality evidence](evidence/quality-gates.md).

- [x] Record reproducible defects and current test-contract mismatch.
- [x] Define scope, acceptance criteria, migration, and primary DSR reference.
- [x] Specify the portfolio-return artifact and resampling method/assumptions.
- [x] Implement and independently validate probability-valued DSR.
- [x] Implement and validate paired time-series inference.
- [x] Migrate CLI/reporting contracts and inventory nine saved runs.
- [x] Complete quality gates, independent cleaner/hardener/QA and archive evidence.
- [x] Complete final manuscript verification and update inference-readiness tracking.

## Evidence

- [Registered method and simulation](method-design.md): daily UTC actual equity,
  classical DSR with declared selection history, paired stationary bootstrap.
- [Independent validation](evidence/README.md): six 80-digit reference checks;
  primary null rejection 6% and 7% under registered 8.775% tolerance at n=1200;
  primary effect-0.002 power 100% and 94%; all decisions coherent. Two block-length
  rules registered for 90–180-day windows both failed the size gate (reported in
  full); calibrated confirmatory paired inference needs a longer window or TD-62.
- [Saved-run smoke script](evidence/smoke-saved-runs.sh): both September pilot
  runs completed, each with zero trades and 30 recorded daily portfolio returns.
  Corrected statistics are unavailable (zero variance/degenerate differences at
  L=3 and L=1). No performance claim follows.
- Review follow-up (September 27): candle close confirmed as the LEAN mark from
  engine source and the engine `Return` series, which is now cross-checked;
  ledger-computed selection dispersion pinned to an independent constant; producer
  digest/adapter verification; strict `Return` containers; per-scenario
  error/unavailable channels; relative run identity; 174/174 mutants killed; see
  [lessons-learned](lessons-learned.md).
- [Local inventory](evidence/local-inventory.json) and
  [pilot inventory](evidence/pilot-inventory.json) preserve legacy outputs and list
  missing metadata. Metadata is reconstructed only on temporary smoke copies;
  raw run/model artifacts remain unchanged and no selection history is invented.
- `make audit`: no known vulnerabilities at execution time.
- Manuscript build and `make verify` passed after final text changes.

The exact inference contract is in the analyzer README. Broader readiness
(Task 10), event leakage, execution economics, validation design and H1 remain
open. Software validation does not turn the zero-trade pilot into inferential
evidence. See [spec.md](spec.md) and [QA procedure](qa-procedure.md).
