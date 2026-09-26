# Progress — Spec 04i (trail_stop_to_level formula fix + test-runner staleness)

- [x] Confirmed the formula bug against both independent production sources (fx-manager EJB commit
      `902ec7e4d`, spockfx-engine Spring commit `a1ed6b43b`) — `trail_stop_to_level` was `abs()`-ing
      the factor and hard-coding a loss-side subtraction; real formula is `entry + sign*diff` like
      `target_level`, factor used signed.
- [x] Fixed `rules/trail_stop.py::trail_stop_to_level` + docstrings.
- [x] Updated `tests/features/trail_stop.feature` with corrected expected values + edge-case
      scenarios (positive factor BUY/SELL, zero factor BUY/SELL, zero spread BUY/SELL).
- [x] Confirmed the fix is correct via direct `python -c` import (bypassing pytest entirely) —
      matches hand calculation exactly.
- [x] Plan step 1 (isolate `uv run` vs direct venv pytest) — executed: ruled out `uv run` itself.
- [x] Plan step 2 — superseded once root cause found.
- [x] Root cause found: stale/corrupted shared `.venv` across parallel worktrees. Fixed by
      `rm -rf algo-suite/.venv && uv sync`. Confirmed 7/7 passing locally after the fix, and
      independently by two reviewers (Codex + a separate Claude session) in disposable worktrees.
- [x] Note added to `algo-suite/docs/technical-debt.md` about the shared-venv failure mode.
- [ ] `make check` green workspace-wide — blocked only by a pre-existing, unrelated Ruff failure in
      `scripts/bigquery_*` (confirmed present on `main`, not touched by this PR). Focused gate for
      the changed files is green.
- [x] `lessons-learned.md` written, story moved to `docs/stories/done/`.
