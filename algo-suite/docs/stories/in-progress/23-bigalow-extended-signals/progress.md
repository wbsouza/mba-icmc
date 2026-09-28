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
