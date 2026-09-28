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
- [ ] T4 Implement causal context evaluation
- [ ] T5 Implement next-bar confirmation state machine
- [ ] T6 Implement explicit F3 policy modes
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
- Commit: `feat(candles): implement the expanded geometry catalog` (SHA in the next entry).
