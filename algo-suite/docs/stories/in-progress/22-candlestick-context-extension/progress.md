# Story 22 — progress

- [x] 2026-09-28 — brief, webinar notes and the tlc-spec-driven plan drafted (Codex, inside story 13).
- [x] 2026-09-28 — split into this story when story 13 closed; .specs paths updated.
- [x] 2026-09-28 — scoped planning amendment: deterministic rules active; earlier Laya proposal explicitly superseded and DEFERRED.
- [ ] Review the amended 19-task plan and shared coordinator handoff gates.
- [ ] Execution: after explicit authorization only; all implementation tasks remain pending.

## Canonical scope and history

[Canonical tasks](../../../../../.specs/features/candlestick-context/tasks.md) own
the implementation checklist: 19 active IDs T1–T16 and T22–T24; T17–T21 remain
in the DEFERRED history table. Active requirements are CND-01–19 and CND-25/26
(21); CND-20–24 remain DEFERRED. CND-18/19 retain reviewed recognition data and
leakage-free rules evaluation independently of learned models.

Phase 1: T1–T6 (6). Phase 2: T7–T14 (8). Phase 3: T15–T16 plus T22–T24 (5):
dataset, protocol, runner, evidence and monograph. T22 depends on T16; no active
task depends on deferred work. No optional Laya gate remains active.

## Parallel handoff

Follow the [coordinator-owned Stories 19/21/22 plan](../../parallel-19-21-22.md).
Main owns coordination and Story 19; a separate agent owns Story 21; lane C owns
rules/perception/F3. Story 19's tested F7 fitting changes precede Story 22 T9's
serialized encoder integration. Normal F7 model provenance remains in scope.
Coordinator integration leases cover training, signal contracts/production,
decision recording, schema/ingestion and viewer. One editor owns monograph changes.

Before implementation, record the shared-plan launch contracts and actual owner,
branch/worktree/base SHA. Before Phase 2, obtain shared-file leases and the F7
handoff. After T14, obtain integrated legacy/parity/protection/audit acceptance.
Before T22, freeze T16's rules-only protocol; before T24, hand verified evidence to
the single editor. No implementation worker or worktree was created in this turn.

Main owns cross-story link checks and final planning validation. This lane runs
the canonical spec/tasks structural validators only; no code tests or studies.
Publication is blocked by read-only `.git` and unavailable Forgejo approval;
no new branch, commit, push or PR is claimed. Preserve the existing directory moves.

## Working tree and ownership

- Agent role: Claude coder, lane C (Story 22), Phase 1 T1–T6 only.
- Worktree `/tmp/mba-impl-22`, branch `feat/22-candlestick-rules`, base SHA `ef0111d`
  (`docs: plan parallel stories 19, 21 and 22 without Laya`), branched from `main`.
- Specifier-authored feature files (untracked at hand-off, committed with their task):
  `candle_contract.feature` (T2), `candle_catalog.feature` (T3), `candle_context.feature`
  (T4), `candle_sequence.feature` (T5), `f3_policy_modes.feature` (T6);
  `qa-procedure-phase1.md` in this directory.
- Test baseline recorded before T1 (cwd `algo-suite`, exit 0):
  `uv run pytest algo-backtest/tests -q -p no:cacheprovider --collect-only` →
  1598/1651 collected (53 deselected);
  `uv run pytest algo-backtest/tests/steps/test_candlestick_detector.py algo-backtest/tests/steps/test_f3_pattern.py -q -p no:cacheprovider`
  → 110 passed.
- Environment repair (worktree-local, not a repo change): the worktree `.venv` held a
  truncated `scipy` 1.17.1 (6 files under `scipy/sparse`), which broke 18 collections
  with `module 'scipy.sparse' has no attribute 'spmatrix'`;
  `uv sync --all-packages --reinstall-package scipy` restored it (same pinned version).

## Phase checklist (mirrors tasks.md; ticked in the delivering commit)

- [x] T1 Review and freeze the source-rule ledger
- [x] T2 Define immutable pattern evidence and configuration
- [x] T3 Implement the expanded geometry catalog
- [x] T4 Implement causal context evaluation
- [x] T5 Implement next-bar confirmation state machine
- [x] T6 Implement explicit F3 policy modes
- [ ] T7 Integrate shared closed-bar evidence into native signals
- [ ] T8 Fingerprint the complete signal contract
- [ ] T9 Version the F7 pattern feature encoder
- [ ] T10 Integrate evidence into training rows
- [ ] T11 Serialize decision evidence
- [ ] T12 Ingest old and new evidence in results database
- [ ] T13 Extend viewer catalog metadata
- [ ] T14 Render separate pattern and decision evidence
- [ ] T15 Validate reviewed rules-recognition data and split boundaries
- [ ] T16 Register bounded recognition and trading protocol
- [ ] T22 Record complete experiment attempts and parameters
- [ ] T23 Publish comparison evidence with parameters beside results
- [ ] T24 Update the monograph from verified evidence

T17–T21 are DEFERRED and never implemented.

## Task log

### 2026-09-28 — T1 review and freeze the source-rule ledger (CND-01)

- Artifact: `candlestick-rule-ledger.md` (this directory). All four sources readable;
  SHA-256 verified for the book, both presentation copies and the transcript.
  Page offset verified per cited page: PDF = printed + 6 in the major-signals chapter,
  PDF = printed + 4 in the high-profit-patterns chapter.
- Adopted every formula pinned by the specifier (feature description blocks and
  `qa-procedure-phase1.md`) unchanged; refined two citations only (bullish harami
  criteria p.76/82; hanging-man OCR line is criteria 1 on p.61/67). No disputed
  scenario.
- TA-Lib relation column verified empirically (`talib` 0.8.1) on every ledger example
  after 20 context candles; scores recorded in the ledger.
- Docs gate (cwd repo root): `git diff --check` exit 0;
  `python3 ~/.claude/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/candlestick-context/spec.md --strict`
  exit 0 (0 errors, 0 warnings);
  `... validate_tasks.py .specs/features/candlestick-context/tasks.md --strict` exit 0.
- Status: tasks.md T1 boxes ticked; spec.md CND-01 → `Implemented (T1)`.
- Commit: `05bbdad` `docs(candles): review and freeze the source-rule ledger`; pushed to
  `origin/feat/22-candlestick-rules` (new branch).

### 2026-09-28 — T2 immutable pattern evidence and configuration (CND-02, CND-03)

- Files: `algo-backtest/src/algo_backtest/perception/candle_contract.py` (new:
  `CATALOG`/`ADMITTED_RULES`, `ContextConfig`, `SequenceConfig`, `CandleConfig`,
  `PatternHit`, `IndicatorValue`, `StochasticEvidence`, `LevelEvidence`,
  `ContextEvidence`, `SequenceEvidence`, `CandleEvidence`, `ClosedBar`, `validate_bar`,
  `CandleHistory`), `algo-backtest/tests/features/candle_contract.feature` (specifier),
  `algo-backtest/tests/steps/test_candle_contract.py` (new), `tools/perception_quality.py`
  (one registration line: `"candle_contract": set()`).
- Assumptions: default `timeframe_minutes` is 60 (the feature only fixes the divisor rule);
  `CandleEvidence` carries its own `max_history` bound so `history_count` is validated
  without a configuration; the evidence sub-types for context and sequence live in the
  contract so T4/T5 evaluators import types from it (no reverse import); a READY hit must
  carry exactly the catalog polarity (stricter than "not contradicting"); `last_gap`
  counts missing bars on the continuous grid (calendar policy is a T5 input).
- Gate (cwd `algo-suite`):
  `uv run pytest algo-backtest/tests/steps/test_candle_contract.py -q -p no:cacheprovider`
  → exit 0, 112 passed (18 templates);
  `uv run pytest algo-backtest/tests/steps/test_candlestick_detector.py algo-backtest/tests/steps/test_f3_pattern.py -q -p no:cacheprovider`
  → exit 0, 110 passed (unchanged);
  `uv run ruff check algo-backtest tools` → exit 0;
  `uv run ruff format --check` on the three touched files → the two new files formatted;
  `tools/perception_quality.py` was already non-formatted before this change (its diff is one
  added line) and 66 pre-existing files under `algo-backtest` fail the workspace-wide format
  check, none touched here (pre-existing, fixed on the integration branch);
  `uv run mypy --strict algo-backtest tools/perception_quality.py` → exit 0 (65 files);
  `make check-perception-architecture` → PASS.
- QA REPL checks 2.2–2.4 reproduced: `1 256 legacy 19`; `max_history=257` → ValueError
  naming `max_history` and 256; `max_history=199` → ValueError naming the 200-bar SMA lookback.
- Adequacy review (Check A, evidence-or-zero; file `tests/steps/test_candle_contract.py`):
  CND-02 stable ordered hits → `assert_evidence_outcome` :305 via `_assert_outcome` :88
  (`mention in str(error)` for "order"/"doji"/"doji_star"); CND-03 rejection before state
  advances → `assert_rejected` :385 (`fragment in message`, `"repair" in message`) +
  `assert_untouched_then_accepts` :403 (`history.bars == before`, count unchanged, next bar
  accepted) + `assert_unchanged` :460 / `assert_evicts_oldest` :466; bounds/unknown ids/
  policy/timeframe/version → `assert_config_outcome` :229; hit polarity/version/status →
  `assert_hit_outcome` :255; immutability → `assert_frozen` :173; defaults →
  `assert_defaults` :112, `assert_enabled_rules` :123, `assert_context_defaults` :139;
  gap flag → `assert_gap` :427; eviction → `assert_retained` :454. Check B: every outcome
  asserts a value or a message fragment, no call-count or no-throw-only assertions.
  Check C: every scenario maps to a contract line of the feature description
  (CND-02/03) or a tasks.md T2 listed case; none removed. Check D: Gherkin-first,
  `scenarios("../features/candle_contract.feature")`, docstrings on every step.
- Status: tasks.md T2 boxes ticked; spec.md CND-02, CND-03 → `Implemented (T2)`.
- Commit: `071d1d0` `feat(candles): define immutable pattern evidence and configuration`; pushed.

### 2026-09-28 — T3 expanded geometry catalog (CND-01, CND-02, CND-04, CND-05, CND-09)

- Files: `perception/candle_catalog.py` (new: ledger formulas for the 13 new rules, TA-Lib
  legacy scores exactly as `candlestick.py`, `evaluate_catalog`, `legacy_label`,
  streaming `CandleCatalog`), `tests/features/candle_catalog.feature` (specifier, two
  fixture amendments below), `tests/steps/test_candle_catalog.py` (new),
  `tools/perception_quality.py` (registration: `candle_catalog` may import
  `candle_contract` and `candlestick`), `perception/candle_contract.py` (the close-time
  validator split into `_aligned_utc_close_time` + `_strictly_after` because the
  perception CRAP gate counts boolean operands and reported CC 10 > 8; behaviour and
  messages unchanged, 112 contract examples still pass).
- Amended scenarios (feature file, reason recorded; specifier notified):
  1. "Hanging man and inverted hammer": the four inverted-hammer rows used
     `(960, 1070, 958, 955)`, an impossible bar (low 958 > close 955) that CND-03
     validation rejects; low changed to 952 (body 5, upper 110, lower 3 <= 11.8), outcomes
     unchanged. Ledger example corrected the same way.
  2. "Opposing hits on one bar": the dip bar `(10, 10.6, 9.8, 9.0)` had close 9.0 below
     low 9.8, and 12 bars left the two stars WARMUP (so "exactly hammer and hanging_man"
     could not hold). Now 8 float context candles, dip `(10, 10.6, 8.9, 9.0)`, 3 context
     candles, final `(9.55, 9.62, 8.5, 9.6)`; by the specifier's own doji formula the final
     bar is also `doji` and `doji_dragonfly` (body 0.05 <= 0.112, upper 0.02 <= 0.112), so
     the expected hits are doji, doji_dragonfly, hammer (+1), hanging_man (-1), status
     READY; TA-Lib hammer 100 and legacy label "hammer" kept. QA step 3.4 needs the same
     change (specifier's file).
- Assumptions: legacy TA-Lib scores are computed on the retained (<= 256-bar) history,
  as the legacy `CandleDetector` computes on its 64-bar buffer; frozen equality is proven
  on the legacy corpora at every prefix. `CandleCatalog(config, pair)` produces
  `CandleEvidence` with context/confirmation None (T4/T5 produce their own evidence; T7
  assembles). Legacy fixtures are duplicated verbatim from `test_candlestick_detector.py`
  because pytest runs with `--import-mode=importlib` (step modules are not importable).
- Gate (cwd `algo-suite`, all exit 0):
  `uv run pytest algo-backtest/tests/steps/test_candle_catalog.py -q -p no:cacheprovider`
  → 106 passed (17 templates);
  `uv run pytest algo-backtest/tests/steps/test_candle_contract.py algo-backtest/tests/steps/test_candle_catalog.py -q -p no:cacheprovider`
  → 218 passed;
  `uv run pytest algo-backtest/tests/steps/test_candlestick_detector.py algo-backtest/tests/steps/test_f3_pattern.py -q -p no:cacheprovider`
  → 110 passed; `uv run ruff check algo-backtest tools` → clean; new files formatted;
  `uv run mypy --strict algo-backtest tools/perception_quality.py` → 66 files clean;
  `make check-perception-architecture` → PASS.
  Pure gate host-side line (the `make check-perception` pytest --cov line plus the two new
  step files): 501 passed, 9 deselected; `candle_catalog.py` 99% before removing one
  impossible branch (now no unreachable line), `candle_contract.py` 90% (uncovered:
  `IndicatorValue`, `LevelEvidence`, `ContextEvidence`, `SequenceEvidence` validators and
  the context/confirmation type checks, exercised by T4–T6; re-checked at phase end).
  `uv run python tools/perception_quality.py --coverage build/perception-host-coverage.json`
  (informative, without the native merge): every `candle_catalog.py` function CRAP <= 8;
  the only FAIL was `candle_contract.py:_validated_close_time` CC 10, fixed by the split
  above. Docker lines of `make check-perception` (native LEAN assertions, feature parity,
  closed-signal parity, mutations): BLOCKED in this lane until the phase-end attempt
  (recorded there).
- Adequacy review (file `tests/steps/test_candle_catalog.py`): CND-01 ledger rules with
  boundary examples → `assert_neutral_hits` :317 / `assert_ready_hits` :324 (`ready ids ==
  expected`, polarity == catalog polarity) over every doji/spinning/two-bar/umbrella row;
  CND-02 every hit preserved in stable order → `assert_hits_table` :376 (`[(id, polarity,
  status)] == table`), `assert_ready_ids` :408 + `assert_order_independent` :418
  (`evidence == evidence` across enabled_rules orders); CND-04 WARMUP per rule →
  `assert_warmup_ids` :383, `assert_hit_status` :363, `assert_status` :331; CND-05 prefix
  invariance → `assert_prefix_invariance` :425 (`first == second`), `assert_prefix_final`
  :433; CND-09 frozen legacy equality → `assert_corpora_equal` :445 (`labels == oracle` on
  every prefix of every corpus), `assert_corpora_vocabulary` :451, `assert_label` :439,
  `assert_legacy_label` :396 / `assert_legacy_label_none` :402; TA-Lib independence →
  `assert_native` :357, `assert_native_score` :370, `assert_engulfing_score` :337,
  `assert_native_hammer` :390; bounded history → `assert_bounded` :457. Check B: every
  assertion compares ids/polarities/statuses/labels, none is call-count or no-throw only.
  Check C: every scenario maps to a ledger rule row, a tasks.md T3 listed case (warmup,
  simultaneous, opposing, ordering, prefix, frozen equality) or CND-02/04/05/09.
  Check D: Gherkin-first with `scenarios("../features/candle_catalog.feature")`.
- Status: tasks.md T3 boxes ticked; spec.md CND-01 → `Implemented (T1, T3)`, CND-02 →
  `Implemented (T2, T3)`, CND-04/05/09 → `Implemented (T3)`.
- Commit: `feat(candles): implement the expanded geometry catalog` (`ea95c24`); pushed.

### 2026-09-28 — T4 causal context evaluation (CND-03, CND-04, CND-05, CND-06)

- Files: `perception/candle_context.py` (new: `ema_value` seeded like
  `training.ema_series`, `stochastic_evidence`/`_raw_k`/`_smoothed`/`_zone` for the
  12,3,3 stochastic with strict 80/20 zones, `level_evidence` for the SMA 20/50/200
  normalized distances, `_t_line_position`/`_TREND` for trend, `evaluate_context` and
  the streaming `ContextEvaluator`), `tests/features/candle_context.feature`
  (specifier, unchanged), `tests/steps/test_candle_context.py` (new),
  `tools/perception_quality.py` (registration: `candle_context` may import
  `candle_contract` only — carried over from the prior session's hand-off, verified
  correct and unchanged).
- Assumptions: none beyond the ledger's pinned choices (gaps 12–14 in
  `qa-procedure-phase1.md`): `ContextEvaluator` is a thin streaming wrapper around
  `evaluate_context` bound to a `CandleHistory`; `evaluate_context` itself is a pure
  function of the retained closed-bar window so both the streaming and static paths
  share one implementation (prefix invariance follows structurally).
- Gate (cwd `algo-suite`, all exit 0):
  `uv run pytest algo-backtest/tests/steps/test_candle_context.py -q -p no:cacheprovider`
  → 52 passed;
  `uv run pytest algo-backtest/tests/steps/test_candle_contract.py algo-backtest/tests/steps/test_candle_catalog.py algo-backtest/tests/steps/test_candle_context.py -q -p no:cacheprovider`
  → 270 passed; `uv run ruff check algo-backtest tools` → clean;
  `uv run mypy --strict algo-backtest tools/perception_quality.py` → 67 files clean;
  `make check-perception-architecture` → PASS.
  Pure gate host-side line (the `make check-perception` pytest --cov line plus the
  three new step files): 553 passed, 9 deselected; `candle_context.py` 98.75% covered;
  `candle_contract.py` rose from T3's 90% to 95.4% (`ContextEvidence`,
  `IndicatorValue`, `StochasticEvidence`, `LevelEvidence` validators now exercised;
  `SequenceEvidence` and the confirmation branch of `CandleEvidence.__post_init__`
  remain uncovered pending T5/T6, as T3 predicted).
  `uv run python tools/perception_quality.py --coverage build/perception-host-coverage.json`
  (informative, without the native merge): every `candle_context.py` function CRAP <= 8
  (highest `_smoothed` CRAP 4.03); the two `candle_contract.py` FAILs
  (`SequenceEvidence.__post_init__` CRAP 14.08, `CandleEvidence.__post_init__` CRAP
  8.13) and the two pre-existing `lean_indicator.py` FAILs are all coverage-driven by
  branches T5/T6/native-runtime tests exercise, not by this task's code; re-checked at
  phase end. Docker lines of `make check-perception` (native LEAN assertions, feature
  parity, closed-signal parity, mutations): BLOCKED in this lane until the phase-end
  attempt (recorded there).
- Adequacy review (file `tests/steps/test_candle_context.py`): CND-06 separately typed
  fields → `assert_fields` :396 (`ema`/`stochastic`/`levels`/`trend` all present),
  `assert_own_status` :403 (each field's own status), `assert_no_hits` :414 (no pattern
  hit or confirmation field on context evidence); CND-04 per-indicator WARMUP →
  `assert_ema` :281, `assert_raw_k` :299, `assert_slow_k` :305, `assert_d` :311,
  `assert_level_statuses` :357, `assert_status` :364 (hand-calculated EMA(8) seed,
  stochastic 12/14/16-bar readiness, SMA 20/50/200 per-period readiness); CND-04 flat/
  zero-range handling without NaN → `assert_zone` :317, `assert_finite` :337
  (UNDEFINED value/status, `math.isnan`/`isinf` false on every field); CND-05 causal,
  prefix-invariant evidence → `assert_prefix_invariance` :421 (`first == second` across
  a rising and a falling suffix), `assert_prefix_ema` :429, `assert_history_count` :390
  (256-bar eviction); CND-03 fail-fast configuration/input validation without state
  mutation → `assert_context_rejected` :267, `assert_candle_rejected` :274,
  `assert_rejected` :370, `assert_recovers` :383 (a rejected bar leaves ema/status
  unchanged, then the next valid close is hand-calculated); boundary exactness →
  `assert_distances` :343, `assert_close_time` :435. Check B: every assertion compares
  a value/status/field set or a rejection-message fragment; none is call-count or
  no-throw-only. Check C: every scenario maps to a ledger parameter (T-line, 12,3,3
  stochastic, SMA 20/50/200), a tasks.md T4 listed case (hand-calculated values, exact
  boundaries, warmup by indicator, flat/zero-range, invalid configuration, unchanged
  prefixes) or CND-03/04/05/06; none removed. Check D: Gherkin-first with
  `scenarios("../features/candle_context.feature")`, one-line docstring on every step.
- Status: tasks.md T4 boxes ticked; spec.md CND-03 → `Implemented (T2, T4)`, CND-04 →
  `Implemented (T3, T4)`, CND-05 → `Implemented (T3, T4)`, CND-06 → `Implemented (T4)`.
- Commit: `feat(candles): implement causal context evaluation` (`4a0d4d7`); pushed.

### 2026-09-28 — T5 next-bar confirmation state machine (CND-05, CND-07, CND-08)

- Files: `perception/candle_sequence.py` (new: `ScheduledClosure`/`CalendarPolicy`,
  `_expected_next_close`/`_aligned_strictly_after` for the calendar-aware next-close
  computation, `_confirmation_direction` for the inclusive-edge engulfing check,
  `_is_doji` reusing T3's `evaluate_catalog` with a single-rule `CandleConfig`, and
  the streaming `SequenceEvaluator`), `tests/features/candle_sequence.feature`
  (specifier, unchanged), `tests/steps/test_candle_sequence.py` (new),
  `tools/perception_quality.py` (registration: `candle_sequence` may import
  `candle_contract` and `candle_catalog`).
- Assumptions: none beyond the ledger's pinned choices (gaps 3, 4, 16, 17 in
  `qa-procedure-phase1.md`). `SequenceEvaluator` reuses T2's `validate_bar` directly
  (not `CandleHistory`, whose `last_gap` only tracks the continuous grid and cannot
  express a scheduled closure) so ordering/duplicate rejection and the calendar
  policy share one bar-timestamp check. `evaluate_catalog` on a single bar with
  `enabled_rules=("doji",)` reuses T3's exact doji geometry rather than
  reimplementing it; discovered mid-task that a READY-but-non-firing rule is
  *omitted* from `evaluate_catalog`'s output (gap 2), not returned as a false hit,
  so `_is_doji` treats an empty result as "not a doji" rather than indexing into it.
- Gate (cwd `algo-suite`, all exit 0):
  `uv run pytest algo-backtest/tests/steps/test_candle_sequence.py -q -p no:cacheprovider`
  → 20 passed;
  `uv run pytest algo-backtest/tests/steps/test_candle_contract.py algo-backtest/tests/steps/test_candle_catalog.py algo-backtest/tests/steps/test_candle_context.py algo-backtest/tests/steps/test_candle_sequence.py -q -p no:cacheprovider`
  → 290 passed; `uv run ruff check algo-backtest tools` → clean;
  `uv run mypy --strict algo-backtest tools/perception_quality.py` → 68 files clean;
  `make check-perception-architecture` → PASS.
  Pure gate host-side line (the `make check-perception` pytest --cov line plus the
  four new step files): 573 passed, 9 deselected; `candle_sequence.py` 96.7% covered,
  `candle_catalog.py` 100%; `candle_contract.py` rose to 97.0%
  (`SequenceEvidence.__post_init__` CRAP fell from T4's informative 14.08 to 4.05,
  now exercised). `uv run python tools/perception_quality.py --coverage
  build/perception-host-coverage.json` (informative, without the native merge):
  every `candle_sequence.py` function CRAP <= 8 (highest `_confirmation_direction`
  CRAP 7.0); the sole remaining non-native FAIL is `candle_contract.py:
  CandleEvidence.__post_init__` CRAP 8.125 (the `confirmation` field's isinstance
  branch, only exercised once a producer assembles both context and confirmation
  onto one `CandleEvidence`, which is T6/T7 scope); the two pre-existing
  `lean_indicator.py` FAILs are native-runtime, out of this lane's scope. Docker
  lines of `make check-perception` (native LEAN assertions, feature parity,
  closed-signal parity, mutations): BLOCKED in this lane until the phase-end attempt
  (recorded there).
- Adequacy review (file `tests/steps/test_candle_sequence.py`): CND-07 confirmation
  dated at the confirming bar's close → `assert_confirmation_time` :246
  (`evidence.confirmation_time == parsed time`), `assert_direction_with_id` :231
  (direction and the ledger's named rule id both checked); CND-08 non-qualifying
  expiry → `assert_reason` :264 (`"not_engulfing"`), `assert_states` :208 (EXPIRED in
  the per-bar sequence); CND-05 causal, prefix-invariant evidence → `assert_
  suffix_invariance` :294 (`first[:5] == second[:5]`), `assert_suffix_diverge` :303
  (bar 6 differs by suffix); missing-expected-bar expiry under both the continuous
  grid and a scheduled closure → the four "Rule: Missing expected bars" scenarios,
  asserted via `assert_reason`/`assert_states`/`assert_confirmation_time`; inclusive
  engulfing edges and mandatory colour → the 6-row Scenario Outline via
  `assert_state_at` :215 and `assert_direction` :240; replacement candidates and
  no self-confirmation → `assert_candidate_time` :258 over the `F, D, D, B` and
  `F, D, D(gap), B` scenarios; fail-fast without consuming state →
  `assert_rejected` :270, `assert_still_candidate` :278, `assert_next_confirms` :285;
  separately typed evidence → `assert_fields` :316 (`{state, candidate_close_time,
  confirmed_direction, confirmation_time, reason}` exactly), `assert_no_hits` :329.
  Check B: every assertion compares state/direction/timestamp/reason values or a
  rejection-message fragment; none is call-count or no-throw-only. Check C: every
  scenario maps to a ledger definition (doji, qualifying engulfing, expected next
  bar, calendar policy) or a tasks.md T5 listed case (both directions, failed
  confirmation, expiry, replacement candidate, no self-confirmation, missing
  expected bar, suffix invariance); none removed. Check D: Gherkin-first with
  `scenarios("../features/candle_sequence.feature")`, one-line docstring on every
  step.
- Status: tasks.md T5 boxes ticked; spec.md CND-05 → `Implemented (T3, T4, T5)`,
  CND-07/08 → `Implemented (T5)`.
- Commit: `feat(candles): implement next-bar confirmation state machine` (`354c9cb`); pushed.

### 2026-09-28 — T6 explicit F3 policy modes (CND-09, CND-11, CND-12)

- Files: `chain/filters/f3_pattern.py` (`PatternConfig` gains `mode: str = "legacy"`;
  `parse_pattern_config`/`_mode` validate it against T2's `POLICY_MODES`;
  `pattern_mapping` gains a `mode` entry after `detector`; `F3PatternFilter.apply`
  dispatches to the unchanged legacy path (renamed `_apply_legacy`, byte-identical)
  or the new `_apply_evidence`, which reads `state.features["candle_evidence"]`,
  computes candidate directions via `_candidates`/`_candidate_ids` (READY non-neutral
  hits plus a CONFIRMED sequence's direction as a `doji_engulfing_bullish`/`_bearish`
  pseudo-id), checks eligibility via `_satisfied` (T-line position and stochastic
  zone), and returns BUY/SELL/ABSTAIN with the `warmup`/`neutral_only`/`conflicting`/
  `context` reason codes and `candle_hits`/`candle_mode`/`candle_veto_reason`
  enrichment via `_evaluate`), `tests/features/f3_policy_modes.feature` (specifier,
  unchanged), `tests/steps/test_f3_policy_modes.py` (new).
- Assumptions: none beyond the ledger's pinned choices (gaps 18-22 in
  `qa-procedure-phase1.md`). Reused `state.features["candle_evidence"]` directly
  rather than adding a helper, since T7 (out of this lane's scope) is the only
  future writer of that key. `f3_policy_modes.feature`'s own step file duplicates
  the `pattern section`/`parsed bullish patterns`/`raises an error naming` steps
  already in `test_f3_pattern.py` (own module, own fixture `f3m_ctx`) because
  `--import-mode=importlib` step modules are not cross-importable (same reason T3
  recorded for its legacy fixtures); `test_f3_pattern.py`'s 15 pre-existing
  scenarios were re-run unmodified to prove the addition is non-invasive.
- Gate (cwd `algo-suite`, all exit 0):
  `uv run pytest algo-backtest/tests/steps/test_f3_policy_modes.py -q -p no:cacheprovider`
  → 53 passed;
  `uv run pytest algo-backtest/tests/steps/test_f3_pattern.py algo-backtest/tests/steps/test_f3_policy_modes.py -q -p no:cacheprovider`
  → 73 passed (the 15 legacy scenarios unchanged); `uv run ruff check algo-backtest tools`
  → clean; `uv run mypy --strict algo-backtest tools/perception_quality.py` → 68 files
  clean (F3PatternFilter is outside `tools/perception_quality.py`'s registry — it lives
  in `chain/filters`, not `perception`, so no registration was needed or made).
  Phase-end Build gate: `uv run pytest algo-backtest/tests -q -p no:cacheprovider` →
  1941 passed, 53 deselected (baseline at T0 was 1598/1651 collected, 53 deselected;
  1994 collected now = +343 new scenarios across T2-T6). `make lint` and `make type`
  (full workspace, not `algo-backtest`/`tools` alone): both FAIL, but every failure is
  in `scripts/bigquery_*.py`, `tools/mutation_harness.py` and
  `docs/stories/done/20-session-2-clean-rerun/scripts/*.py` — pre-existing debt with
  no Story 22 file in the diff (confirmed via `git diff --stat` on those paths across
  this branch's commits: empty), unrelated to `algo-backtest`/`tools` scope and outside
  this lane's private files; recorded as pre-existing, not a Story 22 regression.
- Phase-end Docker attempt (`make check-perception`, this lane's first successful
  full run — Docker/LEAN image was already cached locally): the three native/LEAN
  lines all PASS — `test_double_smoothed_heikin_ashi.py`+`test_perception_hardening.py`
  host coverage line 283 passed; the same two `-m integration` → 9 passed;
  `test_feature_parity.py -m integration` → 8 passed;
  `test_closed_signal_parity.py`+`test_minute_pnl_anchors.py -m integration` → 7
  passed — proving Story 22 introduced no regression in the existing native/parity
  suite. The final `perception_quality.py --coverage ... --merged-coverage` CRAP step
  FAILs: every `candle_*.py` function reports 0% coverage there, because the
  Makefile's own hardcoded host-coverage command (`check-perception:` target, line 1)
  lists only the six pre-Story-22 step files and was never extended to the four new
  `test_candle_*.py`/`test_f3_policy_modes.py` files — a Makefile edit, which is
  explicitly outside T1-T6's private files (COMMON-RULES/LANE-C brief). This is a
  structural gap for the integration lane (T7+) to close, not a code defect: the same
  files reach 96.7-100% coverage under the host-side line this lane actually runs (see
  each task's own entry above). Full log: `/home/wellington/.cache/claude-tmp/check-perception.log`
  (this lane's scratch directory, not part of the repo).
- Adequacy review (file `tests/steps/test_f3_policy_modes.py`): CND-09 legacy
  byte-identical and evidence-blind → the "Legacy decisions are frozen" Outline and
  `assert_matches_default` :318 (`parsed == default` `FilterResult` equality across
  all six legacy names and no-pattern); CND-11 advisory never vetoes → `assert_no_veto`
  :280 across every advisory row including every ABSTAIN; CND-12 required-entry vetoes
  ineligible bars with a distinct reason → `assert_veto` :287 (`result.veto ==
  (veto=="true")`) over 15 required_entry rows, `assert_four_codes` :330
  (`reason.startswith(code)` for warmup/neutral_only/conflicting/context, four
  independently built fixtures) and `assert_enrichment` :343 (`enrichment ==
  {"candle_hits": ..., "candle_mode": ..., "candle_veto_reason": ...}` exactly on the
  conflicting-hits fixture); mode parsing and rejection → `assert_mode` :236,
  `assert_failure` :250 over 5 invalid-mode cases (wrong case, integer, null, list,
  unknown value) plus the 4-row valid-mode Outline; `pattern_mapping`'s `mode` entry
  → `assert_mapping` :257 (exact dict equality against the feature's JSON literal);
  missing/malformed evidence → `assert_raises_naming`/`assert_error_also_names` :301,
  :308 (both "candle_evidence" and the mode name checked) over the three malformed-
  evidence scenarios (absent in advisory, absent in required_entry, wrong type).
  Check B: every assertion compares a recommendation/veto/reason-prefix/enrichment
  dict/error-message fragment; none is call-count or no-throw-only. Check C: every
  scenario maps to a ledger eligibility rule (candidate directions, T-line/zone
  satisfaction, the four reason codes) or a tasks.md T6 listed case (advisory abstain
  without veto, required warmup/neutral/conflict rejection, eligible long/short, frozen
  legacy decisions); none removed; the pre-existing `f3_pattern.feature`'s 15 scenarios
  are untouched. Check D: Gherkin-first with
  `scenarios("../features/f3_policy_modes.feature")`, one-line docstring on every step.
- Status: tasks.md T6 boxes ticked; spec.md CND-09 → `Implemented (T3, T6)`,
  CND-11/12 → `Implemented (T6)`.
- Commit: `feat(candles): implement explicit f3 policy modes` (SHA in the next entry).

## Phase 1 gate (T1-T6 complete)

All six Phase 1 tasks are committed and pushed on `feat/22-candlestick-rules`. Baseline
at branch start (`ef0111d`): 1598/1651 collected, 53 deselected. End of Phase 1:
1941 passed, 53 deselected (1994 collected; +343 scenarios). `uv run ruff check
algo-backtest tools` and `uv run mypy --strict algo-backtest tools/perception_quality.py`
are clean at every task and at phase end. `make check-perception-architecture` PASS
throughout. Full-workspace `make lint`/`make type` fail only on pre-existing,
Story-22-unrelated files (see the T6 entry above); not attempted to fix, out of scope.
`make check-perception`'s Docker/native lines all PASS (no regression); its merged CRAP
step fails solely because the Makefile's hardcoded coverage command doesn't yet include
the new `test_candle_*.py`/`test_f3_policy_modes.py` files, a structural item for the
integration lane. `git -C /tmp/mba-impl-22 status --short`: clean (all six commits
pushed to `origin/feat/22-candlestick-rules`).

## 2026-09-28 — Cleaner phase 1 review (no code changes)

Independent review of `05bbdad..d20f152` on `feat/22-candlestick-rules`
(scope: `git diff ef0111d..HEAD -- algo-backtest/src tools/perception_quality.py`).

| File | ruff C901/PLR0912/PLR0915 | mypy --strict | Coverage (lines+branches) | Max CRAP (function) | Actions |
| --- | --- | --- | --- | --- | --- |
| `perception/candle_contract.py` | clean | clean | 96% — 9 lines / 8 branches uncovered, all in `__post_init__`/`_validated_hits`/`CandleHistory.config` invariant guards (never exercised by an invalid-construction scenario) | `CandleEvidence.__post_init__` ≈8.11 (cc=8, borderline; matches the coder's own T5 note of 8.125) | none — see findings |
| `perception/candle_catalog.py` | clean | clean | 100% | all ≤8 | none |
| `perception/candle_context.py` | clean | clean | 99% — `ContextEvaluator.history` property getter (line 148) untested | ≤2 | none |
| `perception/candle_sequence.py` | clean | clean | 94% — `ScheduledClosure`/`CalendarPolicy` invariant guards (lines 65, 69, 84) and one branch of `_expected_next_close`'s no-match path uncovered | `ScheduledClosure.__post_init__` ≈5.6 | none |
| `chain/filters/f3_pattern.py` | clean | clean | 98% — missing lines 142/144 are in the pre-existing `_validate_detector` (unchanged by this diff, not new mode-handling code); all new `_evaluate`/`_candidates`/`_satisfied`/`_apply_evidence` lines are 100% covered | `_evaluate` radon cc=9 (ruff's actual C901 gate, max-complexity 8, passes clean — reviewed the function: five linear guard-clause returns, judged readable, not split) | none |
| `tools/perception_quality.py` (registration diff) | clean | clean | n/a (10-line diff, not itself a coverage target) | n/a | none |

Findings (report-only, no refactor applied):
- The four new modules' uncovered lines are all dataclass `__post_init__`
  fail-fast invariant guards ("repair the producer/evaluator" raises) plus one
  untested public accessor (`ContextEvaluator.history`) — a test-coverage gap,
  not a complexity or duplication problem. Splitting the flagged functions
  would not raise coverage (the same branches would just be measured in a
  smaller, still-uncovered function, worsening that function's own CRAP) and
  writing new invalid-construction scenarios is Specifier/Hardener scope per
  `STAGES.md`, not Cleaner's, so none were added here. Recommend the Hardener
  stage's mutation pass (or a Coder follow-up) add scenarios that construct
  invalid `ScheduledClosure`/`CalendarPolicy`/`CandleEvidence`/etc. and read
  `ContextEvaluator.history`, which will also resolve the one borderline CRAP
  (`CandleEvidence.__post_init__`) without any production-code change.
- Confirmed duplication: `_price()` (OHLC scalar validator) in
  `candle_contract.py:478` is functionally identical to the legacy
  `candlestick.py:60` `_price()`, and both files contain an OHLC-ordering
  check with the same invariant. Per brief guidance, not merged: the legacy
  version types `value: float` while the new one deliberately types
  `value: object` (validating pre-normalization input), and the ordering
  check is packaged differently (legacy's separate `_validated_candle`
  normalizer vs. the new module's inline check in `validate_bar`) — merging
  would mean designing a new shared validation module and touching the
  perception architecture boundaries, not a trivial change. Left as a
  candidate for a dedicated future task, untouched.
- Confirmed code-22b's observation: `Makefile`'s `check-perception:` target
  (the pytest --cov line) hardcodes a pre-Story-22 step-file list and was
  never extended to `test_candle_contract.py`, `test_candle_catalog.py`,
  `test_candle_context.py`, `test_candle_sequence.py`,
  `test_f3_policy_modes.py`. This is integration-lane scope (already recorded
  in the T6 entry above); not fixed here.
- No missing docstrings (AST-checked, every function/method in all five
  files). No dead code or duplicate-import findings from a full
  `uv run ruff check` (all rules, not just C901) on the six files. Naming
  reviewed against `spec.md`/`candlestick-extension.md` (no `design.md`
  exists for Story 22 in this worktree); no conflicts found.
- `make check-perception-architecture check-inference-architecture`: both
  PASS, unchanged.

No production or test code was modified — every check passed or the only
gaps found require new test scenarios outside Cleaner's authorized scope
(STAGES.md reserves scenario-writing for Specifier/Hardener). This entry is
committed standalone as `docs(candles): record cleaner review for phase 1`.

## Hardener phase 1 (2026-09-28)

Manual mutation testing (no `mutmut` in the workspace) over the phase's five
production modules: `candle_contract.py`, `candle_catalog.py`,
`candle_context.py`, `candle_sequence.py`, and the mode-handling hunks in
`f3_pattern.py` (`git diff ef0111d..HEAD`). One mutation at a time, backed up
in place, run against the full covering test set (the five modules' own step
files plus `test_f3_policy_modes.py`, `test_candlestick_detector.py`,
`test_f3_pattern.py`), then restored and `git status --porcelain` reconfirmed
against the pre-mutation baseline before the next mutation. Full table,
operators and justifications: `mutation-phase1.md`.

- 51 mutations injected (15 contract, 8 catalog, 10 context, 10 sequence, 8
  F3 mode hunks) — well above the brief's 8-per-module / 6-for-F3 minimums.
  Negative control (CC1, a plainly-covered boundary) confirmed KILLED first.
- First pass: 45 KILLED, 6 SURVIVED, 0 TIMEOUT, 0 ERROR. All six survivors
  landed exactly on the coverage gaps the Cleaner flagged: the
  `sma_periods`/`MAX_HISTORY` boundary and a `SequenceEvidence` partial-
  contradiction case in `candle_contract.py`'s `__post_init__` guards
  (CC5, CC10), the `CandleHistory.config` and `ContextEvaluator.history`
  accessors (CC14, CX10), and two `ScheduledClosure`/`CalendarPolicy`-
  adjacent boundaries in `candle_sequence.py` (CS2: equal start/end; CS8: the
  half-open closure window's right edge).
- Added six killing Gherkin scenarios (feature first, then steps): a new
  Examples row for the `sma_periods` boundary; a new "Sequence evidence
  confirmation fields agree with its state" Rule with a construction Scenario
  Outline; a `config`/`history` accessor assertion added to two existing
  scenarios in `candle_contract.feature`/`candle_context.feature`; a new
  "A scheduled closure's bounds are validated eagerly" Rule; and a new
  closure-boundary scenario timed so a candidate's continuous next close
  lands exactly on `closure.end`. New step definitions in
  `test_candle_contract.py`, `test_candle_context.py`, `test_candle_sequence.py`.
  Re-running all six mutations against the hardened suite: all now KILLED.
- One equivalent mutant: CC12 (`_validated_hits`' ascending-order check
  widened from `<` to `<=`) is unreachable on any input, because the
  preceding duplicate check (`current == previous`) always raises first on an
  equal pair — no scenario added; justification recorded in
  `mutation-phase1.md`.
- Coverage after hardening (the same seven-file run): `candle_catalog.py`
  100% (unchanged), `candle_context.py` 100% (was 99%), `candle_sequence.py`
  98% (was 97%), `candle_contract.py` 98% (was 97%), `f3_pattern.py` 99%
  (unchanged — the two missing lines, 142/144, are `_validate_detector`'s
  raises, outside this phase's scope).
- Final gates, all PASS: `uv run pytest algo-backtest/tests -q
  -p no:cacheprovider` (1951 passed, 53 deselected), `uv run ruff check
  algo-backtest`, `uv run mypy --strict algo-backtest`, `make
  check-perception-architecture check-inference-architecture`.
- Restoration confirmed clean throughout: every mutation restored from its
  backup immediately after its test run, `git status --porcelain` matched
  the pre-mutation baseline (the phase-2 specifier's concurrently-added
  untracked feature files, left untouched) after every single mutation and
  after the full pass; no `.mutbak` files left behind.
- Committed as `test(candles): harden phase 1 modules against surviving
  mutants` (feature files, step files and this progress/mutation-report
  update only — no production code touched).

## Phase 2 integration: T7 minimum viable slice + first real backtests (2026-09-28)

Fast-tracked, time-boxed delivery: merged `origin/feat/23-bigalow-extended-signals`
into the Story 22 Phase 2 launch worktree (`3a525ef`, clean, no conflicts — Story 23
was branched from Story 22, so this merge brings both stories' catalog/context work,
`candle_contract.py`/`candle_catalog.py`/`candle_context.py`/`candle_sequence.py`/
`f3_pattern.py`'s legacy/advisory/required_entry modes, in one step), then implemented
T7 (`.specs/features/candlestick-context/tasks.md`) as a deliberately reduced minimum
viable slice, disclosed here:

- `chain/market_signals.py`: `MarketSignals` now builds a `CandleCatalog` +
  `ContextEvaluator` + `SequenceEvaluator` when `pattern.detector: expanded` is
  configured, merges their per-bar output into one `CandleEvidence` via
  `dataclasses.replace` (catalog evidence plus `context`/`confirmation` attached),
  and publishes it as `state.features["candle_evidence"]` every closed bar —
  `enabled_rules=ADMITTED_RULES`, i.e. the full ~19+3 catalog (Story 22's 19 plus
  Story 23's 3). `MarketSignals` now takes `bar_minutes`/`pair`; call sites in
  `engine/chain_algorithm.py` and `training.py` updated mechanically (training.py
  itself not otherwise touched — T10 is explicitly deferred, see below).
- `chain/filters/f3_pattern.py`'s `_validate_detector` now admits `"expanded"`
  alongside `"disabled"`/`"talib"`.
- Added the bundled strategy `strategies/candles-expanded/config.yaml`: F1(trend) +
  F3(pattern, `mode: required_entry`, `detector: expanded`) + F5(risk_guard) +
  F6(capital_mgmt), no F7 (`terminal_filter: f3_pattern`) — a rule-only chain proving
  the expanded catalog reaches native signal production without needing a trained
  model.
- Found and fixed a real, pre-existing bug surfaced by that no-F7 strategy:
  `chain/wiring.py`'s `terminal_decision()` built `LastFilterTerminalDecision` from
  the raw YAML canonical filter name instead of translating it through
  `_VOTER_NAME_MAP` to the runtime `FilterResult.filter_name` (`AgreementTerminalDecision`
  already did this translation; `LastFilterTerminalDecision` didn't). Harmless for
  `f4_news_context`/`constant_direction` (identical canonical/runtime names — the only
  `terminal_filter` values used before this), fatal for F1/F2/F3 (`f3_pattern` vs.
  `F3_pattern`). One-line fix (`_VOTER_NAME_MAP[config.terminal_filter]`), verified
  against the full suite and the native LEAN gate below.
- Added `tests/features/candles_expanded_integration.feature` (`@integration`): a
  mandatory native LEAN scenario proving `candles-expanded` runs a real backtest
  end-to-end in the pinned LEAN container with no `--model`, asserting
  `BASELINE_DECISION|` actually appears in the container log (the chain really ran,
  not just "CLI exited 0").

**Scope reduction (disclosed):** T8 (signal_contract fingerprinting for F7
compatibility), T9 (F7 pattern feature encoder), T10 (training.py candle wiring
beyond the mechanical constructor-signature change already made), and T11/T12
(decision_recorder/results-db extensions) are explicitly deferred — this slice's
runs use no F7 model. Cleaner/Hardener passes on this diff are also deferred
(disclosed time-boxing tradeoff, not silently skipped).

**Gates, all green:** `uv run pytest algo-backtest/tests -q -p no:cacheprovider`
(2369 passed, 0 failed), `uv run ruff check algo-backtest tools`, `uv run mypy
--strict algo-backtest`, `make check-perception-architecture
check-inference-architecture`. The native `@integration` LEAN scenario above passes.

Committed as `feat(candles): wire the expanded catalog into native signal
production (minimum viable slice for today's delivery)`.

### Real backtests: full-year 2015 (M1) vs. 2016-03/2017-02 (H1)

Two real runs of `candles-expanded` against real, materialized EUR/USD minute data
(the real `algo-backtest materialize`/`run` CLIs, the real pinned LEAN container —
never the main data root itself: parquet copied read-only into an ad-hoc scratch job
dir per run, lean-data materialized there).

**Full-year 2015 (2015-01-01 to 2015-12-31), M1 (`price_features.bar_minutes: 1`,
`candles-expanded`'s own default), $10,000 starting cash:**

| Metric | Value |
| --- | --- |
| Closed trades | 1,810 |
| Total return | -99.54% |
| Sharpe | -1.1498 |
| Max drawdown | 99.6% |
| Hit rate | 35.72% |
| Balance | 10,000.00 → 46.24 |

Ran clean (`success=True`, no `RuntimeError`) — this window did not trip the
same-bar double-fill condition described below.

**2016-03-01 to 2017-02-28 (the registered cross-story comparison window), $10,000
starting cash:**

The identical `candles-expanded` config (M1) hit a real, pre-existing bug on this
window: the CLI's post-run statement build refused with `ValueError: trade-plans.json
has no plan with entry_order_id 2053 for the closed trade entered at
2016-09-08T11:46:00+00:00; the executor records one per planned entry, so the run's
artifacts are inconsistent — re-run the backtest`. This is documented technical debt,
**TD-71** (`docs/technical-debt.md`): a same-bar stop/target double-fill that LEAN
can produce before `on_order_event` cancels the sibling order, which `decision_trail`/
`statement` correctly refuse to report on rather than print an untrustworthy number.
TD-71 notes this was "never in the reported H1/H4 runs" — `candles-expanded`'s M1
cadence combined with `required_entry`'s much higher signal churn than any
previously-tested chain made this window the first to trip it. **Not a Story 22/23
defect** — a known executor gap that a high-churn M1 chain was always going to expose
eventually.

To get a real, reportable number for this specific window without fixing TD-71 (a
nontrivial executor same-bar guard, out of this slice's scope), committed
`strategies/candles-expanded-h1/config.yaml`: `extends: candles-expanded`, overriding
only `price_features.bar_minutes: 60` (H1) — the cadence TD-71 says never trips this
bug. **This is a real, disclosed config change (60x slower decision cadence,
materially fewer trades), not the identical strategy `candles-expanded` runs at.**
Disclose this wherever a number from `candles-expanded-h1` is used.

**2016-03-01 to 2017-02-28, H1 (`candles-expanded-h1`), $10,000 starting cash:**

| Metric | Value |
| --- | --- |
| Closed trades | 285 |
| Total return | -32.79% |
| Sharpe | -0.7851 |
| Max drawdown | 42.6% |
| Hit rate | 33.12% |
| Balance | 10,000.00 → 6,719.60 |

Ran clean (`success=True`, 46s wall clock, well inside the CLI's `--timeout`; run.json/
statement.md/trade-plans.json/trades.json all present and non-partial).

**Comparison, side by side:**

| Window | Cadence | Trades | Total return | Sharpe | Max DD | Hit rate |
| --- | --- | --- | --- | --- | --- | --- |
| 2015-01-01 .. 2015-12-31 | M1 | 1,810 | -99.54% | -1.1498 | 99.6% | 35.72% |
| 2016-03-01 .. 2017-02-28 | H1 (TD-71 workaround) | 285 | -32.79% | -0.7851 | 42.6% | 33.12% |

Both windows show the same qualitative result: this untuned, model-free rule-only
chain (F1 + F3 required_entry/expanded catalog + F5 + F6, no F7) loses money,
consistent with the Story 12-14 finding that every arm was negative over a full
trading year. The two runs are not directly comparable as a controlled A/B (different
windows, different decision cadence) — they are two independent proofs that the
expanded-catalog wiring produces real, executable per-bar evidence in native LEAN,
not a performance claim.

Run artifacts (ad-hoc scratch job dirs, not committed, not under the data root):
- 2015 M1: `/tmp/mba-fast22-job-1790633366/data/runs/candles-expanded/20260928T221502-d48062c34504/`
- 2016-03/2017-02 H1: `/tmp/mba-fast22-job-1790634602-window2/data/runs/candles-expanded-h1/20260928T224937-d663697c9c3e/`
