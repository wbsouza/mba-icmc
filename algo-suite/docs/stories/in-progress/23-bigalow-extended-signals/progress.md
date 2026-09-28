# Story 23 — progress

- [x] 2026-09-28 — story created from `book-mining`'s full-book read
  (findings in `~/.claude/skills/bigalow-candlestick-patterns/references/book-only-material.md`);
  scope deliberately narrowed to the four fully-computable items (Meeting
  Line, Methods Rising, Fibonacci confluence — Tweezer deferred, two
  unresolved conventions); named/factory filter-instance architecture
  explicitly deferred to a future story (user decision, time-boxed).
- [x] 2026-09-28 — T1: froze `rule-ledger-addendum.md` (Counterattack Line,
      Methods Rising and Fibonacci confluence geometry, citations, the two
      spec.md conventions plus one implementation-only tie-break convention,
      and positive/negative/boundary OHLC examples for every rule).
- [x] 2026-09-28 — T2: added `bearish_counterattack_line`,
      `bullish_counterattack_line` and `methods_rising` to `candle_catalog.py`
      / `candle_contract.py`'s `CATALOG`. Admitted (`ADMITTED_RULES`, now 22
      ids) but excluded from the default (`DEFAULT_ENABLED_RULES`, the
      frozen Story 22 19-rule set), so every existing `candle_catalog.feature`
      / `candle_contract.feature` scenario passes unmodified. Deviation: also
      touched `candle_contract.py` (CATALOG registration is unavoidable —
      `PatternHit`/`enabled_rules` validate against it) and split one
      existing `test_candle_contract.py` assertion (`assert_enabled_rules`)
      that had conflated "default enabled" with "admitted" — scoped it to
      the default config's own `enabled_rules` and added a new scenario
      proving the three extended ids are admitted but excluded from the
      default; no existing assertion's substance changed. 22 new scenario
      rows added (candle_catalog.feature), all passing.
- [x] 2026-09-28 — T3: added `FibonacciEvidence`/`FIBONACCI_LEVELS` to
      `candle_contract.py` and `fibonacci_evidence()` to `candle_context.py`,
      wired through `ContextEvidence.fibonacci` (opt-in via
      `ContextConfig.fibonacci_enabled`, default `False`, `fibonacci_lookback_bars`
      default 60). Swing high/low over the lookback, rising/falling leg
      chosen by which extreme is more recent, 0.10-of-range tolerance,
      UNDEFINED on zero range, WARMUP before the lookback, `None` field when
      disabled. 11 new scenarios in `candle_context.feature`, all 53
      existing scenarios pass unmodified.
- [x] 2026-09-28 — T4: marked the three geometry/context items
      (`bearish_counterattack_line`/`bullish_counterattack_line`,
      `methods_rising`, Fibonacci confluence) `**ADMITTED (Story 23)**` in
      `~/.claude/skills/bigalow-candlestick-patterns/references/book-only-material.md`,
      each pointing to the ledger addendum and its implementing commit SHA
      (T1 `833c820`, T2 `4424c25`, T3 `c359df9`). Deviation: that skill
      directory is not a git repository (`git -C
      ~/.claude/skills/bigalow-candlestick-patterns status` -> "fatal: not a
      git repository"), so the file was edited directly with no commit
      there; this algo-suite commit is the docs record of that edit, per
      tasks.md T4's amended "Where"/"Deviation" fields. Tweezer and "Too
      vague to compute" were left untouched (still deferred).

## Working tree and ownership

| Agent | Working tree | Branch | Base SHA |
| --- | --- | --- | --- |
| Coordinator (this session) | — | — | — |
| Coder | /tmp/mba-impl-23 | feat/23-bigalow-extended-signals | ebac509 (feat/22-candlestick-rules) |

## Deferred (explicit, not gates on this story)

- Named/parameterized filter-chain instances (abstract-factory-style rule-set
  presets) — real, wanted, deferred for time. See spec.md Out of Scope.
- Tweezer Top/Bottom, the SMA entry-trigger context field, and all
  stop/exit/sizing items from `book-only-material.md` — see spec.md Out of
  Scope for the per-item reasons.

## Close-out, 2026-09-28

Story 23 done: T1-T4 complete, all `Done when` boxes and all ten BEXT-01..10
requirement statuses in `spec.md`'s traceability table are `Implemented`.

- **T1** `833c820` — rule ledger addendum (citations, conventions, examples).
- **T2** `4424c25` — `bearish_counterattack_line`, `bullish_counterattack_line`,
  `methods_rising` added to the catalog, admitted but excluded from the
  default (`DEFAULT_ENABLED_RULES`); 22 new Gherkin scenarios, all existing
  `candle_catalog.feature`/`candle_contract.feature` scenarios pass
  unmodified (one existing assertion was scoped, not weakened — see the T2
  entry above).
- **T3** `c359df9` — opt-in Fibonacci confluence field on `ContextEvidence`;
  11 new scenarios, all 53 existing `candle_context.feature` scenarios pass
  unmodified.
- **T4** `4d04d11` — the reference skill's `book-only-material.md` marked
  `ADMITTED (Story 23)` for the three implemented items, edited directly (no
  commit there — that directory is not a git repository).

**Final gates** (worktree `/tmp/mba-impl-23`, branch
`feat/23-bigalow-extended-signals`):

| Gate | Command | Result |
| --- | --- | --- |
| Full suite | `uv run pytest algo-backtest/tests -q -p no:cacheprovider` | 1985 passed, 53 deselected (2038 collected); baseline at `ebac509` was 1951 selected / 2004 collected (verified directly against a temporary detached worktree at `ebac509`, then removed) — delta +34, all attributable to T2 (+22) and T3 (+11) plus one new `candle_contract.feature` scenario (+1) |
| Lint | `uv run ruff check algo-backtest` | All checks passed |
| Types | `uv run mypy --strict algo-backtest` (after `rm -rf .mypy_cache`) | Success: no issues found in 67 source files (test files are out of this gate's scope by the repo's own mypy config, `tool.mypy` in the root `pyproject.toml`: "Tests are run by pytest; mypy checks src only") |
| Architecture | `make check-perception-architecture` | PASS |

No blockers. Scope not delivered: the four items explicitly deferred in
`spec.md`'s Out of Scope table (named/factory filter-chain instances,
money-management rules, the SMA entry-trigger context field, Tweezer
Top/Bottom) — all by prior user decision, not incomplete work.

## Cleaner review, 2026-09-28

Baseline `ebac509..6ab39b0`, scope `algo-backtest/src` (candle_catalog.py,
candle_contract.py, candle_context.py) plus their three step files. Complexity
computed with `radon cc -s` (importable); ruff's own C901 engine scores some
of these functions lower than radon (e.g. `fibonacci_evidence` C901 <= 5 vs.
radon 14) and was used only for the repo's own gate (threshold 8, passed
throughout), not for CRAP.

| File | Ruff C901/PLR (thresh 8) | mypy --strict | Coverage (branch) | Max CRAP/cc (radon) | Actions |
| --- | --- | --- | --- | --- | --- |
| candle_catalog.py | All checks passed | Success | 100% | `_methods_rising` cc=8 (at threshold, not over); all else <= 5 after refactor | Extracted `_body_midpoint(prior)` shared by `_piercing_line`, `_dark_cloud_cover`, `_bearish_counterattack_line`, `_bullish_counterattack_line` (identical `(open+close)/2` formula duplicated 4x) |
| candle_context.py | All checks passed | Success | 100% | `fibonacci_evidence` was cc=14 (CRAP 14 at 100% cov) — over threshold | Split into `_swing(window)` (cc=7) and `_nearest_level(...)` (cc=6); `fibonacci_evidence` now cc=3 |
| candle_contract.py | All checks passed | Success | 94% (14 lines uncovered, all pre-existing "repair the evaluator/producer" invariant guards unreachable via the public API — same untested-defensive-guard pattern already present at `ContextEvidence`/`CandleEvidence`/`SequenceEvidence` before Story 23; not a new gap) | `FibonacciEvidence.__post_init__` was cc=9 (CRAP ~13 given its 3 raise branches are among the uncovered lines) — over threshold | Split into `_validate_swings()` (cc=6) and `_validate_level()` (cc=4); `__post_init__` now cc=1 |

Reviewed, not changed: `DEFAULT_ENABLED_RULES` is a separate literal tuple
rather than `ADMITTED_RULES` minus the three Story 23 ids — this is
intentional (the module docstring and BEXT-06 require the default to stay
byte-identical against future `CATALOG` growth, so an explicit frozen list is
correct; a derived exclusion-set would silently re-admit any new rule by
default). No duplication defect found.

Post-refactor: all three step files green (312 passed, unchanged assertions),
`uv run ruff check algo-backtest` all checks passed, `uv run mypy --strict
algo-backtest` success on 67 source files (`.mypy_cache` removed after), `make
check-perception-architecture` PASS.
