# Story 19 — progress

- [x] 2026-09-28 07:25 UTC — all session-1 jobs stopped (`stop-all-jobs.sh`), 19 job directories and the
  run root (832 MB) moved to `experiment-test-archives/pre-rename-session-1/`; viewer database archived.
- [x] 07:40 UTC — job `2026-09-28-session-2` registered (README, 26 cells, 12 models) before any run.
- [x] 07:40 UTC — stage 1 at `b72b3f1`: ten models trained (rows: H1 5642, H4 1235, same as session 1);
  the two news-only trainers failed because the trainer resolves `--strategies-dir` without the packaged
  fallback the run command has (`unknown strategy 'news-only'`). Fix: packaged configs snapshotted into
  the job's strategies directory; retrain via `run-train-fix.sh`. A second script bug (wrong attribute
  name in `calibrate.py`) cost one more calibration pass (`run-calibrate.sh`).
- [x] 07:42 UTC — PR #73 merged (`f438156`, comments/docs only); simulation stage ran at that revision.
- [x] 07:49–08:36 UTC — stage 2: 26 cells, six LEAN slots. 21 completed; 5 sub-hour cells (M5 both, M15
  price-only, M30 both) finished their simulation but stopped at the statement step on the same-bar OCO
  double fill (TD-71); left unpatched as registered (`evidence/runs-exit.txt`).
- [x] Reproduction (`evidence/reproduction.md`): 12 models identical outside the provenance block; all
  calibrated thresholds identical to four decimals; 15 comparable cells identical (trades, per-trade P/L,
  byte-identical `equity.csv`); the session-1 primary test reproduces (−0.048 %/day, p = 0.149).
- [x] Both-sides results (`evidence/results.md`, `evidence/paired-inference.md`): every learned cell
  negative on the year; primary H1 q10 hybrid vs price-only p = 0.81 (untouched) / 0.31 (year); gated pair
  p = 0.071 / 0.099 but both arms −42 % / −57 %; rule vs always-short control p = 0.92 at H1 and H4.
- [x] Chapter 4 `subsec:session-2` + `tab:session-2` + `fig:equity-session-2` (118 pages, no undefined
  references); TD-71 row updated; viewer database rebuilt from the 18 finished headline cells
  (`results-viewer-demo/rebuild-session2.sh`).
- [ ] Review and merge (user). Then move the story to `done/` with `lessons-learned.md`.
- [ ] Deferred: fix TD-71 before any sub-hour result; rising-euro window (2017-03..08) once GDELT lands;
  USD/JPY pass.
