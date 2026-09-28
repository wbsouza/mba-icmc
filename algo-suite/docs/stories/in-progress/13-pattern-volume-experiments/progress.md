# Experiment takeover and consolidation progress

Updated: 2026-09-28 00:56 UTC (September 27, America/Vancouver).
Owner: Codex. User stopped Claude and authorized implementation, experiments,
parallel agents, monograph updates, and incremental commits/pushes.

## Current objective and boundaries

Implement causal candlestick and relative quote-activity filters, apply explicitly
mapped SpockFX settings, run controlled exploratory comparisons, and show every
filter's effective parameters beside each result. Preserve prior jobs, data, and
worktrees. Never label a running job or a successful shell `wait` as a completed run.

All current implementation work is in `/tmp/mba-pattern-volume`, branch
`feat/13-pattern-volume-experiments`, based on Story 12 commit `7165308`.
Worktree decision: **created a new isolated worktree**, rather than extending or
changing an existing Claude worktree. Story 13 extends the Story 12 code history,
not its working directory. All four current agents share the new worktree with
separate file ownership; no additional per-agent worktrees were created.
The original checkout remains on `feat/09-f7-config-regime-gate-cash` at `c6f9be3`;
its existing changes are not part of this work.

## Agent ownership and worktrees

The four Codex agents share one isolated Git worktree with disjoint write ownership.
They do **not** have four independent branches to cherry-pick. Parent Codex reviews,
integrates, commits and pushes their combined work on the Story 13 branch.

| Agent | Agent ID | Git worktree / branch | Ownership and status |
| --- | --- | --- | --- |
| Parent Codex | main session | `/tmp/mba-pattern-volume` / `feat/13-pattern-volume-experiments` | Integration, native parity, experiments, resource limits, Git and this log; active |
| Mendel | `01a0e56c-9c4e-7fa2-b824-94e042fc7b83` | Same Story 13 worktree/branch | TA-Lib detector and BDD complete; independent review found risk-calendar issue; writing focused regression |
| Poincare | `01a0e56c-9c8c-7960-b046-eec4b1aa7a5e` | Same Story 13 worktree/branch | Quote-activity calculation/filter, canonical input reader and hashes, BDD complete; tightening trainer family validation |
| Herschel | `01a0e56c-c91f-70e2-bd1d-b84207343b70` | Same Story 13 worktree/branch | Complete-bar clock, fixed experiment matrix/runner and BDD complete; no job launched by agent |
| Ampere | `01a0e56c-9cc0-7cb1-b9e2-005b5432f357` | Same Story 13 worktree/branch | Prior-run inventory, per-filter appendices, figures and monograph chapters 04/05 complete; awaiting new results |

## Prior Claude worktrees to consolidate separately

Observed with `git worktree list --porcelain`; these are preserved, not merged or
certified by the table. Agent attribution follows the handoff where known.

| Prior owner/task | Worktree | Branch | Observed HEAD |
| --- | --- | --- | --- |
| Claude main | `/home/wellington/workspace/mba-agents/mba-main` | `feat/09-f7-config-regime-gate-cash` | `c6f9be3` |
| Story 12 execution / active predecessor jobs | `/tmp/mba-story12` | `feat/12-execution-realism` | `7165308` |
| ch04-writer | `/tmp/mba-ch04` | `docs/ch04-pilot-results` | `ad227e9` |
| wave4-hardener | `/tmp/mba-w4-hardener` | `wave4/hardener` | `3d8b169` |
| wave4-qa | `/tmp/mba-w4-qa` | `wave4/qa` | `3a0698a` |
| wave4-docs | `/tmp/mba-w4-docs` | `wave4/docs` | `ecf3e2d` |
| wave4-pattern | `/tmp/mba-w4-pattern` | `wave4/pattern` | `7165308` |
| Earlier hardener | `/tmp/mba-hardener` | `test/09-hardener-kills` | `7d4a930` |
| Earlier cleaner | `/tmp/mba-w3-cleaner` | `wave3/cleaner` | `b3e457b` |
| Earlier equity | `/tmp/mba-w3-equity` | `wave3/equity` | `3142319` |

Additional older registered worktrees, not active Codex agents:
`/tmp/mba-w1-{a,c,e,f,h}`, `/tmp/mba-w2-{b,d}`, `/tmp/mba-story11-pr`,
`/tmp/mba-workflow-pr`, `/tmp/mba-pr40-review`, `/tmp/mba-pr40-review-r{2,3,4}`,
and `/tmp/opencode/pr40`. Inspect their status and ancestry before reuse; do not
infer that an old worktree represents unmerged work.

## What changed and why

- Real TA-Lib labels from closed midpoint OHLC replace the optional missing-pattern
  input. Detection stays disabled for historical models; mismatched model contracts
  fail with a retraining instruction. Scores are not confidence probabilities.
- Relative quote activity is current closed-bar tick count / prior 20-bar mean;
  threshold 1.0 is an independent veto. Canonical M1 input is hashed before/after
  execution. This is not centralized FX traded volume or LEAN QuoteBar size.
- A shared UTC closed-bar clock supports H1/H4 parity. Indicators count decision
  bars, while open-position management and calendar risk accounting remain minute
  based. Incomplete candles never generate decisions.
- Native/offline comparison exposed LEAN's RSI half-even loss rounding boundary;
  the offline implementation now follows that boundary. Old parity probes also
  needed the Story 12 capital-management setup; production fallback was not added.
- Independent review found H4 decisions could skip daily equity-anchor updates and
  understate overnight losses. Parent added minute-level updates; regression pending.
  Trainer family compatibility is being checked before expensive input loading.
- Fixed exploratory 2×2 pattern on/off × activity on/off matrix, separately for
  baseline and hybrid. SpockFX Dragon08 H4 risk/exit settings are mapped explicitly;
  EMA/swing entry logic remains a proxy, not an exact JapaDragon reproduction.
- Each runner cell archives effective filter settings, XML/config/code/input/model
  hashes, exact commands, resource budget, status, logs and results. Immutable input
  checks bracket batches; failed cells stop subsequent batches.
- Chapters 04/05 now contain verified intermediate predecessor results, including
  losses, zero-trade runs, missing provenance and selection-history limitations.

## Verification and evidence

- Offline backtest suite: **1,351 passed, 49 integration scenarios deselected**.
- New native signal parity: M1/H1/H4 **3 passed**.
- Legacy native feature/news/DSHA parity after probe repair: **8 passed**.
- Scoped backtest/runner Ruff and strict mypy: pass (64 checked source files).
- Perception and inference architecture checks: pass.
- `make audit`: no known dependency vulnerabilities; editable workspace packages
  skipped by the scanner as configured.
- Execution-chain integration suite still running; final result not yet claimed.
- Whole-workspace checks have unrelated pre-existing lint/type failures; the scoped
  passes above do not imply `make check` is globally green.
- Monograph `make verify`: **94 pages**, no undefined citations/references.
  Existing unrelated layout/duplicate-destination warnings remain.

Detailed frozen snapshot and per-run settings:
[intermediate evidence](evidence/intermediate-results-20260928T003601Z.md).
The snapshot records 16 successful final manifests, four running runs, a historical
failed launch and one planned run. It is not overwritten when later jobs finish.

## Resources, data and optional model ideas

Host: Ryzen 9 5900X, 12 cores/24 threads, 121.4 GiB RAM, RTX 3090 24 GiB.
User authorized more resources. The two identified predecessor LEAN containers
(`boring_panini`, `adoring_vaughan`) were raised from two to four CPUs during their
runs; this changes runtime quota, not their algorithm/settings. The evidence has
a timestamped operational addendum. New plans permit six shared LEAN slots,
four CPUs/8 GiB per container, four training numeric threads and up to two workers
per prepared matrix. No global default or unrelated container was changed.

Candidate input root (read-only):
`/home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/2026-09-26-six-month-pilot/data`.
34 market input files / 43 hybrid input files passed existence checks. A present
monthly file alone is not proof of complete time coverage; hybrid runs also validate
decision-window coverage. December's predecessor feature partition covers only Dec 1.

FinBERT/ModernBERT were suggestions **only if suitable for existing GDELT events**.
Available events/aggregate scores are not article text; no NLP model is being added.
ModernBERT-large is a base masked-language encoder requiring task fine-tuning, not
a ready sentiment classifier. Modern checkpoint use on 2015–2016 would also need
explicit model-vintage/leakage treatment. Local LightGBM OpenCL GPU capability worked
on a small synthetic probe but was slower; CUDA backend unavailable. CPU model
settings are unchanged. No model weights or Torch/Transformers were installed.

## Commit/push log and next actions

`3a705ef` — documentation: agent/worktree ownership, decisions, verification and
consolidation plan. Pushed to `origin/feat/13-pattern-volume-experiments`.
`2be2af2` — moved this file into the Story 13 directory as requested; pushed.
The next documentation commit archives the verified predecessor results and
monograph update, independently of the still-in-review implementation.
Implementation and evidence remain uncommitted pending the two review regressions.

1. Finish risk-calendar and trainer-family regressions; freeze code and commit/push.
2. Prepare fresh disjoint output directories with the immutable matrix/settings.
3. Run baseline/hybrid cells, archive every outcome, show settings alongside results.
4. Append a new evidence snapshot and monograph update; commit/push documentation.
5. Consolidate only after checking branch ancestry and dirty files. Story 13 already
   includes Story 12 through `7165308`; do not blindly reapply those commits or the
   shared agents' files. Review Claude's later hardener/QA/docs branches separately.
   Chapter 04 prewrite was inspected, not wholesale merged; resolve overlap by evidence.

No force-push, branch deletion, worktree removal, merge to main, or PR merge has been
performed by this takeover. Existing jobs are not promised indefinite monitoring.

## Story completion checklist

Check an implementation item only after its changes are committed and tests pass.

- [ ] Inventory predecessor jobs and preserve their results and source revisions.
- [ ] Add causal TA-Lib detection, deterministic conflict handling and BDD tests.
- [ ] Add relative quote-activity calculation and configurable veto with BDD tests.
- [ ] Wire identical closed-bar signals into offline training and LEAN execution.
- [ ] Reject models trained with an incompatible signal/family contract.
- [ ] Map SpockFX parameters and register controlled exploratory comparisons.
- [ ] Verify native/offline parity, offline gates and dependency audit.
- [ ] Train separate models, execute experiments and archive all outcomes.
- [ ] Update monograph and parameter/result evidence for the new comparisons.
