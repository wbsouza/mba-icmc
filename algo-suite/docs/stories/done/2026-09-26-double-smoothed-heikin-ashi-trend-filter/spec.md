# Spec 04k — algo-backtest: Double-Smoothed Heikin-Ashi Trend Filter as an F1 ablation candidate (lane of Spec 04)

> **Completed 2026-09-26, including the PR #43 training/parity follow-up.**
> Offline DSHA reads the same config and is verified against real LEAN; the prior
> TD-62 deferral is superseded. The implementation lives in `algo_backtest/perception/`
> and integrates through the shared `engine/chain_algorithm.py`. It follows
> QuantConnect's manual `PythonIndicator` standard. The exact source classifier
> (including tie-as-down) and MT4 period2=2 are preserved. `baseline-dsha` selects
> the alternative while sharing baseline's frozen EMA-trained F7 model. See
> `ablation/README.md`, `validation.md` and `lessons-learned.md` for measured evidence.
> The package `make check` passes; the root workspace gate retains the unrelated
> pre-existing TD-55 lint blocker. Historical planning/background notes below are
> retained as the original rationale; their "not started" statements are superseded.


> **Naming (2026-09-26):** this candidate was previously called "HAS/JapaDragon" after fx-manager's
> internal codenames. Renamed to **Double-Smoothed Heikin-Ashi Trend Filter** — an intention-revealing
> name (Clean Code: a name should say what the thing does, not what someone once called it) that
> describes the actual technique (pass-1 Wilder-smoothed OHLC → Heikin-Ashi transform → pass-2
> LWMA-smoothed output), not a private codename meaningless to a reader with no fx-manager history.
> `outerHAS.mq4`/`hasTrend.mq4`/`japaDragonBasedIndicator`/`japaDragonStrategy04` etc. below are
> **citations to the real historical source files and config beans** — those proper nouns are kept
> verbatim because they identify exactly what was read as evidence, not because they're good names
> to carry forward into new code. Suggested identifiers for implementation: class
> `DoubleSmoothedHeikinAshiTrend`, config selector value `perception_source: double_smoothed_heikin_ashi`.

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` for full context;
governing contract `specs.md` §14 (fx-manager port map) and §11.3.2 (F1's feature contract).
**Depends on:** Spec 04c (F1 exists, done) for the feature-key contract this feeds; genuinely
independent of Spec 04i/04j (disjoint files).
**Blocks:** nothing — this is an *additional* candidate for F1's still-unbuilt perception layer
(04a/04h), not a replacement for the planned EMA/ADX default. Per the user's explicit choice: "add
as second candidate, compare via ablation," not "replace the default."
**Order:** standalone; can start any time, but is naturally sequenced after whichever story first
builds a real perception layer for F1 (04a/04h), since this reuses that same integration point.
**Boundary:** the `algo_backtest/perception/` package (§5), F1's
config schema (adding a `perception_source` selector), and `algo-analyze`'s existing ablation
machinery (wiring only, not new ablation infrastructure).

## 1. Background — what this is and where it came from

> **Update 2026-09-26 (Spec 04h landed, so part of this background is out of date).** A default
> perception layer for F1 now exists. `algo-backtest/src/algo_backtest/chain/wiring.py`'s
> `price_features()` fills `trend_direction` (sign of EMA(3) minus EMA(8)), `trend_strength` (an
> EMA-gap proxy, not ADX) and `higher_tf_trend_direction` (sign of price minus EMA(60)) from live
> LEAN indicators in `algos/{baseline,hybrid}/main.py`. The offline F7 training path uses the
> same function. The "no real implementation populating them yet" statement below (and in
> `f1_trend.py`'s docstring) was true when written and is no longer. That module is this
> candidate's natural integration point: §5's third open question now has a concrete default
> shape to match. Completion resolved the location as `algo_backtest/perception/`
> and added the `perception_source` selector described above.

> **Update 2026-09-26 (formula fully confirmed against fx-manager's actual MetaTrader source,
> `related-work/projects/fx-manager/metatrader/experts/indicators/`).** §2 and §5 below were
> written against `outerHAS.mq4`/`hasTrend.mq4` alone, with the exact classification rule flagged
> as an unconfirmed reconstruction (open question 1) because the sibling indicator computing it
> wasn't on hand. It is now: `Heiken_Ashi_Smoothed.mq4` (the shared engine both `outerHAS.mq4` and
> the plain-chart `Heiken Ashi Smoothed.mq4` indicator call into) and `trendMtfHasB1.mq4` (the real
> "B1" classifier — a real file, not lost) are both in that checkout. §2 and §5 are rewritten below
> against their actual source, not a reconstruction.

`algo_backtest/chain/filters/f1_trend.py` decides BUY/SELL/veto from three feature keys
(`trend_direction`, `trend_strength`, `higher_tf_trend_direction`) but has **no real
implementation populating them yet** — its own docstring says so: "No upstream perception layer
populates `ExecutionState.features` from real LEAN indicators yet." This spec proposes one
concrete, evidence-backed candidate implementation for `trend_direction`/`higher_tf_trend_direction`
(not `trend_strength`, which is ADX-style and unrelated to this technique).

The candidate: fx-manager's `Heiken_Ashi_Smoothed.mq4` (header comment: "mod by Raff", sourced from
forex-tsd.com, 2006) computes a **double-smoothed Heikin-Ashi** signal, reused at a higher timeframe
by `outerHAS.mq4`/`hasTrend.mq4` and classified up/down by `trendMtfHasB1.mq4`. `spockfx-engine`'s
config (`dragon.xml`'s `japaDragonBasedIndicator`, params `method=2, period=6, method2=3,
period2=1`) confirms the same technique was carried forward into the later Spring/Java rewrite with
matching pass-1 parameters (`period2` differs — resolved in §5, not left open). This was a real,
production-traded signal on both systems, and the entry/against-trend toggle
(`OpenByArrowOrder.DirectionType`, `dragon.xml`'s `japaDragonEntryDetectorAgainstTrend` variant)
is the code-level fossil of the user's own recollection: "going against the trend was always a
terrible decision" — the against-trend variant was built and configured but not what production
ran.

## 2. The formula, precisely

Confirmed directly against `related-work/projects/fx-manager/metatrader/experts/indicators/
Heiken_Ashi_Smoothed.mq4` (the shared engine) and `trendMtfHasB1.mq4` (the classifier) — not
reconstructed.

**Pass 1 + Heikin-Ashi transform** (`Heiken_Ashi_Smoothed.mq4::start()`), per bar `pos`, on whatever
timeframe the indicator is attached to (the primary chart for `trend_direction`; a higher timeframe,
via `outerHAS.mq4`'s array-copy resampling, for `higher_tf_trend_direction`):

1. `maOpen/maClose/maLow/maHigh = SMMA(period=MaPeriod=6)` of that timeframe's raw
   Open/Close/Low/High (`iMA(..., MaMetod=2, ...)` — MQL method code `2` is SMMA/Wilder smoothing).
2. `haClose = (maOpen + maHigh + maLow + maClose) / 4`.
3. `haOpen = (prevHaOpen + prevHaClose) / 2` — the *previous bar's* pass-1 `haOpen`/`haClose`
   (pre-pass-2 smoothing), not the previous bar's raw price.
4. `haHigh = max(maHigh, haOpen, haClose)`; `haLow = min(maLow, haOpen, haClose)`.
5. **Direction-reordered body-extreme pair** (this is the detail the original reconstruction
   missed, see §5's resolved question 1): if `haOpen < haClose` (this bar's raw HA candle is
   bullish), store `(near, far) = (haLow, haHigh)`; otherwise store `(near, far) = (haHigh, haLow)`.
   `near`/`far` here are this spec's own naming for the two series MQL calls `ExtMapBuffer7`/
   `ExtMapBuffer8` — the code has no descriptive name for them.

**Pass 2 — smooth four series with `LWMA(period=MaPeriod2)`** (MQL method code `3`,
`iMAOnArray(..., MaMetod2=3, ...)`), each over its own accumulated history:

- `smoothedNear = LWMA(near)`, `smoothedFar = LWMA(far)` — the direction-reordered pair from step 5.
- `smoothedOpen = LWMA(haOpen)`, `smoothedClose = LWMA(haClose)` — the *un-reordered* pass-1 HA
  open/close from steps 2–3.

All four are exposed as `Heiken_Ashi_Smoothed`'s indicator buffers 0–3 respectively
(`SetIndexBuffer(0, smoothedNear)`, `1 → smoothedFar`, `2 → smoothedOpen`, `3 → smoothedClose`).

**Classification** (`trendMtfHasB1.mq4`, confirmed byte-exact — not inferred): reads buffer **1**
(`smoothedFar`) and buffer **0** (`smoothedNear`) — *not* buffers 2/3 (`smoothedOpen`/`smoothedClose`)
— despite the caller locally naming its two variables `haOpen`/`haClose`; that naming in
`trendMtfHasB1.mq4` is misleading and does not mean what it says. The exact rule:

```
down  when smoothedFar >= smoothedNear   (buffer 1 >= buffer 0)
up    otherwise
```

Because the tie (`==`) case is folded into **down**, this is not a symmetric `>`/`<` split: a flat
reading classifies as down, never as a distinct "neutral".

**Decision (2026-09-26): port `>=` byte-exact, do not add an ABSTAIN-on-tie branch.** Checked every
sibling B-family file (`mtfHasB1.mq4`, `hasGridB1.mq4`, `trendHas.mq4`) — all use the identical
unremarked `>=` with no comment anywhere justifying it as a trading rule; it reads as the original
author's unexamined default, not a considered decision. On continuously-moving real price the tie
is effectively unreachable; it is reachable on an extended flat/no-movement stretch, but there is no
evidence an ABSTAIN state there is better *or* worse than the ported default — deciding that needs a
real ablation comparison, not another guess, and this thesis is scoped to defense first. Tracked as
**TD-61**: implement and empirically compare an ABSTAIN-on-tie variant after the defense, not now.

`hasTrend.mq4` (the trend-gate half) runs `trendMtfHasB1.mq4` at a **configurable higher timeframe**
(`level` index into `periods[] = {1,5,15,30,60,240,1440,10080,43200}` minutes) and exposes up/down —
this is the `higher_tf_trend_direction` input. **Known MT4-side bug, do not replicate:**
`hasTrend.mq4` classifies *any* non-exact match to its down-sentinel value as up — including
`EMPTY_VALUE`/`0.0` on a bar that hasn't warmed up yet. A bar with insufficient history is
misclassified as "up" in the original, rather than reporting "not ready". This is exactly the
warm-up hazard §4's Gherkin scenario (and this workspace's fail-fast policy) exists to catch in the
port — abstain/report-not-ready on warm-up, don't reproduce MT4's default-to-up behavior.

`trend_direction` (primary timeframe) runs the identical pipeline at the trading timeframe, per
`Heiken_Ashi_Smoothed.mq4` directly (no higher-timeframe resampling needed).

## 3. Why this maps cleanly onto LEAN — confirmed against LEAN's own source, not assumed

Checked directly against `QuantConnect/Lean` on GitHub (not assumed from the MQL side):

- **`Indicators/HeikinAshi.cs`**: `HA_Close=(O+H+L+C)/4`, `HA_Open=(prev HA_Open+prev
  HA_Close)/2`, `HA_High/Low=max/min(raw,HA_Open,HA_Close)` — the *same* transform as §2 steps 2–4
  above, structurally. LEAN's built-in `HeikinAshi` indicator takes a raw bar as input, though —
  it cannot be pointed at an already-smoothed synthetic OHLC series without either (a) feeding it
  synthetic bar objects built from the pass-1 smoothed values, or (b) reimplementing the transform
  directly against the smoothed series (simpler, and this transform is short enough that
  reimplementing it doesn't sacrifice correctness or reviewability).
- **`Indicators/MovingAverageType.cs`**: has `Wilders` and `LinearWeightedMovingAverage` as native
  types — the exact equivalents of MQL4's method codes `2` (SMMA/Wilder) and `3` (LWMA) used by
  pass 1 and pass 2 respectively. **Use LEAN's native `WilderMovingAverage`/
  `LinearWeightedMovingAverage` indicator classes for both smoothing passes** — do not hand-roll
  a pandas/numpy reimplementation of Wilder smoothing or LWMA; LEAN's own tested indicators are
  the correct dependency here, and matching LEAN's own moving-average semantics (warm-up,
  `IsReady`, rolling-window bookkeeping) is exactly what should be inherited rather than
  reinvented. The offline training exception in §4 step 5 reproduces these
  semantics in host Python and must be verified against the native implementation.
- **Higher-timeframe consolidation**: LEAN's `TradeBarConsolidator` + `RegisterIndicator` (or the
  `consolidate()`/`Resolution` helpers) is the native mechanism for "run an indicator on a coarser
  bar than the subscription resolution" — the direct LEAN-idiomatic replacement for
  `outerHAS.mq4`'s `ArrayCopySeries(..., outerPeriod)` resampling.

**Why this might still legitimately diverge from the original MT4 numbers** (the user's own
caution — "remember that the behaviour of MetaTrader and LEAN might be different" — given concrete
substance here, not left as a vague caveat):
- MQL4's `iMAOnArray` recomputes over a full historical array each call, indexed from the most
  recent bar backwards; LEAN's indicators are streaming/rolling-window, updated forward one bar at
  a time via `IndicatorDataPoint`s. Both converge to the same steady-state value once enough bars
  have been seen, but **warm-up-period edge behavior will differ** — the first `period1+period2`
  or so bars of any backtest will not numerically match what MT4 would have shown at the
  equivalent point, and that is expected, not a bug to chase.
- MT4 bar-close timing (`iTime`, weekend/session gap handling) and LEAN's consolidator bar-close
  timing may bucket boundary ticks differently at session edges — a source of small, structural
  disagreement at higher-timeframe bar boundaries specifically (this indicator's whole mechanism
  depends on higher-timeframe bar closes), not something to try to eliminate, only to be aware of
  when comparing ablation results against any historical MT4-era track record.

## 4. Implementation plan

1. Build the pass-1/HA-transform/pass-2 pipeline as LEAN indicator composition (native
   `WilderMovingAverage` + `LinearWeightedMovingAverage`, hand-written HA transform + the
   direction-reordered near/far pair from §2 step 5 between them) registered against a
   `TradeBarConsolidator` at the configured higher timeframe.
2. Expose `trend_direction` (primary-timeframe instance of the same pipeline) and
   `higher_tf_trend_direction` (higher-timeframe instance) as the two F1 feature keys this
   candidate populates — `trend_strength` is out of scope for this candidate (ADX-style, unrelated
   technique; whatever perception-layer story eventually builds the EMA/ADX default candidate
   presumably supplies it, and F1 doesn't require both keys from the same source).
3. Add a `perception_source` (or similarly-named) config selector so a strategy config can choose
   this candidate (suggested value: `double_smoothed_heikin_ashi`) instead of the eventual default,
   per the user's "second candidate, not a replacement" decision.
4. Wire both candidates through `algo-analyze`'s existing ablation-table machinery (already built,
   `docs/stories/done/2026-09-24-ablation-table`) — no new ablation infrastructure needed, just a
   second config variant to run through it.
5. **Train/serve parity — required in this implementation (PR #43).** Read the
   same resolved strategy perception config in offline training and live execution.
   Add a host-importable Wilder → HA → LWMA pipeline and closed-bar higher-timeframe
   aggregation for `training.py`. Match native seeding, midpoint OHLC, readiness,
   session gaps and fill-forward behavior. Prove matching decision timestamps and
   features against real LEAN for the default and overridden periods/timeframes.
   The existing frozen EMA-trained-model ablation remains a separate experiment;
   implementing DSHA training features does not silently replace its model.
   Baseline/hybrid keep EMA when the selector is absent. Exact ties remain down
   per §2; ABSTAIN is not implemented and stays deferred in TD-61.
6. Gherkin scenarios (per this repo's Gherkin-only rule): the HA-transform math against known
   input/output pairs (hand-computed, same style as `trail_stop.feature`), the §2 classification
   rule's tie-handling (`smoothedFar >= smoothedNear` → down, ported byte-exact per the §2 decision
   — TD-61 tracks the deferred ABSTAIN-on-tie alternative), and a warm-up-period scenario asserting
   the filter correctly reports "not ready"/abstains rather than emitting a wrong-but-plausible
   value before enough bars have accumulated (fail-fast policy — and unlike `hasTrend.mq4`'s own
   bug, see §2).

## 5. Resolved implementation decisions

- **~~The exact classification rule~~ — RESOLVED (2026-09-26).** `trendMtfHasB1.mq4` is in the
  checkout (`related-work/projects/fx-manager/metatrader/experts/indicators/trendMtfHasB1.mq4`) and
  its rule is byte-exact, not inferred: down when `smoothedFar >= smoothedNear` (its own buffers 1
  and 0), up otherwise. See §2. **Tie-handling decided too:** port `>=` byte-exact (fold tie into
  down), do not add an ABSTAIN branch now — no sibling B-family file documents a trading rationale
  for the tie case, and there is no evidence ABSTAIN would be better or worse without an actual
  ablation run. Tracked as **TD-61** for a post-defense empirical comparison.
- **~~`spockfx-engine`'s `period2=1` vs MQL's `MaPeriod2=2`~~ — RESOLVED (2026-09-26).** Both values
  are now confirmed from primary sources, not guessed: `Heiken_Ashi_Smoothed.mq4`'s own `extern int
  MaPeriod2 = 2` default (the original, human-authored MQL source, not decompiled) is `2`;
  `spockfx-engine`'s `indicator.xml` (`japaDragonBasedIndicator` bean, real hand-authored Spring
  config, also not decompiled) explicitly overrides it to `period2=1` for whatever the Java engine
  actually ran in production. This is a genuine, deliberate parameter difference between the two
  systems — not a decompilation artifact (no decompiled source was involved in either value).
  **Decision: use `2`, the original MQL default**, since this port's reference is `outerHAS.mq4`/
  `hasTrend.mq4`/`trendMtfHasB1.mq4` (the MT4 side), and document that spockfx-engine's Java
  rewrite deliberately ran `period2=1` instead, as a fact about that other system, not this port.
- **Module location — RESOLVED.** `algo_backtest/perception/` separates pure formula/config
  from native LEAN adapters. `engine/chain_algorithm.py` integrates both sources. The
  custom indicator is `DoubleSmoothedHeikinAshiTrend`.

## Definition of done

- Double-Smoothed-Heikin-Ashi-based `trend_direction`/`higher_tf_trend_direction` implementation
  built on LEAN's native `WilderMovingAverage`/`LinearWeightedMovingAverage`, not a hand-rolled
  reimplementation, live/backtest side.
- Config-selected offline DSHA features and real LEAN train/serve parity (§4 step 5).
  Preserve the shared frozen model for the existing input-ablation experiment.
- Config-selectable alongside (not replacing) the default perception source.
- Wired through the existing ablation-table machinery; at least one ablation run comparing both
  candidates exists.
- Tie folds into down, ported byte-exact (§2/§5); TD-61 filed for the deferred ABSTAIN-on-tie
  comparison. The `period2=2` choice is documented. The module-location open question is resolved.
- `make check` green.
- Move to `docs/stories/done/<YYYY-MM-DD>-double-smoothed-heikin-ashi-trend-filter/` with
  `lessons-learned.md`.
