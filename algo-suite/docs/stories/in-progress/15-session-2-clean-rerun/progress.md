# Story 15 — progress

- 2026-09-28 07:25 UTC — all session-1 jobs stopped (`stop-all-jobs.sh`), 19 job directories and the
  run root (832 MB) moved to `experiment-test-archives/pre-rename-session-1/`; viewer database archived.
- 07:40 UTC — job `2026-09-28-session-2` registered (README, 26 cells, 12 models) before any run.
- 07:40 UTC — stage 1 launched at `b72b3f1`: ten models trained (rows: H1 5642, H4 1235, same as
  session 1); the two news-only trainers failed because the trainer resolves `--strategies-dir` without
  the packaged fallback the run command has (`unknown strategy 'news-only'`). Fix: packaged configs
  snapshotted into the job's strategies directory; retrain via `run-train-fix.sh`.
- 07:42 UTC — PR #73 merged (`f438156`, comments/docs only); simulation stage runs at that revision.
- pending — stage 2 (26 cells), tables, `reproduction.md`, paired inference, viewer rebuild, Chapter 4.
