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
- [x] Note added to `algo-suite/docs/technical-debt.md` about the shared-venv failure mode (TD-54).
- [x] `make check` green for `algo-backtest`'s own gate (ruff+mypy+pytest). Workspace-wide
      `make check`'s pre-existing, unrelated `scripts/bigquery_*` Ruff failure (52 errors,
      confirmed present on `main`) is registered as **TD-55** with a trigger, not left unchecked.
- [x] `lessons-learned.md` written, story moved to `docs/stories/done/`.
- [x] Follow-up (commit `94bee52`): `trail_stop_at_level` was also missing its `(factor+1)*spread`
      term (found via the same real-source citation used above) — fixed, feature file extended
      with BUY+SELL zero-spread/zero-factor scenarios (13/13 total now), mutation testing 18/18
      killed on the whole file. See spec.md §4.
