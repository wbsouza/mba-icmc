# Story 19 phase 1 — mutation hardening report

Worktree `/tmp/mba-impl-19`, branch `feat/19-adaptive-retraining`, base SHA
`82d3908fd250a6ebb5f72f989599cd2f29bf059d` (unchanged by this pass — only test
feature files and this report were added). Method: manual behaviour-level
mutation (`mutmut` not used), one module at a time, one mutation at a time, in
place in this worktree — back up the file, apply the mutation, run the
covering step files, record KILLED/SURVIVED, restore from backup, confirm
`git status --porcelain` matches the session baseline before the next
mutation. This deviates from the isolated-scratch-worktree recipe in
`STAGES.md`'s Hardener section on explicit direction from the team lead for
this resumed session (in-worktree backup/restore, since the concurrent
specifier agent sharing this worktree never touches the mutated tracked
files, confirmed before starting).

Test command:
```
uv run pytest algo-backtest/tests/steps/test_retraining_ingestion.py \
  algo-backtest/tests/steps/test_retraining_schedule.py \
  algo-backtest/tests/steps/test_retraining_weights.py \
  algo-backtest/tests/steps/test_f7_family_weights.py \
  algo-backtest/tests/steps/test_f7_meta_learner.py -q -p no:cacheprovider -x
```

Scope: `algo_backtest/retraining/{ingestion,schedule,weights,utc}.py` and the
phase-1 diff of `chain/filters/f7_meta_learner.py` (the `family_weights` path,
`git diff ef0111d..HEAD -- .../f7_meta_learner.py`).

35 mutations injected: 9 in `ingestion.py` (incl. 1 negative control), 8 in
`schedule.py`, 8 in `weights.py`, 4 in `utc.py`, 6 in the F7 diff.
**31 KILLED, 4 initially SURVIVED — all 4 fixed with a new Gherkin scenario
and reconfirmed KILLED. 0 SURVIVED / 0 equivalent-mutant justifications
needed.**

## Negative control

| id | file:line | mutation | result |
|---|---|---|---|
| ING-NC | ingestion.py `_require_unique` | removed the duplicate-key `raise` | KILLED |

Confirms the harness actually detects an injected fault (the "batch that
repeats a key within itself" scenario).

## Full table

| id | file:line | operator | original -> mutated | result |
|---|---|---|---|---|
| ING-1 | ingestion.py:105 `_validate_row` | boundary `<=`→`<` | `if label_time <= row.available_at:` → `<` | KILLED* |
| ING-2 | ingestion.py:128 `_require_ordered` | boundary `<`→`<=` | `if later.available_at < earlier.available_at:` → `<=` | KILLED* |
| ING-3 | ingestion.py:138 `_require_declared` | `!=`→`==` | `declared_bars != len(rows)` → `==` | KILLED |
| ING-4 | ingestion.py:217 `consume` | swapped branch | `if not new_rows: return self` → `if new_rows: return self` | KILLED |
| ING-5 | ingestion.py:264 `_require_watermark_order` | boundary `<`→`<=` | `earliest < _parse(watermark)` → `<=` | KILLED* |
| ING-6 | ingestion.py:288 `maturity` | boundary `<=`→`<` | `label_time <= watermark` → `<` | KILLED |
| ING-7 | ingestion.py:306 `_keys_where` | boolean `and`→`or` | visibility/maturity predicate | KILLED |
| ING-8 | ingestion.py:92 `require_label_time` | removed validation (inverted) | `is None`→`is not None` | KILLED |
| SCH-1 | schedule.py:84 `_is_month_start` | `==`→`!=` | month-start equality | KILLED |
| SCH-2 | schedule.py:103 `monthly_epochs` | swapped branch (inverted `not`) | month-start validation guard | KILLED |
| SCH-3 | schedule.py:110 `monthly_epochs` | boundary `<`→`<=` | epoch-loop bound | KILLED |
| SCH-4 | schedule.py:120 `epoch_starting` | `==`→`!=` | epoch match | KILLED |
| SCH-5 | schedule.py:131 `_fitting_spans` | arithmetic `-`→`+` | embargo application | KILLED |
| SCH-6 | schedule.py:133 `_fitting_spans` | swapped ternary branch | rolling vs. expanding family start | KILLED |
| SCH-7 | schedule.py:179 `select_rows` | boundary `<`→`<=` | label_time-before-span-end | KILLED |
| SCH-8 | schedule.py:38 constant | wrong constant | `_COMBINER_DAYS` 30→31 days | KILLED |
| WGT-1 | weights.py:60 `_require_half_life` | boundary `<=`→`<` | half-life positivity | KILLED |
| WGT-2 | weights.py:88 `age_days` | boundary `>`→`>=` | future-availability guard | KILLED |
| WGT-3 | weights.py:110 `exponential_weights` | `==`→`!=` | zero-total-weight guard | KILLED |
| WGT-4 | weights.py:128 `_validated_total` | boundary `<`→`<=` | negative-weight guard | KILLED |
| WGT-5 | weights.py:134 `_validated_total` | `==`→`!=` | zero-mass guard | KILLED |
| WGT-6 | weights.py:152 `effective_n` | arithmetic `*`→`+` | denominator sum-of-squares | KILLED |
| WGT-7 | weights.py:171 `_row_violation` | boundary `<`→`<=` | row-count minimum | KILLED |
| WGT-8 | weights.py:165 `_class_counts` | wrong constant `+1`→`+2` | class tally increment (cleaner-flagged spot) | KILLED |
| UTC-1 | utc.py:15 `require_utc` | boolean flip | `tzinfo is None`→`is not None` | KILLED |
| UTC-2 | utc.py:15 `require_utc` | boolean op `or`→`and` | guard condition | KILLED |
| UTC-3 | utc.py:15 `require_utc` | `!=`→`==` | utcoffset check | KILLED |
| UTC-4 | utc.py:24 `iso_utc` | wrong constant | `"Z"`→`""` | KILLED |
| F7-1 | f7_meta_learner.py `_validated_family_weights` | `!=`→`==` | length check | KILLED |
| F7-2 | f7_meta_learner.py `_validated_family_weights` | removed validation (inverted) | `isfinite` guard | KILLED |
| F7-3 | f7_meta_learner.py `_validated_family_weights` | boundary `<`→`<=` | negative-weight guard | KILLED* |
| F7-4 | f7_meta_learner.py `_fit_family` | swapped branch | `sample_weights is None`→`is not None` | KILLED |
| F7-5 | f7_meta_learner.py `train_meta_learner` | wrong reference | `len(split.train)`→`len(split.validation)` | KILLED |
| F7-6 | f7_meta_learner.py `_fit_family` | wrong constant/type | `dtype=float`→`dtype=int` | KILLED |

`*` = initially SURVIVED, killed by a new scenario added in this pass (see below).

## Survivors fixed

All 4 were genuine boundary-equality gaps, not equivalent mutants — each
required a scenario the existing suite didn't cover:

1. **ING-1** (`label_time == available_at` must still be rejected, RWT-24):
   added the `label_time equal to availability` example row to the existing
   "invalid timestamp" Scenario Outline in `retraining_ingestion.feature`.
2. **ING-2** (rows sharing the same `available_at` are non-decreasing, not
   out of order, RWT-02): added `Rows sharing the same availability are
   non-decreasing, not out of order` to `retraining_ingestion.feature`.
3. **ING-5** (a batch whose earliest new row lands exactly on the current
   watermark must not regress it, RWT-23): added `A batch whose earliest new
   row lands exactly on the watermark does not regress it` to
   `retraining_ingestion.feature`.
4. **F7-3** (a `family_weights` value of exactly `0.0` is valid, not
   negative, RWT-07): added `A weight of exactly zero is accepted and the
   family is still fitted` (new Rule) to `f7_family_weights.feature`.

The cleaner-flagged `weights._class_counts` non-binary-label tally spot
(WGT-8, `+1`→`+2`) was already KILLED by the existing per-class-minimum
scenarios — no new scenario was needed there.

## Gate results after restore

- `git status --porcelain` after every mutation restore matched the session
  baseline exactly (the two intentionally-modified feature files plus the
  concurrent specifier agent's untracked files; the five mutated production
  files show zero diff).
- Full suite: `uv run pytest algo-backtest/tests -q -p no:cacheprovider` →
  1727 passed, 53 deselected.
- `uv run ruff check algo-backtest` → all checks passed.
- `uv run mypy --strict algo-backtest` → no issues, 68 source files
  (`.mypy_cache` removed after).
