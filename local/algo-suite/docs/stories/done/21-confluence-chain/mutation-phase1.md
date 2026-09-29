# Mutation testing — Phase 1 (hardener)

Manual behaviour-level mutation testing of story 21 Phase 1's production modules
(`git diff ef0111d..HEAD -- algo-backtest/src`): `chain/terminal.py`
(`AgreementTerminalDecision` and helpers), `chain/filters/f1_trend.py`
(`MomentumContextConfig`, `MomentumHistory`, `F1MomentumContextFilter`),
`chain/intensity_history.py` (whole module), `chain/filters/f4_news_context.py`
(`intensity_relative` hunks) and `chain/filters/f6_capital_mgmt.py`
(`exit_after_bars` hunks). `mutmut` is not installed in this workspace, so mutations
were injected manually, one at a time, in the real worktree (`/tmp/mba-impl-21`):
back up the one module, apply the mutation in place, run the covering step files,
restore from backup, confirm the file's `git status --porcelain` matches the
pre-mutation baseline before moving to the next mutation.

Covering tests run for every mutation (`-q -p no:cacheprovider -x`, cwd `algo-suite`):
`tests/steps/test_confluence_{agreement,momentum,history,relative_intensity,
capital_plan}.py`, `test_f1_trend.py`, `test_f4_news_context.py`,
`test_f6_capital_mgmt.py`, `test_filter_chain_mechanics.py` (397 scenarios total,
all green pre- and post-campaign).

## Result: 41/41 mutations KILLED (36 targeted + 5 negative controls)

No mutant survived after the fixes below (two survivors on first pass, both killed
by a new Gherkin scenario; details under "Survivors" below).

### `chain/terminal.py` — `AgreementTerminalDecision` (9 mutations)

| id | file:line | operator | original → mutated | result |
|----|-----------|----------|---------------------|--------|
| T1 | terminal.py:188 | count boundary | `len(votes) != 1` → `!= 2` | KILLED |
| T2 | terminal.py:191 | membership negation | `vote in _DIRECTIONAL` → `not in` | KILLED |
| T3 | terminal.py:207 | count boundary | `len(matches) == 1` → `>= 1` | KILLED |
| T4 | terminal.py:221 | comparison negation | `vote is not direction` → `is direction` | KILLED |
| T5 | terminal.py:180 | boolean operator | `is None or self._optional_blocks(...)` → `and` | KILLED |
| T6 | terminal.py:200 | membership negation | `not in required_runtime` → `in` | KILLED |
| T7 | terminal.py:149 | membership negation | `name in seen` → `not in seen` | KILLED |
| T8 | terminal.py:160 | membership negation | `name in _GATE_NAMES` → `not in` | KILLED |
| T9-NEG | terminal.py:53 | wrong constant (negative control) | `Recommendation.BUY: Decision.BUY` → `Decision.SELL` | KILLED |

### `chain/filters/f1_trend.py` — momentum context (9 mutations)

| id | file:line | operator | original → mutated | result |
|----|-----------|----------|---------------------|--------|
| F1-1 | f1_trend.py:159 | comparison boundary | `value > 0` → `>= 0` | KILLED |
| F1-2 | f1_trend.py:244 | comparison boundary | `< self.lookback_bars + 1` → `<=` | KILLED |
| F1-3 | f1_trend.py:246 | arithmetic (swap operands) | `close[-1]/close[0]` → `close[0]/close[-1]` | KILLED |
| F1-4 | f1_trend.py:251 | comparison boundary | `momentum_return > 0.0` → `>= 0.0` | KILLED |
| F1-5 | f1_trend.py:234 | comparison boundary | `close_time <= last` → `< last` | KILLED |
| F1-6 | f1_trend.py:228 | comparison boundary | `close <= 0.0` → `< 0.0` | KILLED |
| F1-7 | f1_trend.py:204 | off-by-one (L+1 vs L) | `maxlen=lookback_bars + 1` → `lookback_bars` | KILLED |
| F1-8 | f1_trend.py:271 | comparison negation | `!=` → `==` (history/config agreement) | KILLED |
| F1-9-NEG | f1_trend.py:251-255 | swapped branch (negative control) | BUY/SELL swapped in `_momentum_recommendation` | KILLED |

### `chain/intensity_history.py` — whole module (10 mutations)

| id | file:line | operator | original → mutated | result |
|----|-----------|----------|---------------------|--------|
| IH-1 | intensity_history.py:87 | sign flip | `cutoff - _WINDOW` → `cutoff + _WINDOW` | KILLED |
| IH-2 | intensity_history.py:325 | window_start inclusive/exclusive | `<=` → `<` | KILLED |
| IH-3 | intensity_history.py:327 | available_at cutoff boundary | `available_at < cutoff` → `<=` | KILLED |
| IH-4 | intensity_history.py:328 | WARMUP boundary | `collection_started_at > window_start` → `>=` | KILLED (see Survivors) |
| IH-5 | intensity_history.py:277 | closure boundary | `end <= start` → `end < start` | KILLED (see Survivors) |
| IH-6 | intensity_history.py:300 | ordering boundary | `closed <= last` → `< last` | KILLED |
| IH-7 | intensity_history.py:214 | quantile index formula | `(n - 1) * q` → `n * q` | KILLED |
| IH-8 | intensity_history.py:59 | wrong constant | `_Q_LOW = 0.10` → `0.20` | KILLED |
| IH-9 | intensity_history.py:371 | closure containment boundary | `bar_end <= end` → `< end` | KILLED |
| IH-10-NEG | intensity_history.py:212-213 | removed validation raise (negative control) | empty-sample guard removed | KILLED |

### `chain/filters/f4_news_context.py` — `intensity_relative` (7 mutations)

| id | file:line | operator | original → mutated | result |
|----|-----------|----------|---------------------|--------|
| F4-1 | f4_news_context.py:378 | comparison boundary | `intensity >= high` → `> high` | KILLED |
| F4-2 | f4_news_context.py:380 | comparison boundary | `intensity <= low` → `< low` | KILLED |
| F4-3 | f4_news_context.py:385 | sign flip | `sign == -1` → `sign == 1` | KILLED |
| F4-4 | f4_news_context.py:497 | comparison negation | `status != READY` → `== READY` | KILLED |
| F4-5 | f4_news_context.py:505 | comparison negation | `q_low == q_high` → `!=` | KILLED |
| F4-6 | f4_news_context.py:525 | comparison boundary | `available > timestamp` → `>= timestamp` | KILLED |
| F4-7-NEG | f4_news_context.py:518-522 | removed validation raise (negative control) | missing-availability-record guard removed | KILLED |

### `chain/filters/f6_capital_mgmt.py` — `exit_after_bars` (6 mutations)

| id | file:line | operator | original → mutated | result |
|----|-----------|----------|---------------------|--------|
| F6-1 | f6_capital_mgmt.py:400 | comparison boundary | `value <= 0` → `< 0` | KILLED |
| F6-2 | f6_capital_mgmt.py:395 | membership negation | `not in section` → `in section` | KILLED |
| F6-3 | f6_capital_mgmt.py:398 | comparison negation | `is None` → `is not None` | KILLED |
| F6-4 | f6_capital_mgmt.py:459 | comparison negation | `is None` → `is not None` (mapping delete) | KILLED |
| F6-5 | f6_capital_mgmt.py:573 | comparison negation | `is not None` → `is None` (plan write) | KILLED |
| F6-6-NEG | f6_capital_mgmt.py:400 | removed validation raise (negative control) | guard replaced with `if False:` | KILLED |

## Negative controls

Five negative controls (T9-NEG, F1-9-NEG, IH-10-NEG, F4-7-NEG, F6-6-NEG), one per
module, each an obvious behaviour-breaking mutation known to be covered by an
existing scenario (wrong constant, swapped branches, or a removed validation raise
on a path every scenario exercises). All five were KILLED, confirming the covering
step files actually detect faults in each module rather than passing vacuously.

## Survivors (first pass) and the scenarios that killed them

**IH-4** — `_compute`'s WARMUP boundary check (`collection_started_at >
window.window_start`) survived because every existing WARMUP/READY scenario used a
collection start either well before the window (`2016-01-01`, thirty-plus days
before `window_start`) or inside it (`2016-03-20`, after `window_start`); none
exercised the exact boundary `collection_started_at == window_start`. Added
"a collection declared exactly at window_start is READY, not WARMUP" to
`confluence_history.feature` (collection declared `2016-03-02T00:00:00Z`, equal to
April's `window_start`, full 30-day coverage) — asserts `status` is `"READY"`, not
`"WARMUP"`. Re-run: KILLED.

**IH-5** — `declare_closure`'s `end <= start` guard survived because the only
existing closure-rejection scenario used `end < start` (`2016-03-18` → `2016-03-17`);
none exercised `end == start` (a zero-length closure, which the docstring's
"`end` not after `start`" contract also rejects). Added "a documented market closure
whose end equals its start is refused, not treated as zero-length" to
`confluence_history.feature`. Re-run: KILLED.

Both additions are pure Gherkin/Examples additions to `confluence_history.feature`;
`test_confluence_history.py`'s existing step definitions cover both scenarios
unchanged (46 scenarios in that file, up from 44). No step code was written or
changed.

## Full campaign counts

- Mutations injected: 41 (36 targeted operators + 5 negative controls).
- KILLED: 41. SURVIVED (final): 0. TIMEOUT: 0. ERROR: 0.
- Per-module minimum met: terminal.py 9 (≥8), f1_trend.py 9 (≥8), intensity_history.py
  10 (≥8), f4_news_context.py 7 (≥6), f6_capital_mgmt.py 6 (≥6).
- Every mutation was applied to, then restored from, a single isolated copy of its
  one module in the shared worktree `/tmp/mba-impl-21`; `git status --porcelain`
  scoped to that file was confirmed clean after every restore, including the one
  case (before the first campaign run) where a concurrent lane's agent had written
  unrelated untracked feature files into the same worktree — left untouched, not
  depended on.

## Post-campaign gates (cwd `algo-suite`, all exit 0)

- `uv run pytest algo-backtest/tests -q -p no:cacheprovider` → 1799 passed,
  53 deselected (network/integration).
- `uv run ruff check algo-backtest` → all checks passed.
- `uv run mypy --strict algo-backtest` → no issues found in 64 source files.
  `.mypy_cache` removed after the run.
