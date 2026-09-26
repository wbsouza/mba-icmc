# Progress — Spec 04i (trail_stop_to_level formula fix + test-runner staleness)

- [x] Confirmed the formula bug against both independent production sources (fx-manager EJB,
      spockfx-engine Spring) — `trail_stop_to_level` was `abs()`-ing the factor and hard-coding a
      loss-side subtraction; real formula is `entry + sign*diff` like `target_level`, factor used
      signed.
- [x] Fixed `rules/trail_stop.py::trail_stop_to_level` + docstrings.
- [x] Updated `tests/features/trail_stop.feature` with corrected expected values + 4 new edge-case
      scenarios (positive factor BUY/SELL, zero factor, zero spread).
- [x] Confirmed the fix is correct via direct `python -c` import (bypassing pytest entirely) —
      matches hand calculation exactly.
- [x] Plan step 1 (isolate `uv run` vs direct venv pytest) — **executed**: ran the venv's `pytest`
      binary directly, bypassing `uv run` entirely. Same 5/7 failure pattern reproduced —
      **rules out** the `uv run` rebuild/resolution hypothesis (§3, hypothesis a) and the
      competing-venv hypothesis (b). The bug is in the test code/pytest-bdd itself, not the
      `uv run` wrapper.
- [x] Plan step 2 (installed-location check before/after) — superseded by step 1's result; not
      needed now that (a)/(b) are ruled out.
- [ ] Plan step 3 (minimal two-scenario repro for pytest-bdd cross-talk, hypothesis c) — next
      action, not yet started. The failure evidence (a SELL scenario's `ts_ctx.result` coming out
      as the BUY scenario's expected value while `ts_ctx.direction`/`entry`/`stop_loss` are
      correctly SELL) points at the `when` step computing with the wrong `direction`/`factor`
      somehow, or at `pytest.approx`/fixture rebinding across scenarios sharing near-identical
      step text — needs the minimal-repro isolation to pin down which. Deliberately deferred per
      the user's explicit scope call for this lane.
- [ ] `tests/steps/test_trail_stop.py` full suite green with hand-verified "Obtained" values.
- [ ] `make check` green.
- [ ] `lessons-learned.md` written, story moved to `docs/stories/done/`.
