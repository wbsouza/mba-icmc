# Experiment takeover and consolidation progress

Updated: 2026-09-28 02:45 UTC (September 27, America/Vancouver).
Owner: Claude (integration and next protocol); Codex implementation and eight-run experiment complete. User stopped Claude and authorized implementation, experiments,
parallel agents, monograph updates, and incremental commits/pushes.

## Claude handoff — implementation and eight-run experiment complete

Start with [claude-handoff-prompt.md](claude-handoff-prompt.md), then the
[test/takeover procedure](qa-procedure.md). Refresh Git/process state before acting.
All implementation, eight accepted backtests, diagnostics, parameter tables and
96-page monograph are committed and pushed on `feat/13-pattern-volume-experiments`
in `/tmp/mba-pattern-volume`. Implementation snapshot: `28cc7d9`; final evidence:
`b0fc82c`. At the handoff check, local and live remote HEAD both matched `b0fc82c`
and the worktree was clean; this handoff documentation is the subsequent commit.
No Codex experiment remains running. No pending implementation task is delegated
to an agent. Do not rerun the completed matrix merely to reconstruct this session.

Next action: inspect branch ancestry and preserved dirty Claude worktrees, then
prepare an integration branch without resetting or blindly cherry-picking them.
Review/consolidation and a newly registered broader-window experiment are the next
phase, not claims of already completed work. This story remains in `in-progress`
pending that review/consolidation. Local verification is not remote CI certification.

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
| Parent Codex | main session | `/tmp/mba-pattern-volume` / `feat/13-pattern-volume-experiments` | Implementation, experiments, verification and evidence publication complete; handing over to Claude |
| Mendel | `01a0e56c-9c4e-7fa2-b824-94e042fc7b83` | Same Story 13 worktree/branch | TA-Lib detector complete; independent review and four native risk-calendar regressions complete |
| Poincare | `01a0e56c-9c8c-7960-b046-eec4b1aa7a5e` | Same Story 13 worktree/branch | Quote-activity/filter/provenance complete; trainer family validation and 16 targeted BDD scenarios pass |
| Herschel | `01a0e56c-c91f-70e2-bd1d-b84207343b70` | Same Story 13 worktree/branch | Complete-bar clock, fixed experiment matrix/runner and BDD complete; no job launched by agent |
| Ampere | `01a0e56c-9cc0-7cb1-b9e2-005b5432f357` | Same Story 13 worktree/branch | Prior and new eight-run snapshots, full parameter appendices, figures, chapters 04/05 and verification complete |

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
  understate overnight losses. Minute-level updates and four native regression
  scenarios now pass. Trainer family compatibility is checked before input loading.
- Fixed exploratory 2×2 pattern on/off × activity on/off matrix, separately for
  baseline and hybrid. SpockFX Dragon08 H4 risk/exit settings are mapped explicitly;
  EMA/swing entry logic remains a proxy, not an exact JapaDragon reproduction.
- Each runner cell archives effective filter settings, XML/config/code/input/model
  hashes, exact commands, resource budget, status, logs and results. Immutable input
  checks bracket batches; failed cells stop subsequent batches.
- Chapters 04/05 now contain verified intermediate predecessor results, including
  losses, zero-trade runs, missing provenance and selection-history limitations.

## Verification and evidence

- Final offline backtest suite: **1,364 passed, 53 integration scenarios deselected**.
- New native signal parity: M1/H1/H4 **3 passed**.
- Legacy native feature/news/DSHA parity after probe repair: **8 passed**.
- Calendar-risk native regressions: **4 passed in 13.24 seconds**.
- Trainer-family/provenance/runner targeted regression batch: **54 passed**.
- Scoped backtest/runner Ruff and strict mypy: pass (64 checked source files).
- Perception and inference architecture checks: pass.
- Extended perception host coverage: **283 passed**; native DSHA probe: **9 passed**
  after repairing its stale receiver. Merged perception coverage/CRAP gate passes:
  every scored function 100% line coverage, max CC/CRAP 7. Full mutations not rerun.
- `make audit`: no known dependency vulnerabilities; editable workspace packages
  skipped by the scanner as configured.
- Execution-chain integration suite: **9 passed, 16 deselected** in 1,162.82 seconds.
- Broad non-backtest suite on disk-backed retry: **504 passed, four deselected**.
- Whole-workspace checks have unrelated pre-existing lint/type failures; the scoped
  passes above do not imply `make check` is globally green.
- Final monograph `make verify`: **96 pages**, no undefined citations/references.
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
`6873b91` — verified predecessor results, parameter appendix, figures and monograph;
pushed.
`28cc7d9` — closed-bar signals, canonical activity provenance, immutable runner and
both independent-review fixes; pushed. `de34647` — detailed test/handoff procedure;
pushed. `4636ce7` — baseline outcome and inode-safe retry record; pushed.
`1f6b16f` — eight completed experiments and threshold diagnostics; pushed.
`fccd186` — expanded perception coverage/native gate and repaired wiring probe; pushed.
`b0fc82c` — final eight-run snapshot, complete parameter appendix, raw artifact archive,
figures and verified 96-page monograph; pushed.
Full execution-chain tests and the disk-backed broad retry are now green.

### Experiment execution and infrastructure incident

Baseline matrix `build/experiments/20260928-baseline-h4-v1` finished: all four cells
successful, parent exit 0, final immutable-input check `ok: true`. At the fixed
settings, activity off gives +1.36% return / six closed trades; activity on gives
+2.87% / three closed trades. Reported maximum drawdown is 5.1% for all four.
Candlestick on/off outcomes are identical; diagnostics below explain the unchanged decisions.
These are tiny reused-window samples, not evidence of significance or profitability.

Hybrid v1 had two successful cells then failed to create the last two results
directories when `/tmp` exhausted inodes (not bytes). The broad non-backtest test
run failed too: 462 passed / 42 failed / four deselected. Its 277,963-entry temporary
directory was **moved, not deleted**, to
`/home/wellington/workspace/mba-agents/experiment-test-archives/story13-workspace-pytest-5972-inode-failure`.
Approximately 278,000 inodes were freed without removing user data/worktrees.

The unchanged hybrid matrix completed in fresh
`build/experiments/20260928-hybrid-h4-v2` (session 29828 ended with exit 0).
All four cells succeeded and its final immutable-input check is `ok: true`.
All eight accepted runs therefore have successful parent/cell and integrity records.
Hybrid returns/trade counts/drawdowns match the baseline at these fixed settings.
The failed v1 archive is
preserved; its stale running statuses do not mean processes are still executing.
The broad test retry completed (504 passed) using the fresh **disk-backed** basetemp
`/home/wellington/workspace/mba-agents/experiment-test-archives/story13-workspace-recheck-20260928`
(session 94754, exit 0). See [qa-procedure.md](qa-procedure.md) for tests and takeover.

1. Risk-calendar/trainer regressions and implementation freeze are complete and pushed.
2. Both fresh matrices completed; failed hybrid v1 is preserved separately.
3. Every outcome and per-filter setting is archived in the new H01–H08 appendix.
4. New result snapshot, figures and 96-page monograph verified and published in `b0fc82c`.
5. Consolidate only after checking branch ancestry and dirty files. Story 13 already
   includes Story 12 through `7165308`; do not blindly reapply those commits or the
   shared agents' files. Review Claude's later hardener/QA/docs branches separately.
   Chapter 04 prewrite was inspected, not wholesale merged; resolve overlap by evidence.

No force-push, branch deletion, worktree removal, merge to main, or PR merge has been
performed by this takeover. Existing jobs are not promised indefinite monitoring.

## Claude integration record (2026-09-28, 01:35–02:00 UTC)

Owner: Claude (`mba-main` session). Takeover per `claude-handoff-prompt.md`; the user
authorized merging the open PRs into `main` and consolidating all work.

### State found

- No Codex or Claude agent running; no LEAN container running; `/tmp` at 74 % inodes
  (771,771 of 1,048,576), `/home` at 3 %. All three predecessor job scripts finished with
  `exit_code=0` (17:31–18:09 PT). Story 13 `1dbbef8` == `origin`, clean, contains story 12
  `7165308` and `origin/main` `5d3c8e8`.
- Outstanding Claude branches, all off `7165308`: `wave4/hardener` (1 commit `3d8b169`,
  story-12 mutation kills; its worktree also held an uncommitted, unverified draft — a
  temporary mutmut test-selection key plus new statement scenarios — saved as a patch, not
  merged), `wave4/qa` (2 commits: story-12 `qa-procedure.md`, `qa_check.py`, 39 scenarios),
  `wave4/docs` (4 commits: README/SPEC/PRD/architecture/debt sync, TD-66..68), `wave4/pattern`
  (no commits; superseded by story 13's TA-Lib detector; worktree left in place). Open PRs:
  #52 `docs/ch04-pilot-results` (3 commits off `main`), #53 `test/09-hardener-kills`
  (1 commit off `main`), #54 `feat/12-execution-realism`.

### Integration branch `integrate/story-12-13` (worktree `/tmp/mba-integrate`, from `1dbbef8`)

| Commit | Merge / change | Conflicts and resolution |
| --- | --- | --- |
| `dfc658e` | `wave4/hardener` | none |
| `4bb7b06` | `wave4/qa` | none |
| `bf3b5b8` | `wave4/docs` | `algo-backtest/README.md`, `SPEC.md`: union, story-13 TA-Lib wording kept, one-year loss stated |
| `c4e8a22` | `test/09-hardener-kills` (PR #53) | `f3_pattern.feature`, `strategies.feature`: exact-failure-text outlines kept; `price_features.feature`: both row sets; `test_strategy_validation.py`: keyword `_write_model`, story-13 callers adapted, duplicate step removed |
| `574b3d4` | follow-up | `buyhold` model-rejection scenario passes `cash` (controls take `cash` since story 12) |
| `e9b4abe` | `docs/ch04-pilot-results` (PR #52) | Chapter 4 resolved by union and evidence: pilot diagnosis, calibration, machinery verification, execution model and one-year protocol from #52; predecessor snapshot, sweeps and H4 matrix from story 13; `\pending` tables filled from the finished run directories; `img/equity-consolidated{,-2015q4}.png` from `algo-analyze equity-curves` |
| `b8213c7` | evidence + Chapter 5 | `evidence/predecessor-final-20260928T013528Z.{md,json}`; conclusion no longer calls R19/R20 unfinished |

Nothing was reset, force-pushed or deleted; `mba-main` stays dirty on `feat/09-…` (its
diff is exactly PR #53's content); shared-agent commits were not re-applied.

### Final predecessor outcomes (see the evidence file for definitions and run ids)

R08/R13 Sept −52.6/−52.8 %; R09/R14 Oct −53.4/−51.4 %; R10/P01 Nov −50.5/−52.8 %;
R19/R20 Mar–Oct 2016 −88.4/−87.5 % (1,029 trades each, every month negative). Sweeps:
R02 gated 0 trades; R01/R04/R05 −0.8/−3.8/−17.7 %; R03/R15/R16 −55.3/−53.5/−42.2 %;
R17/R18 0 trades. Monograph rebuilt: 106 pages, no undefined references.

### Data-coverage audit for the next protocol (read-only, 2026-09-28 01:45 UTC)

- EUR/USD M1 Parquet: every month 2015-01 → 2019-05 present; 2016 months hold 28,910–33,133
  rows each with continuous month boundaries.
- GDELT canonical events: `.done` for 2015-02 → 2016-11 (2016-11: 9,559,316 rows, 30
  distinct days); 2016-12 partial (8 days, no marker). Event features exist only per job
  data root; a new root must build them for its own span (+1 day for the last decision minute).
- Windows already consumed by a decision or a read outcome: Sept 2015 (gate, sweeps, H4
  matrix), Jan–Feb 2016 (calibration grids), Mar–Oct 2016 (R19/R20 outcomes read).
  **November 2016 is the only complete month no decision or reported outcome has touched.**

### Proposed broader-window protocol (to register before any outcome is viewed)

Same 2×2 pattern (disabled / TA-Lib) × activity (off / on) for baseline and hybrid, Dragon08 H4
clock, common capital/costs/risk, six canonical patterns, activity lookback 20 / threshold 1.0,
thresholds 0.55/0.45 gate off. Splits: fit 2015-03-02 → 2015-12-31, calibrate 2016-01,
hold out 2016-02, evaluate 2016-03-01 → 2016-11-30 as one continuous run per cell.
Classification: Mar–Oct 2016 **exploratory** (the M1 one-year outcomes on that span have been
read, though by a different model family and clock); **November 2016 confirmatory-eligible**
for the pre-registered primary comparison (hybrid vs baseline, TA-Lib on / activity off, paired
daily equity difference; block length set from the actual daily sample before viewing;
eight cells declared as the trial count). Warm-up: prime indicators from prior causal history
(February 2016) if the runner supports it; otherwise exclude the first 59 H4 bars identically
in every cell. Budget: six LEAN slots, 4 CPU / 8 GiB per container, two workers, fresh
disk-backed output root and basetemp, `df -i` checked first. Not launched in this session.

### Tuning sweeps and registered broad-window run (2026-09-28, 01:45–02:40 UTC)

- Registered broad-window matrices (PR #56 runner, `plan-broad-window.yaml`) executed through
  the immutable runner: baseline and hybrid, 4 cells each, all `succeeded`, final input checks
  `ok`; 0–1 closed trades per cell (−0.03 % where traded) because the H4 models' p_hat spans
  0.517–0.539 on the January validation bars and cannot cross 0.55/0.45. Output roots
  `/tmp/mba-broad/algo-suite/build/experiments/broad-window-{baseline,hybrid}-20260928T0152`.
- Thresholds re-registered as validation quantiles (5/10/15 % per side) before any 2016-03+
  outcome was viewed; calibration JSONs in the job dirs.
- Five exploratory sweeps, 51 variants, one-year splits, 2016-03-01..2016-11-30 one account
  each, rank on Mar..Oct and read November last: H4 fixed (14), H4 calibrated (11), timeframes
  M15/H1/H2 (9), H1 fixed variants (9), H1 calibrated (8). Evidence
  `evidence/tuning-sweeps-20260928T0240Z.{md,json}` + parameter appendix. Result: no variant
  profitable in November; positive Mar..Oct returns only at 17–65 trades and reversed in
  November; loss grows monotonically with trade count; detector on/off within 0.1 %.
- Job directories (local, gitignored): `data/training/2026-09-28-{broad-window-h4,h4-tuning-sweep,h4-tuning-sweep-q,tf-sweep,h1-tuning-sweep,h1-tuning-sweep-q}`.

### Registered follow-ups (2026-09-28, 03:30–04:10 UTC, before outcomes)

- December 2016 GDELT complete (31 days, `.done`); features built through 2017-01-01 in the
  broad-window root. `2026-09-28-dec-extension`: all 51 sweep variants rerun 2016-03-01..12-31.
- `2026-09-28-h1-open`: permissive H1 family (activity gate off, `ema_higher_tf` 9 vs slow 8 retrain,
  thresholds fixed/q05/q10, relaxed risk guard), 8 cells, 2016-03..12.
- `2026-09-28-h1-grid`: 216-cell H1 grid (thresholds x activity x HTF rule x plan x risk x family),
  6 LEAN slots x 3 CPUs, queued behind the two jobs above; `cpu-monitor.log` records load.
- Monograph Chapter 4 §registered-followups states the three designs and the trial count (275)
  before any result; results land in a later evidence file.
- Observed while rendering: `statement.py` prints prices with float noise (1.1225400000000001);
  fix queued for the next code PR.

## Story completion checklist

Check an implementation item only after its changes are committed and tests pass.

- [x] Inventory predecessor jobs and preserve their results and source revisions.
- [x] Add causal TA-Lib detection, deterministic conflict handling and BDD tests.
- [x] Add relative quote-activity calculation and configurable veto with BDD tests.
- [x] Wire identical closed-bar signals into offline training and LEAN execution.
- [x] Reject models trained with an incompatible signal/family contract.
- [x] Map SpockFX parameters and register controlled exploratory comparisons.
- [x] Verify native/offline parity, offline gates and dependency audit.
- [x] Train separate models, execute experiments and archive all outcomes.
- [x] Update monograph and parameter/result evidence for the new comparisons.

Final deliverables: [eight-run results](evidence/h4-results-20260928T011114Z.md),
[all per-run/filter parameters](evidence/h4-parameters-20260928T011114Z.md),
[raw models/results/failure archive](evidence/h4-run-artifacts-20260928T011114Z.tar.gz),
and [test/takeover procedure](qa-procedure.md). Seven evidence BDD scenarios and
scoped Ruff/mypy pass; monograph verification passes at 96 pages. Final archive
comparison against all three original matrix roots passes. No current Codex agent
has remaining implementation/experiment work. Review/merge/consolidation of earlier
Claude branches and broader-window experimental validation are separate next steps.

### Predecessor jobs: final read-only audit at 01:20 UTC

Ampere checked the five previously pending/planned runs against final `run.json`,
metrics and `trades.json`, not merely shell completion messages. All five record
`success=true`; each has configuration, provenance and `equity.csv`. No new job
was launched and no historical artifact changed. The frozen 00:36 snapshot and
its monograph discussion remain historical; Claude should publish a separate
later snapshot when integrating these final predecessor outcomes.

| Prior reference | Run/window | Closed trades | Return | Engine max drawdown |
| --- | --- | ---: | ---: | ---: |
| R02 | a05-gated, September 2015 | 0 | 0.00% | 0.0% |
| R10 | Baseline, November 2015 | 107 | −50.47% | 51.6% |
| P01 | Hybrid, November 2015 | 132 | −52.82% | 53.3% |
| R19 | Baseline, March–October 2016 | 1,029 | −88.41% | 88.8% |
| R20 | Hybrid, March–October 2016 | 1,029 | −87.50% | 88.2% |

P01 is `hybrid/20260928T004327-8e053507dfb3` under the predecessor
`2026-09-26-six-month-pilot/data/runs/` root. Other reference paths are in the
frozen predecessor snapshot. The three parent scripts report complete/exit 0,
and the process check found no active backtest/LEAN launcher. These are execution
successes, not strategy successes. They used predecessor settings; do not compare
them causally against the new H4 matrix or infer that zero trades proves efficacy.

### Why the pattern-on/off results match

Replay confirms TA-Lib operated on 110 complete September H4 bars and found 24 labels.
The first 59 bars were indicator warm-up; only 51 decisions remained, from September
16 20:00 through September 30 20:00 UTC. F1 vetoed 11, leaving 40 reaching F3.
TA-Lib produced eight non-abstaining recommendations there (four bearish engulfings,
three bullish engulfings, one hammer). The enabled pattern-family model has 50 trees
with three leaves, not the disabled model's constant prediction.

The combined F7 probabilities changed slightly but stayed below the fixed 0.45 SELL
threshold (disabled 0.408089–0.428667; enabled 0.408195–0.428762). Consequently the
final decisions and equity matched. Activity vetoed 17 of 40 eligible bars, leaving
23 SELL decisions instead of 40. This is threshold insensitivity in a small sample,
not failed detection or general evidence that patterns/news do not matter.
No threshold or period was adjusted after observing these results.
