# Spec 04i — algo-backtest: `trail_stop_to_level` formula fix + test-runner staleness bug (lane of Spec 04)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` for full context; this
lane covers a defect found in already-ported money-management code, not new filter-chain scope.
**Depends on:** nothing — `rules/trail_stop.py` already exists and is already ported (Spec 04's
`00-PLAN`/`specs.md` §14.5 fx-manager port map). **Blocks:** trusting `trail_stop.py`'s test suite;
soft-blocks Spec 04j (money-management gaps) and Spec 04k (HAS trend-filter ablation), since both
build on the same `rules/` package and both would inherit an unverified test suite if run before
this lane closes.
**Order:** small, standalone — no parallel-lane conflicts; touches only `rules/trail_stop.py`,
`tests/features/trail_stop.feature`, `tests/steps/test_trail_stop.py`.
**Boundary:** those three files only.

## 1. The scenario — what happened

While auditing `algo_backtest`'s money-management port against the real fx-manager source
(`specs.md` §14, both the original JavaEE/EJB `StrategyMoneyManagementFacadeBean.java` and its
later Spring reimplementation in the sibling `spockfx-engine` project — see the
`fx-manager-borrow-analysis` memory note), `rules/trail_stop.py::trail_stop_to_level`'s own
docstring admitted it was written **without** the real fx-manager source available in this
checkout, and documented its sign-handling as "a deliberate reading of an ambiguous ±."

With the real source now read directly (both independent production implementations agree),
that reading turns out to be **wrong**: the shipped formula hard-coded a loss-side subtraction
and took `abs()` of the configured factor, which flips the sign of the `spread` term relative to
the legacy formula for every factor value, not just unusual ones. See §2 for the exact math.

The fix (formula + docstring + `.feature` scenarios with corrected expected values, plus three
new edge-case scenarios: positive factor, zero factor, zero spread) is already applied in this
worktree, uncommitted. What is **not yet resolved**: running `uv run pytest
tests/steps/test_trail_stop.py` after the fix produces failures whose "Obtained" values don't
match either the old formula or the new formula consistently — see §3.

## 2. The formula bug (root cause: confirmed, fixed)

Real fx-manager formula (both EJB and Spring versions, `StrategyMoneyManagementFacadeBean`'s
`resolveTrailStopToLevel`/`setTrailStopLevels`), same shape as `target_level`/`trail_stop_at_level`:

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
(`japaDragonStrategy04`'s `0.1`, locking in partial profit once a trail arms) — the old
`abs()` call silently discarded that sign, meaning any future config using a positive factor
would have gotten a *loss-side* destination instead of a *profit-side* one. This is exactly the
kind of trading-impactful silent-wrong-default this repo's fail-fast policy exists to prevent —
it just hadn't been caught yet because nothing calls `trail_stop_to_level` from production code
yet (only the test file does; F6/order_executor don't wire trailing stops in yet, Spec 04j).

**Fix applied (this worktree, uncommitted):**
- `rules/trail_stop.py::trail_stop_to_level` — removed `abs()`, unified with `target_level`'s
  `entry + sign*diff` shape, spread term now matches the confirmed source.
- Module + function docstrings rewritten to state the confirmed formula and cite both
  independent sources, instead of the old "documented interpretation of an ambiguous ±."
- `tests/features/trail_stop.feature` — corrected expected values for the two existing
  BUY/SELL scenarios (`1.0965→1.0969`, `1.1035→1.1031`), plus four new edge-case scenarios:
  positive factor (BUY + SELL), zero factor, and zero spread (isolates the R-multiple term).

## 3. The open problem — test-runner staleness

`uv run pytest tests/steps/test_trail_stop.py -v` reports 5 of 7 scenarios failing, but the
**"Obtained" values in the failure output don't match the current (fixed) formula, nor do they
consistently match the old (buggy) formula** — e.g. one run's failure for the BUY-positive-factor
scenario shows `Obtained: 1.0993000000000002`, which is the *SELL*-scenario's expected value, not
any value either formula version would produce for a BUY input.

## 4. The plan — what to do, and why

Use `superpowers:systematic-debugging`'s four-phase method rather than guessing further.
**Scope for this lane: execute steps 1–2 now** (cheap, isolate whether `uv run` itself is the
variable). **Step 3 is written here for the record but deliberately not implemented in this
lane** — only pursue it if 1–2 don't resolve the mystery, as a separate follow-up.

1. **Isolate the environment variable, not the code.** Run the exact same test file with
   `python -m pytest` inside the `mba-research/algo-suite` venv activated directly (no `uv run`
   wrapper), bypassing whatever `uv run` does on each invocation. If it passes clean, the bug is
   in `uv run`'s rebuild/resolution step; if it still fails identically, the bug is in the test
   code itself and `uv run` is a red herring.
2. **Find the actual installed location at failure time.** `uv run python -c
   "import algo_backtest, sys; print(algo_backtest.__file__, sys.path)"` immediately before and
   after a failing `uv run pytest` invocation, in the same shell session, to see whether the
   resolved path changes between the two commands.
3. **(Deferred — do not implement in this lane) If 1–2 don't resolve it: reproduce with a minimal
   two-scenario `.feature` file.** Strip `trail_stop.feature` down to just the
   BUY-positive-factor and SELL-positive-factor scenarios (the pair that showed swapped values) in
   a scratch file, run only those two, and see if the cross-talk still reproduces in isolation —
   narrows whether it's specific to those two scenarios' step text or a general pytest-bdd/fixture
   issue affecting the whole file. Left as a follow-up spec if needed, not executed here.
4. Whichever hypothesis confirms (from 1–2, or later from 3), fix the actual cause — not by
   adding a workaround (e.g. not by giving each scenario uniquely-worded steps to dodge a
   suspected parsing collision without understanding why it collides) — and re-run the full
   `trail_stop.feature` suite to confirm all 7 scenarios pass for the right reason (assert the
   printed "Obtained" values match hand calculations, not just that the exit code is green).
5. Once green and understood, check whether the same class of issue affects any other `.feature`
   file in this test suite that was run via `uv run pytest` during this same work session — if
   the root cause is environmental, it could be silently affecting other "already passing"
   suites' trustworthiness too, not just this one.

## Definition of done

- Steps 1–2 executed and their result documented here (which hypothesis they confirm or rule
  out), even if they don't fully resolve the mystery — that determines whether step 3 becomes a
  needed follow-up or not.
- `tests/steps/test_trail_stop.py`'s full 7 scenarios pass, with the "Obtained" values in a
  manual dry run matching hand-calculated expected values (not just asserted equal — actually
  eyeballed once to catch a second coincidental bug).
- If the root cause is environmental and could affect other suites, a one-line note added to
  `algo-suite/docs/technical-debt.md` flagging which other suites (if any) should be re-verified.
- `make check` green.
- Move this lane to `docs/stories/done/<YYYY-MM-DD>-trail-stop-formula-fix/` with a
  `lessons-learned.md` — this is exactly the kind of "spec didn't anticipate this" gap that
  belongs there (a formula fix that surfaced a tooling bug is not what the original Spec 04
  scoping anticipated).
