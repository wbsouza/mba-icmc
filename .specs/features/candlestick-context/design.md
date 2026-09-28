# Candlestick context design

Status: proposed, planning only. The user explicitly deferred implementation.
Read [spec.md](spec.md) and [context.md](context.md) before execution. No new
architecture decision is approved by the existence of this document.

## Architecture

Use one causal rule producer for offline preparation and LEAN. Keep the old
single-label mode intact. Add optional learned context through locally prepared,
immutable per-bar outputs; do not require a model runtime inside LEAN.

```text
Canonical closed UTC bars
  -> versioned multilabel geometry
  -> causal context + next-bar confirmation
  -> F3 advisory / required-entry policy -> existing chain and risk protection
                   |
                   +-> decision evidence -> results database -> viewer

Reviewed sequences -> chronological split -> frozen Laya model -> keyed cache
                                                                |
                          optional context provider <------------+
```

The cache design adds an artifact lifecycle but isolates model dependencies from
engine replay. Direct in-container inference is the alternative recorded in
context.md; it requires a separate dependency and reproducibility decision.

## Reuse and proposed boundaries

Paths in this table are relative to `algo-suite/`. New modules are proposals,
not claims that those files exist today.

| Component | Existing integration point | Change |
| --- | --- | --- |
| Pattern contracts/catalog | `algo-backtest/src/algo_backtest/perception/candlestick.py` | Retain legacy implementation; add separate immutable evidence and expanded detector modules. |
| Context/sequence | New pure modules in `perception/` | Evaluate only available closed bars; keep geometry separate from confirmation. |
| Decision policy | `algo-backtest/src/algo_backtest/chain/filters/f3_pattern.py` | Explicit legacy/advisory/required-entry configuration. |
| Native signal production | `algo-backtest/src/algo_backtest/chain/market_signals.py` | Shared producer and independently scoped state per stream. |
| Compatibility | `algo-backtest/src/algo_backtest/signal_contract.py` | Hash the complete resolved signal contract, not only detector name. |
| F7 feature encoding | `algo-backtest/src/algo_backtest/chain/filters/f7_meta_learner.py` | Versioned ordered pattern/context features; retain old encoding. |
| Training rows | `algo-backtest/src/algo_backtest/training.py` | Consume identical evidence with identical availability times. |
| Recording | `algo-backtest/src/algo_backtest/chain/decision_recorder.py` | Serialize evidence independently of recommendation/action. |
| Analysis ingestion | `algo-analyze/src/algo_analyze/resultsdb/decisions.py` | Additive, versioned ingestion; historical omissions remain null. |
| Viewer | `algo-viewer/src/model/patterns.ts`, `algo-viewer/src/views/TradeDrawer.tsx` | Catalog metadata and explicit decision evidence. |
| Learned provider | New optional `algo-backtest/src/algo_backtest/candle_learning/` package | Label validation, training, inference, evaluation and cache preparation outside pure numerical modules. |

## Evidence contract

An observation carries schema/catalog versions, pair, UTC close, timeframe,
history count, provider status and stable ordered pattern hits. Each hit records
ID, polarity (including neutral), rule version and its own readiness status.
Overall readiness must not hide a short-lookback hit while a longer recognizer
warms up. Context fields include readiness, EMA(8), configured stochastic
definition, causal trend/level evidence, and normalized distance where defined.

Exact stochastic smoothing, level proximity, trend lookback, gap definition,
kicker correspondence and equality boundaries are T1 outputs, not implied by
the names. Do not equate a TA-Lib function with an author's definition without
boundary examples. The maximum history proposal is 256 bars; reject configurations
requiring more and never silently shorten a window.

Configuration separates detector mode, enabled catalog, context parameters,
sequence rules, decision policy, and provider. Canonical serialization and a
versioned hash cover these fields plus feature order and learned-artifact identity.
Old artifacts without these fields use only the explicit legacy compatibility
path; they cannot be admitted to a new feature schema.

## Timing and state

Validate a complete bar before advancing any recognizer. Duplicate, reversed,
non-UTC, malformed or incomplete observations fail explicitly. Scheduled market
closures are not fabricated candles; the manifest records the calendar policy.
Unexplained missing expected bars invalidate the stream. Confirmation refers to
the next valid closed bar under that policy, never a future open retrospectively.

For the initial sequence: IDLE -> doji candidate -> confirmed or expired at the
next closed bar. Confirmation belongs to the later bar. A bar may expire an old
candidate and create a new one, but cannot confirm itself. Opposing simultaneous
signals remain visible and cannot satisfy an exactly-one-direction entry rule.

All feature values have an availability timestamp. Offline labels may use a
future outcome for evaluation, but that outcome and its horizon never enter the
input at the earlier decision time. Prefix invariance tests enforce this boundary.

## Policy and risk separation

Legacy mode preserves existing six-label behavior. Advisory mode can recommend
or abstain but never veto. Required mode grants entry eligibility only to one
confirmed direction satisfying registered context; warmup, neutral-only and
conflicting evidence reject entry with distinct reasons.

Entry eligibility must not bypass F5/F6 or interrupt existing protective order
management. Native integration must test a held position while new entries are
vetoed. No Bigalow-inspired exit orders or stop changes are part of this slice.
If the current callback order cannot preserve protection, stop for design review
before enabling required mode; do not silently widen the risk-policy scope.

## Learned provider and artifact lifecycle

Laya is an experimental context classifier, not an established candlestick
oracle. T17 must verify the pinned upstream loading/schema interface and license
before implementation; this plan does not invent an API or assume llama.cpp
support. Model weights may require preparation-time downloads, never replay-time
network access. Keep optional dependencies out of the default LEAN runtime.

Reviewed labels, weak rule labels and ambiguous exclusions have separate
provenance. Split chronologically with purging of overlapping input windows and
outcome horizons. Fit preprocessing on train only and calibration on the reserved
calibration set. Do not tune on the final test set. Register a trial budget first.

The input serialization is versioned and bounded. Token overflow is an error,
not truncation. Unknown labels, non-finite probabilities, extra fields or invalid
schema fail validation. Repeatability means identical labels and the specified
probability tolerance in a pinned environment, not universal bitwise determinism.

Cache identity includes pair, timeframe, bar close, window hash, model/tokenizer/
schema/calibration hashes and preprocessing version. Prepare in a temporary
artifact, validate, then atomically publish; identical reuse is allowed, conflicting
content is rejected. No automatic deletion or overwriting of old artifacts.
Require complete preflight coverage before backtest startup. Runtime corruption
must produce a failed-run record, never a fallback signal. This backtest-only
failure behavior is not a live-position recovery design.

## Experiments and reporting

Register exact windows, costs, seeds, thresholds, trial budget and feasible
inference settings before launching. Compare legacy, expanded geometry,
geometry-plus-context, then optional learned context under the same other
filters. Quote activity is a separately registered factor, not a bundled change.
Use recognition metrics (per-label precision/recall, coverage and calibration)
separately from cost-adjusted return, drawdown and trade-count metrics.

Report every attempt with all resolved filter settings, including disabled
filters, dataset/config/code/model hashes, failures and exclusions. Modern-model
evaluation on old market data is retrospective; input-window purging alone does
not establish that upstream pretraining was free of historical contamination.
No book anecdote, accuracy score or profitable backtest authorizes live trading.

## Verification and rollout

Use Gherkin-first tests alongside each component, frozen legacy fixtures,
synthetic boundary fixtures, prefix invariance and native/offline parity. Extend
the existing architecture/coverage/CRAP/mutation gates to the new pure modules.
Viewer acceptance tests cover both old and new artifacts and a detection whose
direction differs from the final action. Synthetic data proves mechanics only.

The first rollout ends with rules and report integration. Learned-context work
can stop at a documented negative feasibility result; it must not manufacture
labels or weaken thresholds to continue. Re-scope unperformed downstream tasks
explicitly if that happens. Final completion requires the skill's independent
Verifier and discrimination sensor, after implementation is separately authorized.
