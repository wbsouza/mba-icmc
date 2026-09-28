# Copy-paste prompt for Claude

Take over Story 13 from Codex. First read these files in
`/tmp/mba-pattern-volume/algo-suite/docs/stories/in-progress/13-pattern-volume-experiments/`:
`progress.md`, `qa-procedure.md`, `evidence/h4-results-20260928T011114Z.md`, and
`evidence/h4-parameters-20260928T011114Z.md`. Read repository instructions too.

## Verified starting point

- Branch: `feat/13-pattern-volume-experiments`, worktree `/tmp/mba-pattern-volume`,
  based on Story 12 `7165308`. Implementation `28cc7d9`; final evidence `b0fc82c`;
  later handoff-only commit follows. Refresh local and remote state yourself.
- All four Codex agents shared this one worktree with disjoint file ownership.
  Their changes are already integrated. Preserve the original dirty `mba-main`
  checkout and older Claude worktrees; their roster is in `progress.md`.
- Implemented and tested causal TA-Lib candlestick labels, a configurable relative
  quote-activity veto, shared closed-bar train/serve signals, H1/H4 timing, model
  compatibility checks, minute risk accounting and an immutable experiment runner.
  Candlesticks feed the existing pattern/model path; they are not a new hard veto.
  Activity is quote tick count divided by the prior 20-bar mean, not traded volume.
- Completed eight fixed exploratory September 2015 H4 runs: baseline/GDELT hybrid
  × candlestick disabled/enabled × activity off/on. Activity off: +1.36%, six closed
  trades; on: +2.87%, three trades; all engine drawdowns 5.1%. Only 51 decisions
  remained after warm-up. Pattern probabilities changed but did not cross the
  fixed decision threshold. Do not interpret these as significant gains.
- Models, logs, configs, metrics, equity and the failed inode-exhaustion attempt
  are committed in the raw artifact archive. All accepted input audits pass.
  Do not relaunch completed runs or overwrite them. Chapters 04/05 and the
  96-page monograph include the new results and full-parameter evidence links.
- Local checks: 1,364 offline backtest scenarios; 504 other workspace scenarios;
  native parity/risk/order-chain tests; scoped Ruff/mypy; architecture and perception
  coverage/CRAP; dependency audit; evidence tests; monograph verify all pass.
  Counts overlap. Full mutation campaign was NOT rerun. Global lint/type checks
  retain unrelated pre-existing failures. Consult the exact commands and limits.

## Next steps, in order

1. Inspect live Git/worktree/process state and branch ancestry. Prepare a separate
   integration branch combining reviewed Story 12/13 work and only genuinely
   outstanding Claude hardener/QA/docs changes. Resolve chapter conflicts against
   evidence. Do not reset dirty worktrees, duplicate shared-agent commits, or merge
   to main automatically. Record every decision, worktree and commit in progress.md.
2. Publish a separate final predecessor-results snapshot from actual artifacts:
   R02/R10/P01/R19/R20 finished; the long-window baseline/hybrid lost approximately
   88%. Preserve the earlier frozen snapshot and update the monograph transparently.
3. Before launching a new experiment, audit actual market/GDELT coverage and UTC
   availability, chronological train/calibration/evaluation boundaries, model vintage,
   warm-up and news missingness. Decide whether a genuinely untouched window exists;
   otherwise label the new evaluation exploratory. Do not invent missing data.
4. Register the broader-window protocol BEFORE viewing outcomes: retain baseline
   and hybrid and the same 2×2 pattern/activity ablation, common capital/costs/risk,
   H4 clock and SpockFX mapping. State all settings, seeds, budgets, trial ledger,
   primary comparison and multiplicity treatment. Preserve the six canonical
   patterns and activity lookback 20/threshold 1.0 unless a separately registered
   rationale changes them. No post-hoc threshold tuning to September results.
5. Fix warm-up comparability using prior causal history if supported and tested;
   otherwise report/exclude warm-up identically. Retrain compatible models on the
   registered training partition. Run a small native smoke before the full matrix.
   Validate registered bootstrap block length against the actual daily sample size;
   keep unavailable inference explicit rather than selecting blocks post-hoc.
6. Run fresh isolated output roots with bounded workers and input hashes. The prior
   budget was six shared LEAN slots, four CPUs/8 GiB per container, two workers per
   matrix. Check current load and disk INODES; use fresh disk-backed pytest basetemp.
   CPU is the proven path. No FinBERT/ModernBERT expansion without suitable timestamped
   text; current GDELT aggregates do not supply it. GPU is not a prerequisite.
7. Report each run's effective filter parameters beside outcomes, including failures,
   warm-up, veto counts, pattern counts, model/news provenance, closed/open exposure,
   returns/drawdowns/trades and valid paired inference where available. Archive raw
   artifacts, generate equity comparisons, update monograph and handoff, then run
   scoped and integration gates (and targeted mutation hardening before sign-off).
   Commit/push coherent batches with what/why. Do not claim profitability from this
   small reused window; do not hide the negative predecessor results.

First action: refresh state, read the handoff, and report the proposed integration
branch plus the data-supported evaluation window before launching new backtests.
