# Spec 04i — algo-backtest: `trail_stop_to_level` formula fix + test-runner staleness bug (lane of Spec 04)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` for full context; this
lane covers a defect found in already-ported money-management code, not new filter-chain scope.
**Depends on:** nothing — `rules/trail_stop.py` already exists and is already ported (Spec 04's
`00-PLAN`/`specs.md` §14.5 fx-manager port map). **Blocks:** trusting `trail_stop.py`'s test suite;
soft-blocks Spec 04j (money-management gaps) and Spec 04k (Double-Smoothed Heikin-Ashi trend-filter ablation), since both
build on the same `rules/` package and both would inherit an unverified test suite if run before
this lane closes.
**Order:** small, standalone — no parallel-lane conflicts; touches only `rules/trail_stop.py`,
`tests/features/trail_stop.feature`, `tests/steps/test_trail_stop.py`.
**Boundary:** those three files only.

## 1. The scenario — what happened

While auditing `algo_backtest`'s money-management port against the real fx-manager source
(`specs.md` §14, both the original JavaEE/EJB `StrategyMoneyManagementFacadeBean.java` and its
later Spring reimplementation in the author's later Heikin-Ashi trading manager — see the
`fx-manager-borrow-analysis` memory note), `rules/trail_stop.py::trail_stop_to_level`'s own
docstring admitted it was written **without** the real fx-manager source available in this
checkout, and documented its sign-handling as "a deliberate reading of an ambiguous ±."

With the real source now read directly (both independent production implementations agree),
that reading turns out to be **wrong**: the shipped formula hard-coded a loss-side subtraction
and took `abs()` of the configured factor, which flips the sign of the `spread` term relative to
the legacy formula for every factor value, not just unusual ones. See §2 for the exact math.

The fix (formula + docstring + `.feature` scenarios with corrected expected values, plus edge-case
scenarios: positive factor, zero factor, zero spread) is committed on `fix/trail-stop-to-level-formula`
(PR #34). **Status as of the PR review round (2026-09-26): resolved.** Two independent reviewers
(a Codex session and a separate Claude session, each in a disposable worktree/fresh `uv sync`) ran
the suite clean — 7/7 passed — directly contradicting this spec's own earlier claim that the suite
was failing. Root cause and fix are in §3.

## 2. The formula bug (root cause: confirmed, fixed)

Real fx-manager formula, cited precisely (not prose-only — a future reader can check these):

- `fxmanager-ejb/src/main/java/fxmanager/facade/StrategyMoneyManagementFacadeBean.java`,
  method `resolveTrailStopToLevel` (~lines 147–159), fx-manager repo
  (`ssh://git@forge.wiseprax.ai/algo-trading/fx-manager.git`), commit `902ec7e4d608ebc8c98fbdabe7d384b65f0fcba0`
  (last touching that file, 2021-03-21).
- the later Heikin-Ashi trading manager's money-management calculator, trail-stop level method
  (unpublished source, revision of 2025-02-24) — a later, independent Spring reimplementation by
  the same author; agrees with the EJB version on this formula.

Same shape as `target_level`/`trail_stop_at_level`:

```
diff  = |entry - SL| * factor + spread     # factor is a SIGNED config value, e.g. -0.66
sign  = +1 if BUY else -1                  # identical rule for all three formulas, no special-casing
result = entry + sign * diff
```

Shipped `trail_stop_to_level` before this fix:

```python
offset = distance * abs(trail_stop_to_level_factor) + spread
return entry - _profit_sign(direction) * offset
```

For a BUY with `factor = -0.66`: real formula gives `entry + (-0.66*dist + spread)`; the old
code gave `entry - (0.66*dist + spread)`. Same R-multiple term, **opposite sign on the spread
term** — a real, verifiable numerical error, not a style difference. Confirmed by hand and by a
direct `uv run python -c "from algo_backtest.rules.trail_stop import trail_stop_to_level, ...`
import, independent of pytest: with the fix applied, the direct import returns `1.0969` for the
BUY/entry=1.1000/SL=1.0950/spread=0.0002/factor=-0.66 case, matching the corrected hand
calculation exactly.

**Why it matters:** `trail_stop_to_level_factor` can be positive in real deployed configs
(a legacy Heikin-Ashi template's `0.1`, locking in partial profit once a trail arms) — the old
`abs()` call silently discarded that sign, meaning any future config using a positive factor
would have gotten a *loss-side* destination instead of a *profit-side* one. This is exactly the
kind of trading-impactful silent-wrong-default this repo's fail-fast policy exists to prevent —
it just hadn't been caught yet because nothing calls `trail_stop_to_level` from production code
yet (only the test file does; F6/order_executor don't wire trailing stops in yet, Spec 04j).

**Fix applied (committed `ec65548`; extended by `94bee52` — see §4):**
- `rules/trail_stop.py::trail_stop_to_level` — removed `abs()`, unified with `target_level`'s
  `entry + sign*diff` shape, spread term now matches the confirmed source.
- Module + function docstrings rewritten to state the confirmed formula and cite both
  independent sources, instead of the old "documented interpretation of an ambiguous ±."
- `tests/features/trail_stop.feature` — corrected expected values for the two existing
  BUY/SELL scenarios (`1.0965→1.0969`, `1.1035→1.1031`), plus four new edge-case scenarios:
  positive factor (BUY + SELL), zero factor, and zero spread (isolates the R-multiple term).

## 3. The test-runner staleness bug — root cause found, resolved

Locally (this author's machine), `uv run pytest tests/steps/test_trail_stop.py -v` reported 5 of 7
scenarios failing, with "Obtained" values that matched neither the old nor the new formula
consistently — e.g. a BUY scenario's result showing the *SELL* scenario's expected value. Plan
steps 1–2 (below) ruled out `uv run` itself as the cause (bypassing it entirely, calling the
venv's `pytest` binary directly, reproduced the identical failure). That narrowed it to the
environment, not the test code — confirmed by two independent reviewers (a Codex session and a
separate Claude session) each running the identical suite clean, 7/7 passed, in a disposable
worktree with a fresh `uv sync`.

**Root cause: a stale/corrupted long-lived shared `.venv`** at `algo-suite/.venv`, used across
several parallel story worktrees on this machine. `rm -rf algo-suite/.venv && uv sync` in the
original worktree fixed it completely — reran locally after the rebuild, 7/7 passed in 0.06s (down
from ~20–35s of `uv run`'s rebuild noise on every prior invocation, itself a symptom of something
being wrong with that venv's editable-install state). Exact mechanism not fully autopsied (the
venv was already deleted before writing this up), but the shared-venv-across-worktrees usage
pattern is the identified cause, not a pytest-bdd defect and not this formula fix.

1. **Isolate the environment variable, not the code — done.** Ran the venv's `pytest` binary
   directly, bypassing `uv run`. Same failure reproduced → ruled out `uv run`'s rebuild/resolution
   step as the cause; something in the venv itself, not the wrapper.
2. **Find the actual installed location at failure time — superseded** by step 1's result once the
   fix (`rm -rf .venv && uv sync`) was tried and confirmed working; no further diagnosis needed.
3. **(Not needed — root cause found without it)** the minimal two-scenario pytest-bdd repro was
   never required once the shared-venv hypothesis was tested and confirmed.

**Action for anyone hitting this again on a worktree sharing a long-lived `.venv`:** `rm -rf
algo-suite/.venv && uv sync` before chasing a pytest-bdd-specific hypothesis.

## 4. Follow-up (2026-09-26, commit `94bee52`): `trail_stop_at_level`'s own spread-term gap

While validating this fix's citations against the real source directly (rather than trusting the
prose summary), the same method (the later trading manager's trail-stop level computation)
showed `trail_stop_at_level` — untouched by the original fix, pre-existing before this PR — is
**also missing its `(factor + 1) * spread` term entirely**, unlike `target_level` and (now)
`trail_stop_to_level`. Since only `tests/steps/test_trail_stop.py` calls this function (no
production caller yet — same as `trail_stop_to_level` before Spec 04j wires it in), this was safe
to fix directly rather than deferring as separate debt:

- `rules/trail_stop.py::trail_stop_at_level` — added a `spread` parameter; formula is now
  `entry + sign*(distance*factor + (factor+1)*spread)`, matching `target_level`'s shape and the
  confirmed Java source exactly.
- `tests/features/trail_stop.feature` — the two existing composite scenarios' arm-level values
  changed (spread was silently dropped before: BUY `1.1025→1.1028`, SELL `1.0975→1.0972`); added
  BUY+SELL zero-spread/zero-factor edge scenarios mirroring `trail_stop_to_level`'s own coverage.
- `tests/steps/test_trail_stop.py` — passes `ts_ctx.spread` through to the new parameter.

Verified: **13/13 BDD scenarios pass** (up from 9 after the SELL-mirror additions in §2/§3's
close-out), `ruff`/`mypy` clean, **mutation testing 18/18 mutants killed (100%)** on the whole
`trail_stop.py` file (not just the originally-touched function).

## Definition of done

- [x] Root cause found and documented: stale/corrupted shared `.venv` across parallel worktrees,
  not a pytest-bdd defect — fixed by `rm -rf .venv && uv sync`.
- [x] `tests/steps/test_trail_stop.py`'s full suite passes (13/13 as of `94bee52`; was 7/7 at the
  original fix, 9/9 after the SELL-mirror close-out), "Obtained" values hand-verified against the
  confirmed formula.
- [x] One-line note added to `algo-suite/docs/technical-debt.md` about the shared-venv failure
  mode (TD-54), since it could silently affect any other suite's trustworthiness on this machine.
- [x] `make check` green for the focused/owned scope (`algo-backtest`'s own gate: ruff+mypy+pytest
  all pass). Workspace-wide `make check`'s pre-existing, unrelated `scripts/bigquery_*` Ruff
  failure (52 errors, confirmed present on `main`, outside any workspace member's `src/`) is now
  registered as **TD-55** with an explicit trigger, rather than left as a bare unchecked box.
- [x] Move this lane to `docs/stories/done/<YYYY-MM-DD>-trail-stop-formula-fix/` with a
  `lessons-learned.md`.
