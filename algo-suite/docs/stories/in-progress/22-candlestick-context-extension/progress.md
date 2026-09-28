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
- [ ] T2 Define immutable pattern evidence and configuration
- [ ] T3 Implement the expanded geometry catalog
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
- Commit: `docs(candles): review and freeze the source-rule ledger` (SHA recorded below
  after commit).
