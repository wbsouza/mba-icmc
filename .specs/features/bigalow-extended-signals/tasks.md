# Bigalow extended signals tasks

Status: approved for implementation 2026-09-28. Baseline: `feat/22-candlestick-rules`
at `ebac509`. [Spec](spec.md). No design.md — this is a small, scoped extension
of two existing, already-designed classes (`candle_catalog.py`, `candle_context.py`),
not new architecture; see spec.md's Assumptions table for the component-level
decisions a design.md would otherwise hold.

## Execution Protocol

Follow tlc-spec-driven's Execute flow: Gherkin first, implement, gate, mark
tasks.md/spec.md, one atomic Conventional Commit per task, trailer
`Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`, validated with
`python3 /home/wellington/.claude/skills/tlc-spec-driven/scripts/check_commit.py`.
NDA/CLAUDE.md rules apply (never name the two earlier trading systems;
Gherkin-only tests; fail-fast; docstrings).

## Test Coverage Matrix

| Code Layer | Required Test Type | Location Pattern | Run Command |
| --- | --- | --- | --- |
| Domain (candle_catalog.py, candle_context.py) | Gherkin/pytest-bdd unit | algo-backtest/tests/features + tests/steps | Quick |

## Gate Check Commands

| Gate | Command |
| --- | --- |
| Quick | `uv run pytest algo-backtest/tests/steps/test_<name>.py -q -p no:cacheprovider` (nonzero collected) plus `test_candle_catalog.py`/`test_candle_context.py` regressions |
| Build | `uv run ruff check algo-backtest`; `uv run mypy --strict algo-backtest` (`rm -rf .mypy_cache` after); `make check-perception-architecture` |
| Docs | `git diff --check`; `python3 /home/wellington/.claude/skills/tlc-spec-driven/scripts/validate_spec.py .specs/features/bigalow-extended-signals/spec.md --strict`; `python3 /home/wellington/.claude/skills/tlc-spec-driven/scripts/validate_tasks.py .specs/features/bigalow-extended-signals/tasks.md --strict` |

## Execution Plan

```text
T1 -> T2 -> T3 -> T4 -> T5
```

## Task Breakdown

### T1: Freeze the extension's source-rule ledger addendum

**What**: Record the three new patterns' exact geometry, book citations
(PDF page + line range, from `book-only-material.md`), positive/negative/
boundary OHLC examples, and the two conventions chosen in spec.md's
Assumptions table (Meeting Line tolerance, Fibonacci swing reuse).

**Where**: `algo-suite/docs/stories/in-progress/23-bigalow-extended-signals/rule-ledger-addendum.md`
**Depends on**: None
**Requirement**: BEXT-01, BEXT-02, BEXT-07
**Reuses**: The existing `candlestick-rule-ledger.md`'s format (from Story 22, read-only reference — do not edit that file, this is a new addendum for this story).
**Tests**: Documentation checks.
**Gate**: Docs (commands above).
**Done when**:
- [x] Every new rule has a citation, one positive/negative/boundary example, and the chosen convention stated explicitly.

**Commit**: `docs(candles): freeze the bigalow extended-signals rule ledger addendum`

### T2: Add Meeting Line and Methods Rising to the catalog

**What**: Extend `candle_catalog.py`'s multilabel table with `bullish_counterattack_line`,
`bearish_counterattack_line`, `methods_rising` per T1's addendum. Preserve
the existing 18-rule catalog's exact output when these new IDs are not in
the enabled-rule config. Register in `tools/perception_quality.py` if new
rule functions need separate quality registration (check the existing
pattern first — likely no separate registration needed since this extends
the same module, not a new one).

**Where**: `algo-suite/algo-backtest/src/algo_backtest/perception/candle_catalog.py`
**Depends on**: T1
**Requirement**: BEXT-01, BEXT-02, BEXT-03, BEXT-04, BEXT-05, BEXT-06
**Reuses**: The existing multilabel evaluator, `select_pattern`-style priority handling if applicable, the existing WARMUP/prefix-invariance test helpers from `candle_catalog.feature`'s step file.
**Tests**: Gherkin unit. At least 3 cases per new rule ID (positive/negative/boundary, per T1's addendum) plus warmup, prefix-invariance, and legacy-catalog-unchanged cases — at least 15 scenarios total.
**Gate**: Quick.
**Done when**:
- [x] All listed cases pass; legacy 18-rule scenarios still pass unmodified.
- [x] Evidence and requirement/task status included in the commit.

**Commit**: `feat(candles): add meeting line and methods rising to the catalog`

### T3: Add Fibonacci confluence to the context evaluator

**What**: Extend `candle_context.py`'s `ContextEvidence`/`ContextEvaluator`
with a Fibonacci-retracement confluence field, reusing the existing swing
high/low calculation per spec.md's convention table. Existing fields
(T-line, stochastic, SMA distances) unchanged when this field is disabled.

**Where**: `algo-suite/algo-backtest/src/algo_backtest/perception/candle_context.py`
**Depends on**: T2
**Requirement**: BEXT-07, BEXT-08, BEXT-09, BEXT-10
**Reuses**: The existing swing-level lookback already computed for F6's stop distance.
**Tests**: Gherkin unit. At least 10 scenarios: hand-calculated rising/falling-trend retracement levels, at-tolerance and outside-tolerance prices, zero-range degenerate case, warmup, and the "existing fields unchanged" regression.
**Gate**: Quick.
**Done when**:
- [ ] All listed cases pass; existing context-field scenarios unmodified.
- [ ] Evidence and requirement/task status included in the commit.

**Commit**: `feat(candles): add fibonacci confluence to the context evaluator`

### T4: Mark the extension admitted in the reference skill

**What**: Update the skill's `book-only-material.md` to mark the four
admitted items as `ADMITTED (Story 23)` with a pointer to the ledger
addendum and the implementing commits, so the reference skill and the
engine stay in sync.

**Where**: `~/.claude/skills/bigalow-candlestick-patterns/references/book-only-material.md`
**Depends on**: T3
**Requirement**: (documentation only, no new BEXT ID)
**Tests**: Documentation checks.
**Gate**: Docs (commands above).
**Done when**:
- [ ] The skill file reflects the implemented state for all four items.

**Commit**: `docs(candles): mark the bigalow extended signals as admitted in the skill`

### T5: Close out the story progress

**What**: Update this story's `progress.md` checklist and add a dated
close-out entry summarizing T1-T4.

**Where**: `algo-suite/docs/stories/in-progress/23-bigalow-extended-signals/progress.md`
**Depends on**: T4
**Requirement**: (documentation only, no new BEXT ID)
**Tests**: Documentation checks.
**Gate**: Docs (commands above).
**Done when**:
- [ ] progress.md's T1-T4 checklist items are all checked with a dated close-out entry.

**Commit**: `docs(candles): close out story 23 progress`

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1 | One document | Atomic |
| T2 | One catalog extension | Atomic |
| T3 | One context extension | Atomic |
| T4 | One document | Atomic |
| T5 | One document | Atomic |

## Diagram-Definition Cross-Check

| Task | Depends on | Diagram | Status |
| --- | --- | --- | --- |
| T1 | None | None | Match |
| T2 | T1 | T1 | Match |
| T3 | T2 | T2 | Match |
| T4 | T3 | T3 | Match |
| T5 | T4 | T4 | Match |
