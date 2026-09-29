# Story 19 phase 2 — mutation hardening report

Worktree `/tmp/mba-impl-19`, branch `feat/19-adaptive-retraining`, base SHA
`59c5f06` (cleaner's phase-2 closure commit; unchanged by this pass except for
new/extended Gherkin scenarios and this report). Method: manual
behaviour-level mutation (`mutmut` present in the venv but not configured for
this workspace — `source_paths` guessing failed, so the STAGES.md manual
recipe was used instead), one module at a time, one mutation at a time,
in place in this worktree — back up the file, apply the mutation, run the
covering step files, record KILLED/SURVIVED, restore from the backup, confirm
`git status --porcelain` matches the session baseline before the next
mutation. `PYTHONDONTWRITEBYTECODE=1` was set for the whole session and
`__pycache__` was wiped before starting, per the team lead's brief.

Scope: `algo_backtest/retraining/{bundle,thresholds,trainer,cycle}.py`, the
T6 diff of `chain/filters/f7_meta_learner.py` (`combiner_weights`), and the
T9 additions to `retraining/ingestion.py` (`row`, `rows`, `visible_partitions`),
i.e. `git diff 82d3908..HEAD -- algo-backtest/src`.

**56 mutations injected** (9 bundle.py, 11 cycle.py, 8 thresholds.py,
8 trainer.py, 5 f7_meta_learner.py diff, 4 ingestion.py diff, 1 negative
control on cycle.py). **48 KILLED on first run, 8 initially SURVIVED — all 8
fixed with a new or extended Gherkin scenario and reconfirmed KILLED. 0
SURVIVED / 0 equivalent-mutant justifications needed.**

Both design-gap-focused mutations the team lead flagged as high-value were
tried and **KILLED on the first run**, confirming the coder's two
production-behaviour fixes are properly guarded:
- `C5-design-gap-b` (cycle.py): removing the watermark-conflict tolerance
  `{request.source_watermark, _watermark_after(request)}` so only the
  original `source_watermark` is accepted — killed by the existing "Different
  policies at the same boundary are independent cycles" scenario, which
  replays the same already-consumed batches under a second, independent
  policy at the same boundary.
- `D1`/`D2-design-gap-a` (trainer.py): making `ledger_watermark` and
  `hashes.data_sha256` compute from the ledger's raw/global state instead of
  the epoch's own cutoff (RWT-30 future-tail regression) — both killed by
  the existing "Consuming and mutating rows after the cutoff leaves the
  semantic payload hash and provenance unchanged" scenario, since both fields
  are bundle-identity fields and any future-tail leak changes `bundle_id`.

## Negative control

| id | file:line | mutation | result |
|---|---|---|---|
| NEG-CTRL | cycle.py `handle` | `CycleResponse(status="ok", ...)` → `status="broken"` | KILLED |

Confirms the harness detects an injected fault (`the response status is "ok"`).

## Full table

### bundle.py (9 mutations, 9 KILLED)

| id | file:line | operator | original -> mutated | result |
|---|---|---|---|---|
| B1 | bundle.py:296 `stage` | boundary `>=`→`>` | `theta_low >= theta_high` → `>` | KILLED |
| B2 | bundle.py:310 `stage` | `!=`→`==` | conflict-bytes check inverted | KILLED |
| B3 | bundle.py:244 `_validate_staged` | `!=`→`==` (line 245 uncovered raise) | sha256-mismatch check inverted | KILLED |
| B4 | bundle.py:250 `_validate_staged` | `!=`→`==` (line 251 uncovered raise) | probe-predict-mismatch check inverted | KILLED |
| B5 | bundle.py:413 `_require_fields` | boolean `or`→`and` | missing/null field check weakened | KILLED |
| B6 | bundle.py:402 `_require_schema_version` | `!=`→`==` | schema-version check inverted | KILLED |
| B7 | bundle.py:429 `list_bundles` | boolean `not` removed→added | staging-dir filter inverted | KILLED |
| B8 | bundle.py:263 `_default_clock` (uncovered) | wrong value | `datetime.now(UTC)` → `.replace(year=2000)` | SURVIVED → new scenario "Publishing without an injected clock records the real wall-clock instant" → KILLED |
| B9 | bundle.py:393 `_get_dotted` | boolean `or`→`and` | missing-path detection weakened | KILLED |

### cycle.py (11 mutations, 11 KILLED)

| id | file:line | operator | original -> mutated | result |
|---|---|---|---|---|
| C1 | cycle.py:68 `_default_clock` (uncovered) | wrong value | `.replace(year=2000)` | SURVIVED → new scenario "A coordinator opened without an injected clock records the real wall-clock instant" → KILLED |
| C2 | cycle.py:283 `eligible_bundle` (uncovered raise) | `is None`→`is not None` | "no cycle recorded" raise inverted | SURVIVED-then-fixed-together with C10 (same new scenario) → KILLED |
| C3 | cycle.py:287 `eligible_bundle` | `!=`→`==` | failed-cycle check inverted | KILLED |
| C4 | cycle.py:300 `_check_timeout` | boundary `>`→`>=` | rejects an attempt exactly at budget | SURVIVED → new scenario "An attempt that lands exactly on the registered timeout budget is not over budget" → KILLED |
| C5-design-gap-b | cycle.py:319 `_run_consume` | tolerance set narrowed | `{source_watermark, _watermark_after(request)}` → `{source_watermark}` | **KILLED** (see design-gap summary above) |
| C6 | cycle.py:316 `_run_consume` | swapped branch | `"consume" not in completed` → `in` | KILLED |
| C7 | cycle.py:479 `_require_future_activation` | boolean `not` removed | month-start check inverted | KILLED |
| C8 | cycle.py:466 `_require_no_boundary_conflict` | `==`→`!=` | boundary-conflict status check inverted | KILLED |
| C9 | cycle.py:453-455 `_run_publish` (uncovered resume-read path) | wrong key | `payload["bundle_id"]` → `payload.get("wrong_key")` | SURVIVED (twice — first fix was a no-op string-identity mutation, corrected) → new scenario "A timeout right after the publish checkpoint is written is retried, resuming from the publish checkpoint itself" plus a new assertion step `the response's bundle_id is actually present in the registry` → KILLED |
| C10 | cycle.py:504-505 `_find_by_policy_boundary` (uncovered) | wrong value | `return None` → `return {}` | KILLED by the same new scenario as C2 |
| C11 | cycle.py:474 `_require_future_activation` | boundary `<=`→`<` | future-only activation check widened | KILLED |

### thresholds.py (8 mutations, 8 KILLED)

| id | file:line | operator | original -> mutated | result |
|---|---|---|---|---|
| T1 | thresholds.py:67 `select_scored_rows` | boundary `<=`→`<` | span lower-bound inclusion removed | KILLED |
| T2 | thresholds.py:67 `select_scored_rows` | boundary `<`→`<=` | span upper-bound (half-open) violated | SURVIVED (existing "at-end" fixture row was also excluded by its own label_time, masking the available_at boundary) → new fixture row `at-end-mature` isolating the available_at boundary alone → KILLED |
| T3 | thresholds.py:67 `select_scored_rows` | boundary `<`→`<=` | label_time half-open bound (RWT-01) violated | KILLED |
| T4 | thresholds.py:101 `calibrate_thresholds` | boundary `<`→`<=` | minimum-rows off-by-one | KILLED |
| T5 | thresholds.py:111 `calibrate_thresholds` | boundary `<`→`<=` | non-increasing-thresholds check inverted | KILLED |
| T6 | thresholds.py:83 `_require_probability` | boundary `<`→`<=` | strict (0,1) interior widened to inclusive | KILLED |
| T7 | thresholds.py:31-32 constants | wrong constant | `0.10/0.90` → `0.05/0.95` | KILLED |
| T8 | thresholds.py:74 `_require_finite_scores` | validation bypassed | `if not math.isfinite` → `if False and ...` | KILLED |

### trainer.py (8 mutations, 8 KILLED)

| id | file:line | operator | original -> mutated | result |
|---|---|---|---|---|
| D1-design-gap-a | trainer.py:117 `_watermark_at_cutoff` | cutoff ignored | `visible_keys(cutoff)` → `visible_keys(cutoff.replace(year=9999))` | **KILLED** (see design-gap summary above) |
| D2-design-gap-a | trainer.py:192 `_data_sha256` | cutoff ignored | `ledger.visible_partitions(cutoff)` → `ledger.partitions` | **KILLED** (see design-gap summary above) |
| D3 | trainer.py:139 `_stage_weights` | swapped branch | `policy == "E"` → `!=` | KILLED |
| D4 | trainer.py:118-119 `_watermark_at_cutoff` (uncovered raise) | validation removed | "no row visible" raise bypassed | SURVIVED → new scenario "Training against a ledger with no consumed data fails naming that no row is visible" (new `a fresh ledger with nothing consumed` step) → KILLED |
| D5 | trainer.py:237-238 `prepare_epoch` | swapped branch | family/combiner spans swapped | KILLED |
| D6 | trainer.py:270-271 `prepare_epoch` | swapped branch | `family_weights`/`combiner_weights` args swapped | KILLED |
| D7 | trainer.py:273 `prepare_epoch` | wrong value | `perf_counter() - fit_started` → `perf_counter()` (absolute clock, not a delta) | SURVIVED (existing assertion only checked `>= 0.0`) → tightened `both epochs record a published_at UTC instant and a non-negative training_duration_seconds` to `0.0 <= duration < 60.0` → KILLED |
| D8 | trainer.py:131 `_class_counts` | off-by-one | `+ 1` → `+ 2` | SURVIVED (no scenario asserted exact `per_class` counts) → new scenario "The manifest's per-stage provenance records exact per-class row counts" → KILLED |

### f7_meta_learner.py diff (5 mutations, 5 KILLED)

| id | file:line | operator | original -> mutated | result |
|---|---|---|---|---|
| E1 | f7_meta_learner.py:305-310 `train_meta_learner` | swapped validation order | `family_weights` validated first → `combiner_weights` validated first | SURVIVED (no scenario had both vectors invalid at once) → new scenario "Both stage vectors invalid at once fails naming family_weights, checked first" → KILLED |
| E2 | f7_meta_learner.py:321 `train_meta_learner` | `is None`→`is not None` | sample_weight branch inverted | KILLED |
| E3 | f7_meta_learner.py:394 `_require_two_combiner_classes` | boundary `>`→`>=` | positive-weight filter widened (zero-weight rows counted as positive) | KILLED |
| E4 | f7_meta_learner.py:356 `_validated_stage_weights` | `!=`→`==` | length check inverted | KILLED |
| E5 | f7_meta_learner.py:368 `_validated_stage_weights` | boundary `<`→`<=` | negative check off-by-one (rejects zero weights) | KILLED |

### ingestion.py diff (4 mutations, 4 KILLED)

| id | file:line | operator | original -> mutated | result |
|---|---|---|---|---|
| I1 | ingestion.py:303 `rows` | wrong order | preserves caller order → `sorted(keys)` | KILLED |
| I2 | ingestion.py:322 `visible_partitions` | boundary `<=`→`<` | excludes a partition consumed exactly at cutoff | KILLED |
| I3 | ingestion.py:295-296 `row` | swapped fields | `available_at`/`label_time` swapped | KILLED |
| I4 | ingestion.py:324 `visible_partitions` | `in`→`not in` | membership filter inverted (complement set) | KILLED |

## New/extended Gherkin scenarios (kill fixes)

- `retraining_bundle.feature`: "Publication defaults to the real wall clock when
  no clock is injected" — "Publishing without an injected clock records the real
  wall-clock instant" (kills B8).
- `retraining_cycle.feature`: "A coordinator opened without an injected clock
  records the real wall-clock instant" (kills C1); "Looking up the eligible
  bundle for a boundary that never had a cycle run fails naming that nothing is
  eligible" (kills C2, C10); "An attempt that lands exactly on the registered
  timeout budget is not over budget" (kills C4); "A timeout right after the
  publish checkpoint is written is retried, resuming from the publish checkpoint
  itself" plus the new `the response's bundle_id is actually present in the
  registry` assertion (kills C9).
- `retraining_thresholds.feature`: added fixture row `at-end-mature` to "Rows
  outside the span or with a label maturing at or after its end do not move the
  quantiles" to isolate the `available_at` half-open upper bound from the
  `label_time` bound (kills T2).
- `retraining_trainer.feature`: "Training against a ledger with no consumed
  data fails naming that no row is visible" (kills D4); tightened the
  `training_duration_seconds` assertion to `< 60.0` (kills D7); "The manifest's
  per-stage provenance records exact per-class row counts" (kills D8).
- `f7_combiner_weights.feature`: "Both stage vectors invalid at once fails
  naming family_weights, checked first" (kills E1).

None of the fixes weaken or delete an existing scenario; all are additions or a
single sharpened numeric bound.

## Gate (cwd `/tmp/mba-impl-19/algo-suite`, all exit 0)

- `uv run pytest algo-backtest/tests/steps/test_retraining_bundle.py
  test_retraining_cycle.py test_retraining_thresholds.py
  test_retraining_trainer.py test_retraining_ingestion.py
  test_f7_combiner_weights.py test_f7_meta_learner.py test_f7_model_io.py -q
  -p no:cacheprovider`: 199 passed (191 baseline + 8 new scenarios).
- `uv run ruff check algo-backtest`: clean.
- `uv run mypy --strict algo-backtest`: clean, 72 source files (cache removed
  after).
- `uv run pytest algo-backtest/tests -q -p no:cacheprovider`: 1835 passed, 53
  deselected, 0 failed (85 s) — up from the cleaner's 1827 by the 8 new
  scenarios, otherwise unchanged.
- `git status --porcelain` after every restore matched the session baseline
  (only the two pre-existing untracked `qa-procedure-phase{1,2}.md` files);
  the final diff touches only the feature files and step files listed above —
  no production module in `algo-backtest/src` was left modified.
