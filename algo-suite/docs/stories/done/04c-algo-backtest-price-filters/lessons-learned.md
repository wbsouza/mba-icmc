# Lessons learned — Spec 04c: algo-backtest price-derived filters F1-F3

**mutmut's cache is keyed on source-file hashes, not test-file hashes — a
test-only change silently reuses stale verdicts.** After strengthening the
`Then` steps to assert `filter_name`/`reason`/boundary conditions (no change
to `f1_trend.py`/`f2_indicator.py`/`f3_pattern.py` themselves), re-running
`uv run mutmut run` reported the exact same 48 survivors, at 0.00
mutations/second — it never actually re-executed the mutation-testing phase,
it replayed the previous run's cached pass/fail verdicts from the git-ignored
`mutants/` directory, because the mutated functions' source hashes hadn't
changed. Confirmed by inspecting `mutmut`'s own `state.py`
(`old_function_hashes` vs. `current_function_hashes`) and its own CLI hint
("If the changes affect your tests, delete the `mutants/` directory...").
Deleting `mutants/` and rerunning dropped survivors from 48 to 17, then to 13,
matching each round of test strengthening. Lesson: after editing tests
*without* touching the mutated source, `rm -rf mutants/` before re-running,
or the mutation report silently lies about whether the new assertions did
anything.

**Boundary-value survivors are the majority of the real (non-canary) kill
work, same shape as 04b's `confidence` lesson but now on oscillator
thresholds.** `_bullish`/`_bearish` in `f2_indicator.py` compare against
`50.0`/`0.0`; mutants shifting `>` to `>=` or the constant by ±1 only show up
against boundary inputs (`rsi=50.0` exactly, `macd_hist=0.0` exactly, `rsi`
one unit past the threshold). The original four scenarios (two directional,
one disagreement, two ABSTAIN) all used comfortably-clear-of-boundary values
and left 7 of these mutants alive; killed by adding 7 boundary-exact/near
scenarios under a new Rule. `filter_name`/`reason`-emptiness mutants (`None`,
case-changed, `XX`-wrapped) recurred across all three filters for the same
reason as 04b: the original assertions checked `recommendation`/`veto` but
never `filter_name` or that `reason` was non-empty.

**A short-circuit guard can make its own downstream comparison operator
unkillable — recognize that before writing more tests to chase it.**
`f1_trend.py`'s `_conflicts()` is `trend_direction != 0.0 and
higher_tf_trend_direction != 0.0 and (trend_direction > 0.0) !=
(higher_tf_trend_direction > 0.0)`; two mutmut survivors flip the third
clause's `>` to `>=` on each variable. Because the preceding `!= 0.0` guards
on those exact same variables already exclude the zero case those `>=`
mutants would newly capture, `>` and `>=` are behaviorally identical for
every input that reaches the third clause — no test input can distinguish
them. Confirmed equivalent rather than spending more scenarios trying to kill
it; logged to `technical-debt.md` (TD-39) alongside the message-text canaries
(same accepted-debt-class handling as TD-34/TD-36) instead.

**The feature-key contract is this story's real design decision, not an
implementation detail.** No upstream perception layer exists yet, so F1-F3
each invent their own `state.features` keys documented in their module
docstrings: F1 reads `trend_direction`/`trend_strength`/
`higher_tf_trend_direction` (all required, fail-fast on missing — no ABSTAIN
scenario was requested for F1, so a missing key is treated as a hard
contract violation rather than a no-op); F2 reads `rsi`/`macd_hist` (both
optional/nullable — a missing or `None` reading is the defined "no-information
bar" ABSTAIN case, never a raise); F3 reads `candlestick_pattern` (optional —
absent/`None` is ABSTAIN, but a *present, unrecognized* value raises, since
that signals the upstream detector emitted something outside this filter's
known vocabulary rather than "no pattern this bar"). Three different
missing-value policies (hard-fail, ABSTAIN-on-None, ABSTAIN-vs-raise
depending on presence) for three filters reading the same `dict[str,
object]` — deliberate per-filter, not an inconsistency: F1 has no ABSTAIN
requirement in the spec, F2 and F3 do. Whoever wires the real LEAN/TA-Lib
perception layer (04a/04h) needs to either match these exact keys/semantics
or update these filters' docstrings and tests in the same change.
