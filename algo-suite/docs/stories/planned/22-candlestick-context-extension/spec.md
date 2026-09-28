# Story 22 — candlestick context extension (planned)

Status: planned. Drafted 2026-09-28 by Codex inside story 13 (as "planned candlestick extension")
and split into its own story when story 13 closed. Owner: unassigned. No implementation, model or
experiment has run.

## Entry points

- [Candlestick catalog and learned-context brief](candlestick-extension.md): Bigalow's catalogue and
  context rules, the supplied CMT presentation, Laya as a proposed learned pattern/context complement
  to TA-Lib's detector.
- [Timestamped webinar notes](bigalow-video-notes.md).
- tlc-spec-driven plan under `.specs/features/candlestick-context/` (specification, design, 24 tasks);
  its task outputs (`candlestick-rule-ledger.md`, `candlestick-method-design.md`,
  `candlestick-results.md`) land in this directory.

## Evidence already in hand (from the 2026-09-28 offline checks, exploratory)

On the session-2 H1 decision log the six TA-Lib patterns read as continuation signals lean the wrong
way (bearish engulfing: next bar up 61 % of the time, n = 291); read in context (bullish after a fall,
bullish in an F1 downtrend, bullish near a 60-bar low) the bullish side shows 54–59 % at 4 hours on
small samples; the shooting star works as intended (63 % at 4 h, n = 41). Tables:
`in-progress/21-confluence-chain/evidence/signal-horizon-check.md`. This is why the extension's first
deliverable is the context-rule ledger, not more patterns.

## Boundaries

Same as the .specs plan: frozen model versions, causal inputs, independent recognition review,
controlled comparisons on the session-2 protocol; nothing here changes stories 16, 19 or 21.
