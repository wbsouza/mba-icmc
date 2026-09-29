# Experiment registry

Every experiment session or job run in this project, in chronological order, with the
protocol status it was run under, where its evidence lives and where (if anywhere) the
monograph reports it. Maintained by hand; one entry per job directory.

**What a registry entry is.** A pointer to evidence, never a re-statement of it. Each entry
names the job directory (the launch-time name), the story and branch or pull request that
owned it, its protocol status, its window, its cells and models, one key result copied
verbatim from the evidence file it cites, and the Chapter 4 / Chapter 5 label under which
the monograph reports it. Numbers here are copied from the cited file and must not be
edited independently of it: if a number in this file and the evidence file disagree, the
evidence file wins and this file is wrong. Add a row when a job is registered or launched;
never rewrite an old row to make a result look different from its evidence.

**Protocol status vocabulary.**

- *registered before viewing*: the design, window, cell list, primary comparison and
  selection rule were written down (README or story registration file) before any cell of
  the job ran or any outcome of its window was read.
- *exploratory*: declared before viewing but on a window already consumed by an earlier
  decision, or a sweep whose selection history the monograph counts as trials.
- *ad-hoc*: run without a written registration, or stopped or re-specified after launch.

**Where the job directories are.** Every job before the confidentiality rename of
2026-09-28 (session 1) was moved, not deleted, out of `algo-suite/data/training/` into
`/home/wellington/workspace/mba-agents/experiment-test-archives/pre-rename-session-1/`
on 2026-09-28 07:25 UTC (story 20 progress). Those directories keep their launch-time
names and file names; some of them still carry launch-time strategy names that are under
the author's confidentiality agreement, so this registry refers to them by dated job name
only and to their cells by the sanitized names used in the story evidence. The archive
also holds `broad-window-h4-runs/` (the session-1 LEAN runs root that every 2026-09-28
sweep wrote into; session 2 reused the same input root after emptying its run
directory) and `viewer-db/` (the
session-1 results databases); neither is a job. The session-2 job stays in
`algo-suite/data/training/2026-09-28-session-2/` (local, gitignored) with its input root
`2026-09-28-broad-window-h4/`. Both `data/training/` and the archive are read-only inputs
for this registry.

**Dates.** The date column is the UTC time of the job's `exit-status.txt` (recorded by the
machine in `-07:00` and converted here), or the registration time when the job did not
finish. README and story files also state UTC registration times ("registered HH:MM
UTC"); for several session-1 jobs those are minutes to half an hour later than the
machine's exit timestamp for the same stage. A file-time audit (entries 14, 18 and 19)
reconciles them: each stage's plan, variant list and strategy configurations were written
seconds before that stage launched, so every cell was fixed before its own launch, while
the README paragraphs that state a registration time were written after the stage had
finished. Those stated times are writing times, not pre-registration times; the file
modification times are the record of when each design was fixed. The pre-specified
primary comparison of the trading year comes from the one-year protocol (Chapter 4
`subsec:one-year-protocol`), not from those paragraphs.

## Index

| # | Date (UTC) | Job directory | Story, branch / PR | Protocol status | Monograph |
|---|---|---|---|---|---|
| 1 | 2026-05-26 | none (`experiments/baseline-comparison.yaml`, results in `algo-suite/docs/first-baseline-results.md`) | pre-story price-only baselines, done story `2026-05-26-algo-backtest-price-only-baselines` | ad-hoc | not reported |
| 2 | 2026-09-27 05:45 | `2026-09-26-six-month-pilot` (archived) | story 09, `feat/09-f7-config-regime-gate-cash`, PR #51 | exploratory (window written down 2026-09-26 before the run; September became development data once the gate decision read its outcome) | Ch. 4 `subsec:zero-trade`, `tab:pilot-splits`, `subsec:intermediate-provenance`, `subsec:machinery-verification` |
| 3 | 2026-09-27 10:16 | `2026-09-27-f7-ungated-september` (archived) | story 09, PR #51 | exploratory (gate off and thresholds chosen after the zero-trade diagnosis; thresholds calibrated on July 2015 only) | Ch. 4 `subsec:threshold-calibration` / `tab:threshold-calibration`, `sec:baseline-results` / `tab:september-replay`, `sec:hybrid-results`, `subsec:machinery-verification` |
| 4 | 2026-09-28 00:31 | `2026-09-27-variant-sweep-sept-b` (archived) | story 12, `feat/12-execution-realism`, integrated by PR #55 | ad-hoc September-2015 sweep (machinery check on development data) | Ch. 4 `sec:ablations` / `tab:intermediate-sweeps` (R15–R18) |
| 5 | 2026-09-28 00:41 | `2026-09-27-variant-sweep-sept` (archived) | story 12, PR #55 | ad-hoc September-2015 sweep | Ch. 4 `sec:ablations` / `tab:intermediate-sweeps` (R01–R05) |
| 6 | 2026-09-28 01:09 | `2026-09-27-execution-realism` (archived) | story 12, PR #55 | exploratory: machinery check of the execution model on Sept–Nov 2015, not the experiment | Ch. 4 `subsec:execution-model`, `sec:confirmation-results` / `tab:confirmation-2015`; Ch. 5 `sec:final-remarks` |
| 7 | 2026-09-28 01:09 | `2026-09-28-one-year-protocol` (archived) | story 12, PR #55 | registered before viewing (2026-09-27, before any 2016 bar was simulated; window extended to October 2016 before the first bar) | Ch. 4 `subsec:one-year-protocol` / `tab:one-year-splits`, `subsec:intermediate-annual`, `sec:confirmation-results` / `tab:one-year-results`, `tab:one-year-monthly`, `fig:equity-consolidated`; Ch. 5 `sec:final-remarks` |
| 8 | 2026-09-28 01:11 | `build/experiments/20260928-baseline-h4-v1` and `20260928-hybrid-h4-v2` (story-13 worktree; raw archive removed from the repository, see entry) | story 13, `feat/13-pattern-volume-experiments`, PR #55 | exploratory (previously inspected September 2015, `plan.yaml` `classification: exploratory`) | Ch. 4 `subsec:h4-snapshot` / `tab:h4-results`, `tab:h4-parameters`, `tab:h4-diagnostics`, `fig:h4-equity`; Ch. 5 `sec:final-remarks` |
| 9 | 2026-09-28 01:52 | registered broad-window matrices (`plan-broad-window.yaml`; output roots `/tmp/mba-broad/algo-suite/build/experiments/broad-window-{baseline,hybrid}-20260928T0152`; input root `2026-09-28-broad-window-h4`) | story 13, PR #56 (runner), PR #57 | registered before viewing (`registration.registered_at: 2026-09-28T01:44:00Z`; November 2016 confirmatory-eligible) | Ch. 4 `subsec:tuning-sweeps` (prose: "zero or one trade in each of its eight cells") |
| 10 | 2026-09-28 01:51 | `2026-09-28-h4-tuning-sweep` (archived) | story 13, PR #57 | exploratory, declared before viewing (README: 01:55 UTC) | Ch. 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps`; Ch. 5 `sec:final-remarks` |
| 11 | 2026-09-28 02:08 | `2026-09-28-h4-tuning-sweep-q` (archived) | story 13, PR #57 | exploratory, thresholds re-registered as validation quantiles before any 2016-03+ outcome was viewed | Ch. 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps`, `fig:equity-tuning-h4q` |
| 12 | 2026-09-28 02:13 | `2026-09-28-tf-sweep` (archived) | story 13, PR #57 | exploratory, declared before viewing (README: 02:05 UTC) | Ch. 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps` |
| 13 | 2026-09-28 02:31 | `2026-09-28-h1-tuning-sweep` (archived) | story 13, PR #57 | exploratory, declared before viewing (README: 02:25 UTC) | Ch. 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps` |
| 14 | 2026-09-28 02:31 | `2026-09-28-h1-tuning-sweep-q` (archived) | story 13, PR #57 | exploratory, declared before viewing (files written 02:18 UTC before launch; the README text says 02:35 UTC, see entry) | Ch. 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps` |
| 15 | 2026-09-28 04:35 | `2026-09-28-dec-extension` (archived) | story 13, PR #59 | registered before viewing (registered before any December bar was read; story progress 03:30–04:10 UTC) | Ch. 4 `subsec:registered-followups` |
| 16 | 2026-09-28 04:37 | `2026-09-28-h1-open` (archived) | story 13, PR #59 | exploratory, declared before viewing (README: 04:05 UTC); called a curiosity check by the monograph | Ch. 4 `subsec:registered-followups` (prose only: "recorded only in the story evidence") |
| 17 | 2026-09-28 05:08 (stopped) | `2026-09-28-h1-grid` (archived) | story 13, PR #59 | exploratory, declared before viewing; stopped by the user after a fraction of its cells | Ch. 4 `subsec:registered-followups` (prose only); counted in the trial count of `sec:experimental-threats`; no result in the monograph |
| 18 | 2026-09-28 05:38 (news-only) and 05:52 (rule arm) | `2026-09-28-news-only` (archived) | story 14, `feat/14-news-only-strategy` PR #60 (code), PRs #61, #62 (docs) | registered before viewing (cells and calibration fixed before launch per file times; the README stating 05:40 and 06:05 UTC was written at 06:07 UTC, see entry) | Ch. 4 `subsec:news-only` |
| 19 | 2026-09-28 06:21 to 07:31 | `2026-09-28-trading-year` (archived) | story 14, PRs #63, #65 | registered before viewing (file-time audit: each stage's plan and configurations written seconds before its launch; the README's "registered" times are writing times, see entry) | Ch. 4 `subsec:trading-year` / `tab:trading-year`, `fig:equity-trading-year` |
| 20 | 2026-09-28 07:00 (registered) to 07:25 (stopped) | `2026-09-28-tf-year` (archived) | no story file; user request recorded in the job README | registered before viewing (README: 07:05 UTC), then stopped for session 2 | not reported (session 2 re-ran the sub-hour q10 cells) |
| 21 | 2026-09-28 03:30–04:28 (file times) | `2026-09-28-reports` (archived) | rendering bundle for the viewer and the monograph, not an experiment | none | none |
| 22 | 2026-09-28 07:40 (registered) to 08:36 | `2026-09-28-session-2` (local, `algo-suite/data/training/`) | story 20 (registered as 15, renumbered by PR #78), `exp/session-2`, PR #74 | registered before viewing (README written before any cell ran) | Ch. 4 `subsec:session-2` / `tab:session-2`, `fig:equity-session-2`; TD-71 |

Chapter 5 has no per-experiment subsection. `sec:final-remarks` summarizes entries 6, 7, 8
and 10–14 by their Chapter 4 sections; no other entry is cited in Chapter 5.

## Entries

### 1. Price-only baselines on EUR/USD 2024-06 (2026-05-26)

- **Window.** No training split: rule strategies (moving-average crossover and mean
  reversion). Backtest 2024-06-03 to 2024-06-28, $100k cash, long-only, fixed sizing 0.5.
- **Cells and models.** Two runs (`ma-eurusd-2024-06`, `meanrev-eurusd-2024-06`), M1
  clock, no learned model.
- **Key result (as stated).** Both baselines lose money: 288 closed trades, total return
  −0.0095, Sharpe −9.59 (moving-average); 6 trades, −0.0018, Sharpe −14.60 (mean reversion).
- **Evidence.** `algo-suite/docs/first-baseline-results.md` (result table, window and exact
  commands; raw run artifacts were not committed and are regenerated by re-running).
- **Monograph.** Not reported in Chapter 4 or 5.

### 2. Six-month training and first September-2015 replay (`2026-09-26-six-month-pilot`)

- **Window.** Family fitting 2015-02-02 to 2015-06-30; combiner calibration July 2015;
  trainer held-out August 2015; LEAN replay 2015-09-01 to 2015-09-30 (M1 clock, 15-minute
  label). First attempt started 2026-09-27 04:43 UTC and failed on the missing broker
  adapter (`attempt-1-*` files); resumed supervisor finished 2026-09-27 05:45 UTC, exit 0.
- **Cells and models.** Two cells (baseline, hybrid), two models (`baseline-f7.json`
  SHA-256 `1a6fd37e…4e831e`, `hybrid-f7.json` `a6dda4c2…06af9b7`), 153,531 fitting /
  32,813 calibration / 30,297 held-out rows each; `--param size=0.5`, $100,000 engine
  default.
- **Key result (as stated).** Both replays completed with `success=True` and zero closed
  trades (`baseline/20260927T044836-4cd12c922200`, `hybrid/20260927T053156-4f2ebf081eaf`).
  Diagnosis: with the regime gate on, p̂ < 0.50 on every one of 11,540 bull bars and
  p̂ > 0.49 on every one of 11,827 bear bars, so all 23,367 bars reaching F7 were HOLD;
  8,145 bars were vetoed by F1.
- **Evidence.** Story record
  `algo-suite/docs/stories/done/09-six-month-training-september-pilot/progress.md`
  ("Decision", "Execution", "Zero-trade diagnosis") and `evidence.json` (model hashes and
  provenance); archived job directory (`run.sh`, `status.txt`, `exit-status.txt`,
  `baseline-september.log`, `hybrid-september.log`, `baseline-f7.json`, `hybrid-f7.json`);
  story 11 `done/11-statistical-inference-corrections/evidence/pilot-sources.json`
  (30 daily returns per run, unchanged source hashes).
- **Monograph.** Chapter 4 `subsec:zero-trade`, `tab:pilot-splits`,
  `subsec:intermediate-provenance`, `subsec:machinery-verification`.

### 3. September-2015 replay with the gate off (`2026-09-27-f7-ungated-september`)

- **Window.** Same frozen models and data root as entry 2; replay 2015-09-01 to
  2015-09-30; thresholds 0.55/0.45 calibrated on the July-2015 validation span, regime gate
  off, $10,000 account (`--param cash=10000`, still `size=0.5`). Finished 2026-09-27
  10:16 UTC, exit 0, code revision `709b9bd` plus the recorded uncommitted amendment.
- **Cells and models.** Two cells, the two 2026-09-26 models unchanged (hashes in
  `model-hashes.txt`).
- **Key result (as stated).** Baseline `baseline/20260927T094856-5d34ecde9301`: 1,032
  closed trades, $10,000 → $9,995.38 (−0.05%), max DD 1.5%, win rate 60%. Hybrid
  `hybrid/20260927T100447-5e124bec56dc`: 1,069 trades, $10,000 → $10,051.41 (+0.51%), max
  DD 1.5%, win rate 62%. F4 abstained on all 23,367 hybrid bars. Threshold grid: at
  0.55/0.45 gate off, July validation 5,140 signals (15.7%), directional hit 0.568
  (baseline). "Not an economic result" per the story record.
- **Evidence.** Story 09 `progress.md` ("Amendment — 2026-09-27") and
  `evidence/threshold-calibration.json`, `evidence/qa-procedure.md`, `evidence/qa_check.py`;
  archived job directory (`run.sh`, `git-revision.txt`, `model-hashes.txt`, two simulation
  logs). Runs R07/R12 in story-13
  `evidence/intermediate-results-20260928T003601Z.md` and its parameter appendix.
- **Monograph.** Chapter 4 `subsec:threshold-calibration` / `tab:threshold-calibration`,
  `sec:baseline-results` / `tab:september-replay`, `sec:hybrid-results`
  (`fig:intermediate-equity` shows R08/R13, entry 6), `subsec:machinery-verification`.

### 4. September-2015 template-plan variant sweep (`2026-09-27-variant-sweep-sept-b`)

- **Window.** Frozen pilot baseline model (entry 2), 2015-09-01 to 2015-09-30, $10,000,
  execution model of story 12. Finished 2026-09-28 00:31 UTC, exit 0, code `7165308`.
- **Cells and models.** Four variants run in parallel (the archived `run.sh` status
  string says five), one model. Evidence names: R15 `ha-h1-template`, R16
  `ha-h1-template-atr`, R17 `ha-1r2r-template`, R18 `ha-setup-template`. The job's own
  variant directories and log names carry launch-time names not repeated here.
- **Key result (as stated).** R15 144 trades −53.47% (max DD 55.8%); R16 437 trades
  −42.16% (50.1%); R17 and R18 0 trades, 0.00%.
- **Evidence.** Story 13
  `evidence/predecessor-final-20260928T013528Z.md` (table and variant overrides) and
  `evidence/per-run-parameters-20260928T003601Z.md`; archived job directory (`run.sh`,
  `exit-status.txt`, `model-hashes.txt`, per-variant `*-parameters.txt` and `*-2015-09.log`).
- **Monograph.** Chapter 4 `sec:ablations` / `tab:intermediate-sweeps`.

### 5. September-2015 reference-plan variant sweep (`2026-09-27-variant-sweep-sept`)

- **Window.** As entry 4. Finished 2026-09-28 00:41 UTC, exit 0, code `7165308`.
- **Cells and models.** Five variants extending `baseline` (one knob each plus their
  combination), one model. Evidence names: R01 `reference-conservative`, R02
  `reference-gated`, R03 `reference-risk1`, R04 `reference-selective`, R05
  `reference-wide-stop`.
- **Key result (as stated).** R01 3 trades −0.81% (DD 10.8%); R02 0 trades; R03 552 trades
  −55.28% (55.4%); R04 6 trades −3.76% (5.6%); R05 14 trades −17.65% (21.5%).
- **Evidence.** As entry 4 (same two story-13 evidence files; archived job directory).
- **Monograph.** Chapter 4 `sec:ablations` / `tab:intermediate-sweeps`.

### 6. Execution-model reruns Sept–Nov 2015 (`2026-09-27-execution-realism`)

- **Window.** Frozen 2026-09-26 six-month models; three monthly replays 2015-09,
  2015-10, 2015-11, each from a fresh $10,000; execution model (risk-based lots, stop and
  target orders, trailing stop, partial close, 1-pip spread). Finished 2026-09-28 01:09 UTC,
  exit 0, code `7165308`.
- **Cells and models.** Six runs (baseline and hybrid per month), two models.
- **Key result (as stated).** R08 baseline Sept 320 trades, win 22.2%, net −$5,256.84,
  return −52.57%, max DD 53.8%; R13 hybrid Sept 322, 22.0%, −$5,275.22, −52.75%, 54.0%;
  R09/R14 Oct −53.35% / −51.37%; R10/P01 Nov −50.47% / −52.82%. September baseline:
  249 trades closed at the stop, 65 at the 2R limit, 6 liquidated; lots margin-capped near
  1.66 so realized risk about 0.8% per trade.
- **Evidence.** Story 13 `evidence/predecessor-final-20260928T013528Z.md` (run ids),
  `evidence/intermediate-results-20260928T003601Z.md` (R08/R09/R13/R14 at the 00:36 UTC
  snapshot), `evidence/per-run-parameters-20260928T003601Z.md`; story 12 `spec.md`
  ("Registered protocol") and `progress.md`; archived job directory (`run.sh`,
  `git-revision.txt`, `model-hashes.txt`, `baseline-parameters.txt`,
  `hybrid-parameters.txt`, six run logs). LEAN artifacts were written under the pilot's
  data root `2026-09-26-six-month-pilot/data/runs/`.
- **Monograph.** Chapter 4 `subsec:execution-model`, `sec:confirmation-results` /
  `tab:confirmation-2015`; Chapter 5 `sec:final-remarks`.

### 7. One-year protocol, M1 chain (`2026-09-28-one-year-protocol`)

- **Window.** Registered 2026-09-27 with the user before any 2016 bar was simulated:
  family fitting 2015-03-02 to 2015-12-31, combiner calibration January 2016, trainer
  held-out February 2016 (no replay), one continuous simulation per strategy 2016-03-01 to
  2016-10-31 (extended from 2016-09-30 on the evening of 2026-09-27, before the first bar
  was simulated), $10,000, execution model, M1 clock. Pre-registered threshold rule:
  0.55/0.45 gate off unless the January validation hit rate falls below 0.5. Finished
  2026-09-28 01:09 UTC, exit 0, code `7165308`.
- **Cells and models.** Two cells (R19 baseline `baseline/20260928T000117-8bb8148c2302`,
  R20 hybrid `hybrid/20260928T000142-8bbdd0d8fd2c`), two models (`0b41fd39ebf3…`,
  `b67ac32e1fc5…`), 312,878 fitting / 28,802 calibration / 30,120 held-out rows.
- **Key result (as stated).** R19 1,029 trades, win 25.0%, net −$8,840.72, return
  −88.41%, max DD 88.8%, profit factor 0.64; R20 1,029 trades, 24.8%, −$8,775.76, −87.50%,
  88.2%, 0.63; every month negative for both. No paired inference computed (block length
  and trial count not registered before evaluation).
- **Evidence.** Story 13 `evidence/predecessor-final-20260928T013528Z.md` (table,
  monthly returns), `evidence/intermediate-results-20260928T003601Z.md` (training
  diagnostics, anti-alignment); story 12 `spec.md` and `progress.md`; archived job
  directory (`run.sh`, `git-revision.txt`, `model-hashes.txt`, `baseline-f7.json`,
  `hybrid-f7.json`, `threshold-calibration.json`, `calibrate_thresholds.py`,
  `calibration.log`, training and simulation logs, `data/runs/`).
- **Monograph.** Chapter 4 `subsec:one-year-protocol` / `tab:one-year-splits`,
  `subsec:intermediate-annual`, `sec:confirmation-results` / `tab:one-year-results`,
  `tab:one-year-monthly`, `fig:equity-consolidated`; Chapter 5 `sec:final-remarks`.

### 8. H4 candle and quote-activity matrix on September 2015 (`20260928-baseline-h4-v1`, `20260928-hybrid-h4-v2`)

- **Window.** `plan.yaml` (`classification: exploratory`): fit 2015-02-02 to 2015-06-30,
  calibrate July 2015, held out through 2015-09-30, evaluate 2015-09-01 to 2015-09-30, H4
  clock, label horizon 240 minutes, $10,000. Snapshot clock-confirmed 2026-09-28
  01:11:14 UTC; final integrity checks 01:04:27 and 01:10:10 UTC.
- **Cells and models.** Eight cells H01–H08 (baseline and hybrid × detector disabled /
  TA-Lib × activity gate off / on), one model per cell. An interrupted hybrid v1 root
  (two cells succeeded, two hit ENOSPC) is preserved separately and is not a replication.
- **Key result (as stated).** Activity off: 6 closed trades, +1.36%, engine max DD 5.1%
  (H01, H03, H05, H07); activity on: 3 trades, +2.87%, 5.1% (H02, H04, H06, H08). Only 51
  decisions per cell after warm-up; candle on/off and baseline/hybrid outcomes identical.
- **Evidence.** Story 13 `evidence/h4-results-20260928T011114Z.md`,
  `h4-parameters-20260928T011114Z.md`, `h4-snapshot-20260928T011114Z.json`,
  `h4-decision-audit-20260928T011114Z.json`, `h4-figure-provenance-20260928T011114Z.json`,
  `figures/h4-*`; `h4-run-artifacts-20260928T011114Z.REMOVED.md` records that the raw
  three-root archive was removed from the repository (SHA-256
  `7bdc1ef9…1cf2c`, retained locally under `experiment-test-archives/`). Runner:
  `algo-suite/experiments/heikin-ashi-signals/` (`README.md`, `plan.yaml`, `runner.py`).
- **Monograph.** Chapter 4 `subsec:h4-snapshot` / `tab:h4-results`, `tab:h4-parameters`,
  `tab:h4-diagnostics`, `fig:h4-equity`; Chapter 5 `sec:final-remarks`.

### 9. Registered broad-window H4 matrices (`plan-broad-window.yaml`)

- **Window.** Fit 2015-03-02 to 2015-12-31, calibrate January 2016, held out through
  2016-02-29, evaluate 2016-03-01 to 2016-11-30 as one continuous run per cell, H4 clock,
  fixed thresholds 0.55/0.45, $10,000. Registration block: `registered_at
  2026-09-28T01:44:00Z`, primary comparison hybrid vs baseline (TA-Lib on, activity off,
  paired daily equity difference), trial count 8, `confirmatory_months: ['2016-11']`,
  first 59 H4 bars excluded identically. Output roots timestamped `20260928T0152`.
- **Cells and models.** Eight cells (four baseline, four hybrid), one model per cell,
  executed through the immutable runner; both final input checks `ok=True`.
- **Key result (as stated).** Activity-off cells 1 trade, −3.00%, max DD 4.0%; activity-on
  cells 0 trades, +0.00% (both families). Cause: the H4 models' p̂ spans 0.517–0.539 on the
  99 January-2016 validation bars and cannot cross 0.55/0.45.
- **Evidence.** Story 13 `evidence/tuning-sweeps-20260928T0240Z.md` ("Registered
  broad-window matrices" and "Threshold calibration"), `progress.md` ("Tuning sweeps and
  registered broad-window run"); plan
  `algo-suite/experiments/heikin-ashi-signals/plan-broad-window.yaml`; input root README
  `algo-suite/data/training/2026-09-28-broad-window-h4/README.md` (local). The output
  roots under `/tmp/mba-broad/` were not archived into `pre-rename-session-1/`.
- **Monograph.** Chapter 4 `subsec:tuning-sweeps` (prose).

### 10. H4 tuning sweep, fixed thresholds (`2026-09-28-h4-tuning-sweep`)

- **Window.** One-year splits (fit 2015-03-02 to 2015-12-31, calibrate January 2016, held
  out February 2016); one continuous $10,000 account per variant 2016-03-01 to
  2016-11-30, H4 clock; rank on March–October, November read last; primary comparison
  t12-hybrid-base vs t01-base; trial count for any November claim 14. README declared
  01:55 UTC; `exit-status.txt` finished 2026-09-28 01:51 UTC, exit 0.
- **Cells and models.** Fourteen variants t01–t14; three models (A baseline+TA-Lib,
  B baseline+detector disabled, C hybrid+TA-Lib).
- **Key result (as stated).** Zero trades in 11 of 14 variants (fixed 0.55/0.45 never
  fires on the H4 models); t03-vol-0.8 and t14-candle-vol-off 1 trade, −3.00%, max DD
  4.0%; t06-theta-52-48 56 trades, win 18%, −14.60% Mar–Oct, −5.01% Nov, −19.01% full,
  max DD 22.5%.
- **Evidence.** Story 13 `evidence/tuning-sweeps-20260928T0240Z.md` (section "H4 fixed
  thresholds 0.55/0.45 (14 variants)", with run ids) and
  `tuning-sweeps-parameters-20260928T0240Z.md`, `tuning-sweeps-20260928T0240Z.json`;
  archived job directory (`README.md`, `h4-threshold-calibration.json`,
  `calibrate_h4_thresholds.py`, `models/`, `logs/`).
- **Monograph.** Chapter 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps`; Chapter 5
  `sec:final-remarks` (as part of the 51 variants).

### 11. H4 tuning sweep, calibrated thresholds (`2026-09-28-h4-tuning-sweep-q`)

- **Window.** As entry 10; thresholds set from the models' January-2016 validation
  quantiles (primary 10% per side; 5% and 15% as sensitivity), declared before any
  2016-03+ outcome was viewed; primary comparison q10-hybrid vs q10-base; trial count so
  far 34. Finished 2026-09-28 02:08 UTC, exit 0.
- **Cells and models.** Eleven variants per README and `variants.txt` (the results table
  also lists t06-theta-52-48); the same three models as entry 10.
- **Key result (as stated).** q10-base 100 trades, −12.10% Mar–Oct, −1.33% Nov, max DD
  21.0%; q10-hybrid 109, −15.81%, −1.16%, 22.9%; q10-atr-stop 65, +9.04% Mar–Oct, −6.03%
  Nov, 25.0%; the template-plan variant traded nothing because `min_reward_risk 2.0`
  vetoes a plan whose first target is 1R (variant error, kept for the record).
- **Evidence.** Story 13 `evidence/tuning-sweeps-20260928T0240Z.md` ("H4 calibrated
  thresholds (11 variants)"); archived job `results.md`, `README.md`,
  `equity-consolidated.{png,html}`, `logs/`.
- **Monograph.** Chapter 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps`,
  `fig:equity-tuning-h4q`.

### 12. Timeframe sweep M15 / H1 / H2 (`2026-09-28-tf-sweep`)

- **Window.** As entry 10, varying only the decision bar (M15, H1, H2), fixed thresholds
  0.55/0.45, label horizon one bar. README declared 02:05 UTC; finished 2026-09-28
  02:13 UTC, exit 0. Trial count across both sweeps 23.
- **Cells and models.** Nine variants (per timeframe: candles with activity on, activity
  off, hybrid with activity on); six models (baseline and hybrid per timeframe).
- **Key result (as stated).** h1-candle-vol-on 18 trades, +11.45% Mar–Oct, −2.46% Nov;
  h1-hybrid-candle-vol-on 17, +13.55%, −2.46%; m15-candle-vol-on 58, −13.98%, −1.15%;
  h2 candle cells 0 trades. On the H1 models 0.55 is the 98th percentile of p̂ and 0.45
  below its minimum, so the H1 runs were effectively long-only on about 2% of bars.
- **Evidence.** Story 13 `evidence/tuning-sweeps-20260928T0240Z.md` ("Timeframes M15 /
  H1 / H2"); archived job `results.md`, `README.md`, `tf-threshold-calibration.json`,
  `models/`, `logs/`.
- **Monograph.** Chapter 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps`.

### 13. H1 tuning sweep, fixed thresholds (`2026-09-28-h1-tuning-sweep`)

- **Window.** H1 models from entry 12; variants of the H1 base over 2016-03-01 to
  2016-11-30; primary comparison h1-hybrid-candle-vol-on vs h1-candle-vol-on. README
  declared 02:25 UTC; finished 2026-09-28 02:31 UTC, exit 0. Trial count so far 43.
- **Cells and models.** Nine variants (the results table lists eleven rows including the
  two entry-12 H1 cells as reference); the two H1 models.
- **Key result (as stated).** h1-hybrid-vol-off 31 trades, +15.01% Mar–Oct, −2.62% Nov,
  +12.01% full, max DD 10.7%; h1-theta-53-47 209 trades, −23.33%, −3.51%, 48.7%;
  h1-theta-57-43 0 trades; h1-vol-0.8 21 trades, +14.80% Mar–Oct, −2.46% Nov.
- **Evidence.** Story 13 `evidence/tuning-sweeps-20260928T0240Z.md` ("H1 fixed-threshold
  variants (9)"); archived job `results.md`, `README.md`, `logs/`.
- **Monograph.** Chapter 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps`.

### 14. H1 tuning sweep, calibrated thresholds (`2026-09-28-h1-tuning-sweep-q`)

- **Window.** As entry 13 with symmetric quantile thresholds (5/10/15% per side) from
  `tf-threshold-calibration.json`. The README text says "Declared 2026-09-28 02:35 UTC";
  the job's files show `README.md`, `run.sh`, `variants.txt`, `model-map.json`,
  `model-hashes.txt` and the `strategies/` directory all written at 02:18:11 UTC, the
  first cell's parameter dump at 02:18:12 UTC, `exit-status.txt` at 02:31:57 UTC (exit 0)
  and `results.md` at 02:32:26 UTC. The stated 02:35 matches none of these; the batch was
  declared and launched at 02:18 UTC. Trial count so far 51.
- **Cells and models.** Eight variants; the two H1 models.
- **Key result (as stated).** h1-q05-base 114 trades, +3.08% Mar–Oct, −8.01% Nov;
  h1-q10-base 196, −26.59%, −4.59%; h1-q15-base 316, −51.13%, −8.78%; h1-q10-hybrid 204,
  −19.86%, −7.54%; h1-q15-hybrid 327, −58.72%, −5.57%.
- **Evidence.** Story 13 `evidence/tuning-sweeps-20260928T0240Z.md` ("H1 calibrated
  thresholds (8)"); archived job `results.md`, `README.md`, `logs/`.
- **Monograph.** Chapter 4 `subsec:tuning-sweeps` / `tab:tuning-sweeps`.

### 15. December extension of the 51 tuning variants (`2026-09-28-dec-extension`)

- **Window.** All 51 sweep variants (entries 10–14) rerun as continuous $10,000 accounts
  2016-03-01 to 2016-12-31 with their original models and configurations; November stays
  the first untouched month, December the second, read after it. Registered before any
  December bar was read (December GDELT completed 2026-09-28 03:30 UTC). Finished
  2026-09-28 04:35 UTC, 51/51 exit 0.
- **Cells and models.** 51 cells, the models of entries 10–14 unchanged.
- **Key result (as stated).** Nov positive 0/51, Dec positive 10/51, both 0/51; full
  Mar–Dec above deposit 9/51 (best +9.05% on 37 trades, h1-hybrid-vol-off).
- **Evidence.** Story 13 `evidence/december-extension-20260928T0445Z.md` and
  `evidence/tuning-followups-part1-20260928T0445Z.md`; archived job `results.md`,
  `README.md`, `plan.tsv`, `logs/`.
- **Monograph.** Chapter 4 `subsec:registered-followups`.

### 16. Permissive H1 family (`2026-09-28-h1-open`)

- **Window.** One-year splits; models retrained with `ema_higher_tf 9` (higher-timeframe
  agreement disabled), activity gate removed; thresholds fixed 0.55/0.45, calibrated 5%
  and 10%; one variant with a relaxed risk guard; 2016-03-01 to 2016-12-31, $10,000. README
  declared 04:05 UTC; finished 2026-09-28 04:37 UTC, exit 0. Trial count so far 59.
- **Cells and models.** Eight cells; two retrained models (baseline, hybrid).
- **Key result (as stated).** Fixed-threshold cells 0 trades; h1-open-q05 293 trades
  −38.01% full (max DD 42.7%); h1-open-q10 586 trades −52.12% (59.1%); h1-open-q10-hybrid
  572 trades −37.65% (52.5%).
- **Evidence.** Story 13 `evidence/tuning-followups-part1-20260928T0445Z.md`
  ("Permissive H1 family"); archived job `results.md`, `README.md`, `calibration.json`,
  `models/`, `logs/`.
- **Monograph.** Chapter 4 `subsec:registered-followups` (prose: curiosity checks
  "recorded only in the story evidence").

### 17. H1 combinatorial grid, stopped (`2026-09-28-h1-grid`)

- **Window.** 216 cells = thresholds {fixed, 5%, 10%} × activity gate {off, 1.0, 0.8} ×
  higher-timeframe rule {strict, relaxed} × plan {HA-H4 template, 1R/2R template, ATR
  stop} × risk guard {standard, relaxed} × family {baseline, hybrid}; span 2016-03-01 to
  2017-01-31 (January 2017 a third read-last month); models from entries 12 and 16.
  Started 2026-09-28 04:37 UTC; **stopped by the user** (`status.txt`:
  `stopped_by_user=curiosity_experiment`, 05:08 UTC, `cells_done=20`; README: stopped
  05:12 UTC after 11 of 216 cells). Trial count so far 59 + 216 = 275.
- **Cells and models.** `logs/runs-exit.txt` lists 26 cells: 11 exit 0, 6 exit 143
  (terminated), 3 exit 1, 6 exit 137 (killed). No results table was produced.
- **Key result (as stated).** None tabulated; README: "nothing from this job enters the
  monograph". Finished cells stayed in the runs root (now `broad-window-h4-runs/`).
- **Evidence.** Archived job `README.md`, `status.txt`, `variants.txt`, `make_grid.py`,
  `cpu-monitor.log`, `logs/grid.log`, `logs/runs-exit.txt`, per-cell run logs. Story 13
  `progress.md` ("Registered follow-ups (2026-09-28, 03:30–04:10 UTC)").
- **Monograph.** Chapter 4 `subsec:registered-followups` (prose) and the trial count in
  `sec:experimental-threats`; no result.

### 18. News-only and rule-only news strategies (`2026-09-28-news-only`)

- **Window.** One-year splits; H1 and H4 clocks; F4 → F5 → F6 → F7 with F7 fitted on the
  news family only; thresholds 0.55/0.45 or, if unreachable, 5% and 10% January quantiles
  decided from the calibration JSON; one $10,000 account per cell 2016-03-01 to
  2016-12-31; rank on March–October, November and December read last; primary comparison
  news-only vs price-only baseline at H1. The spec text says "registered 05:40 UTC" and
  that the rule-only arm (F4 decides from the intensity at the January-2016 90% / 10%
  quantiles 0.6294 / −0.0046, both sign conventions) was "added 06:05 UTC, before any
  cell ran". File-time audit (UTC): `run.sh` 05:31:57; calibration files 05:34:09–13;
  first run log 05:34:21; news-only stage exit 05:38:54; rule-arm strategy configurations
  05:51:31; rule stage exit 05:52:52; job `README.md` (the registration text) 06:07:42.
  Reading: the cells and their calibrated thresholds were fixed before launch (the
  thresholds come from the calibration JSON, not from a 2016-03+ outcome), and the
  README paragraph was written after both stages had finished; its stated times are
  writing times. Trial count 10.
- **Cells and models.** Six news-only cells (2 clocks × fixed/q05/q10) and four rule
  cells (2 clocks × 2 signs); two models (`news-only-h1` 4,739 fitting rows,
  `news-only-h4` 1,030; January band H1 0.5253–0.5288, H4 0.5245–0.5265).
- **Key result (as stated).** Fixed-threshold cells 0 trades; news-only-h1-q10 230 trades
  −38.45% (max DD 46.5%); news-only-h4-q10 75 trades −14.39%; news-rule-h1-plus 178
  trades −47.02%; news-rule-h1-minus 39 trades +12.91% (short-only in practice), positive
  in both untouched months; EUR/USD drift −3.37% March 1 → December 31 is the confound.
  Paired inference: primary news-only-h1-q10 vs h1-candle-vol-off on Nov–Dec +0.001%/day,
  95% CI [−0.341%, +0.344%], p = 0.996; news-rule-h1-minus vs price-only p = 0.237.
- **Evidence.** Story 14 `spec.md` (registration), `progress.md`,
  `evidence/news-only-cells-20260928T0545Z.md`, `news-only-parameters-20260928T0545Z.md`,
  `news-only-calibration-20260928T0545Z.json`, `intensity-quantiles-jan2016.json`,
  `news-cells-20260928T0600Z.md`, `paired-inference-20260928T0615Z.{md,json}`; archived
  job (`README.md`, `results.md`, `paired-inference.{md,json}`, `calibration.json`,
  `intensity-calibration.json`, `models/`, `logs/`).
- **Monograph.** Chapter 4 `subsec:news-only`.

### 19. One trading year, all arms, with supplements and controls (`2026-09-28-trading-year`)

- **Window.** One-year models of entries 12, 13 and 18 reused unchanged; one $10,000
  account per cell 2016-03-01 to 2017-02-28; March–October 2016 development data, November
  2016 to February 2017 untouched, read last; primary comparison hybrid vs price-only at
  H1, paired daily equity on the untouched months (block 4, sensitivity 2, 999 resamples,
  seed 42). The README text says registered 06:25 UTC; supplement 06:50 UTC
  (`q10-atr-stop`, `h1-vol-0.8`); control 06:58 UTC (`short-when-flat-*`, found
  mis-specified and corrected 07:15 UTC to `always-short-*`); both-sides supplement
  07:05 UTC (four calibrated H1 cells); gated supplement 07:10 UTC. `exit-status*.txt`:
  main 06:21, supplement 06:24, control2 06:31, control 06:34, both-sides and gated
  07:31 UTC, all exit 0. Trial count 22.
- **Timestamp audit (file modification times, UTC).** Each stage's `plan*.tsv` and
  strategy configurations were written seconds before its launch: ten main cells
  06:12:24 → launch 06:12:41 → finished 06:21:48; supplement 06:21:02 → 06:21:03 →
  06:24:49; long-whenever-flat control 06:30:03 → 06:30:04 → 06:31:33; always-short
  control 06:32:58 → 06:32:59 → 06:34:26; both-sides 07:03:25 → 07:03:28 → 07:31:35;
  gated 07:04:05 → 07:04:07 → 07:31:35. The README's "registered HH:MM UTC" paragraphs
  for the first four stages were written after those stages finished
  (`paired-inference.md` 06:23:17, `results.md` 06:35:01, README mtime 07:04:05).
  Conclusion: every cell was fixed before its own launch; the primary comparison was
  pre-specified in the one-year protocol (Chapter 4 `subsec:one-year-protocol`); the
  registration paragraphs' times are writing times, not pre-registration times. The audit
  table is appended to story 14 `evidence/trading-year-registration.md` (branch
  `docs/ch05-lessons-2026-09-28`, PR #83), and Chapter 4 carries one sentence about it.
- **Cells and models.** Ten registered cells + 2 + 2 + 2 + 4 + 2 supplement and control
  cells (22 runs; the mis-specified long-whenever-flat pair reported as such at H1 −29.0%,
  H4 −14.5%); no new model.
- **Key result (as stated).** h1-candle-vol-off 44 trades −1.22% full (max DD 17.7%);
  h1-hybrid-vol-off 43 trades −0.78% (18.9%); news-only-h1-q10 252 trades −38.41%;
  news-rule-h1-minus 39 trades +12.20%; always-short-h1 298 trades −7.79%, identical to
  the rule on Dec–Feb; q10-vol-off (H4) 223 trades −4.47%; q10-hybrid-vol-off 239 trades
  −5.54%. Primary hybrid vs price-only H1: −0.048%/day on the untouched months,
  95% CI [−0.115%, +0.019%], p = 0.149; full year +0.001%/day, p = 0.938. The long-
  whenever-flat control exposed the same-bar OCO double fill (TD-71).
- **Evidence.** Story 14 `evidence/trading-year-registration.md` (registration text
  and, on PR #83, the timestamp audit table),
  `trading-year-cells-20260928T0640Z.md`, `trading-year-inference-20260928T0640Z.{md,json}`,
  `progress.md`; archived job (`README.md`, `results.md`, `paired-inference.{md,json}`,
  `plan*.tsv`, `run-*.sh`, `exit-status*.txt`, `equity-trading-year-h1.{png,html}`,
  `logs/`); `algo-suite/docs/technical-debt.md` TD-71.
- **Monograph.** Chapter 4 `subsec:trading-year` / `tab:trading-year`,
  `fig:equity-trading-year`.

### 20. Timeframe year M5 / M15 / M30, stopped (`2026-09-28-tf-year`)

- **Window.** One-year splits; one $10,000 account per cell 2016-03-01 to 2017-02-28;
  TA-Lib candles on, activity gate off, Heikin-Ashi H4 risk template, label horizon one
  bar; per clock baseline and hybrid with fixed 0.55/0.45 and 10% January-quantile
  thresholds. README registered 07:05 UTC before any cell ran (`status.txt` stages
  06:56 train, 06:57 calibrate, 06:59 simulate). Stopped by `stop-all-jobs.sh` at 07:25 UTC
  for session 2 (story 20 progress); `exit-status.txt` records `exit_code=0` at 07:31 UTC.
  Trial count 12.
- **Cells and models.** Twelve cells, six new models (`m5/m15/m30-{baseline,hybrid}`).
  `logs/runs-exit.txt`: m5-base-q10, m5-hybrid-q10 and m15-base-q10 exit 1 (their run
  logs record `success=True` with 1810, 1803 and 1825 closed trades before the statement
  step failed, TD-71); six cells exit 143 (terminated); m30-base-q10, m30-hybrid-q10 and
  m30-hybrid-fixed have no run log.
- **Key result (as stated).** No results table was produced. Session 2 (entry 22) re-ran
  the sub-hour q10 cells with retrained models and reports them as failed at the statement
  step (five of six) or, for m15-q10-hybrid, −98.34% on 1,804 trades.
- **Evidence.** Archived job `README.md`, `status.txt`, `exit-status.txt`, `variants.txt`,
  `models/`, `logs/` (`runs-exit.txt`, `calibration.log`, per-cell run and parameter
  logs); session-2 README ("Known: session-1 M5 q10 cells failed after the backtest in the
  statement step").
- **Monograph.** Not reported; the sub-hour clocks appear only through session 2
  (`subsec:session-2`) and TD-71.

### 21. Rendering bundle, not an experiment (`2026-09-28-reports`)

- **Contents.** Rendered outputs only: `equity-h1-variants{.png,-dashboard.html}`,
  `equity-h4-calibrated{.png,-dashboard.html}`, `equity-one-year-m1.png`,
  `equity-sept-nov-2015-m1.png`, `equity-review.html`, four `h1-hybrid-vol-off-report*.html`
  and `h1-hybrid-vol-off-equity-and-statement.html`, `monograph-tcc-110p.pdf` (file times
  2026-09-28 03:30–04:28 UTC). No run, model or registration; the figures derive from the
  runs of entries 6, 7, 11 and 13.
- **Evidence.** The archived directory itself.
- **Monograph.** None (the figures the monograph uses are regenerated under
  `monografia/img/`).

### 22. Session 2: clean trading-year re-run, BUY and SELL in one simulation (`2026-09-28-session-2`)

- **Window.** Unchanged from entry 19: EUR/USD, models fit 2015-03-02 to 2015-12-31,
  combiner calibrated January 2016, February 2016 held out, one $10,000 account per cell
  2016-03-01 to 2017-02-28; March–October development, November 2016 to February 2017
  untouched. Twelve models retrained under clean template names; thresholds recomputed.
  Registered 07:40 UTC before any cell ran; models trained at `b72b3f1`, simulations at
  `cb418b9` (same code apart from PR #73 comments and docs). Training stage
  `exit-status-train.txt` 07:49 UTC (two news-only trainers re-run after a strategies-dir
  fallback failure); simulation stage `exit-status-simulate.txt` 08:36 UTC, `exit_code=1`
  because five sub-hour cells failed the statement step. Trial count 26.
- **Cells and models.** 26 cells (18 both-sides headline cells, 2 always-short controls,
  3 reproduction-only fixed-threshold cells, plus the sub-hour cells), 12 models; six LEAN
  slots. 21 cells completed; m5-q10-base, m5-q10-hybrid, m15-q10-base, m30-q10-base,
  m30-q10-hybrid stopped at the statement step (TD-71), left unpatched as registered.
- **Key result (as stated).** Reproduction: 12 models identical after dropping
  provenance; 15 comparable cells identical (same trades, per-trade P/L, byte-identical
  `equity.csv`), and the session-1 primary test reproduces (−0.048%/day, p = 0.149).
  Both-sides year: h1-q10-base 516 trades −43.72% (max DD 57.8%); h1-q10-hybrid 514 trades
  −32.94% (46.8%); h1-q05-base −15.31%, h1-q05-hybrid −25.05%; h1-q10-gate-base −57.06%,
  h1-q10-gate-hybrid −42.47%; h4-q10-base −4.47%, h4-q10-hybrid −5.54%; m15-q10-hybrid
  1804 trades −98.34%. Primary hybrid vs price-only H1 q10: −0.016%/day on the untouched
  months, 95% CI [−0.145%, +0.113%], p = 0.806; full year +0.050%/day, p = 0.307. Gated
  pair +0.057%/day, p = 0.071 (untouched). Reversed-sign rule vs always-short control:
  H1 −0.010%/day, p = 0.920; H4 −0.005%/day, p = 0.921.
- **Evidence.** Story 20 `registration.md`, `spec.md`, `progress.md`,
  `evidence/results.md`, `evidence/reproduction.md`, `evidence/paired-inference.{md,json}`,
  `evidence/calibration.json`, `evidence/intensity-calibration.json`,
  `evidence/model-hashes.txt`, `evidence/model-map.json`, `evidence/runs-exit.txt`,
  `evidence/train-exit.txt`, `evidence/git-revision-{train,simulate}.txt`,
  `evidence/variants.txt`, `evidence/equity-session2-h1.png`, `scripts/`; local job
  directory `algo-suite/data/training/2026-09-28-session-2/` (`README.md`, `results.md`,
  `reproduction.md`, `paired-inference.md`, `models/`, `strategies/`, `logs/`, `reports/`).
- **Monograph.** Chapter 4 `subsec:session-2` / `tab:session-2`, `fig:equity-session-2`;
  `algo-suite/docs/technical-debt.md` TD-71.

## Offline checks on 2026-09-28

Analysis-only checks over the session-2 decision log and training rows. Nothing was
traded, no model of any entry above was changed, and every window used was already
viewed; these are exploratory readings that inform planned stories, not experiments.
Same rule as above: this section points, it does not restate.

| Check | What it reads | Where the evidence is | State |
|---|---|---|---|
| Signal-horizon check | `decisions.parquet` of session-2 `h1-q10-base`, hourly GDELT intensity, hourly mid closes; forward 1 h and 4 h returns conditioned on the rule firing, F1/F2/F3 state and 20-day / 6-month momentum, 2016-03-01 to 2017-02-28 | `algo-suite/docs/stories/in-progress/21-confluence-chain/evidence/signal-horizon-check.md` on branch `docs/21-confluence-chain` (PR #82) | table present on the branch tip at the time of writing |
| Candlestick-as-trigger check | same decision log, F3 label as the trigger conditioned on the rule | same file, same branch and PR (per the story-21 plan) | check the branch tip: the file held the signal-horizon table only when this registry was written |
| Support/resistance check | same decision log, level context | same file, same branch and PR (per the story-21 plan) | as above |
| Rolling-retraining pre-check | H1 price-only F7 refit month by month over 2016-03 to 2017-02 under four policies (F frozen, R3 rolling 3-month, R6 rolling 6-month, U expanding); out-of-sample hit rate, log-loss and hit rate on the q10 cut bars; same code, seed and rows as session 2 | `algo-suite/data/training/2026-09-28-session-2/rolling_precheck.py`, `logs/rolling-precheck.log`, `rolling-precheck-h1-base.json` (local) | table present: twelve-month averages F hit 0.498 / log-loss 0.6948, R3 0.507 / 0.6932, R6 0.503 / 0.6937, U 0.505 / 0.6934; months with log-loss below 0.6931: F 2/12, R3 5/12, R6 5/12, U 4/12 |
| Daily-recalibration pre-check | each trading day 2016-03-01 to 2017-02-28, trailing windows of 15, 30, 45 and 60 days; thresholds-only (frozen model, q10 cuts from the window) and refit (family models on the window minus its last 5 days, combiner on those 5 days) | `algo-suite/data/training/2026-09-28-session-2/daily_precheck.py`, `logs/daily-precheck.log` (local) | pending: the log had no table when this registry was written |

The two pre-checks feed story 19 (adaptive retraining, `docs/19-adaptive-recency-retraining`)
and the three decision-log checks feed story 21 (confluence chain); neither story has a
registered experiment yet, so no entry above exists for them.
