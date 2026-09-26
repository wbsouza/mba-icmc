# Spec 04k — algo-backtest: HAS/JapaDragon MTF trend filter as an F1 ablation candidate (lane of Spec 04)

**Parent spec:** `04-algo-backtest-filter-chain-hybrid` — read its `spec.md` for full context;
governing contract `specs.md` §14 (fx-manager port map) and §11.3.2 (F1's feature contract).
**Depends on:** Spec 04c (F1 exists, done) for the feature-key contract this feeds; genuinely
independent of Spec 04i/04j (disjoint files).
**Blocks:** nothing — this is an *additional* candidate for F1's still-unbuilt perception layer
(04a/04h), not a replacement for the planned EMA/ADX default. Per the user's explicit choice: "add
as second candidate, compare via ablation," not "replace the default."
**Order:** standalone; can start any time, but is naturally sequenced after whichever story first
builds a real perception layer for F1 (04a/04h), since this reuses that same integration point.
**Boundary:** a new indicator/perception module (exact location TBD, see §5 open question), F1's
config schema (adding a `perception_source` selector), and `algo-analyze`'s existing ablation
machinery (wiring only, not new ablation infrastructure).

## 1. Background — what this is and where it came from

`algo_backtest/chain/filters/f1_trend.py` decides BUY/SELL/veto from three feature keys
(`trend_direction`, `trend_strength`, `higher_tf_trend_direction`) but has **no real
implementation populating them yet** — its own docstring says so: "No upstream perception layer
populates `ExecutionState.features` from real LEAN indicators yet." This spec proposes one
concrete, evidence-backed candidate implementation for `trend_direction`/`higher_tf_trend_direction`
(not `trend_strength`, which is ADX-style and unrelated to this technique).

The candidate: fx-manager's `outerHAS.mq4`/`hasTrend.mq4` (a custom MetaTrader indicator, part of
a "JapaDragon"/"HAS" family — `Heiken Ashi Smoothed`) computes a **double-smoothed Heikin-Ashi**
signal on a higher timeframe than the trading chart, and `spockfx-engine`'s config
(`dragon.xml`'s `japaDragonBasedIndicator`, params `method=2, period=6, method2=3, period2=1`)
confirms the same technique was carried forward into the later Spring rewrite with matching
smoothing parameters (period2 differs by one, `1` vs MQL's `2` — not reconciled, see §5). This was
a real, production-traded signal on both systems, and the entry/against-trend toggle
(`OpenByArrowOrder.DirectionType`, `dragon.xml`'s `japaDragonEntryDetectorAgainstTrend` variant)
is the code-level fossil of the user's own recollection: "going against the trend was always a
terrible decision" — the against-trend variant was built and configured but not what production
ran.

## 2. The formula, precisely

`outerHAS.mq4`, per-bar, on the higher timeframe (`outerPeriod`, e.g. H4):

1. **Pass 1 — smooth the raw OHLC**: `maOpen/maHigh/maLow/maClose = SMMA(period=6)` of the higher
   timeframe's raw Open/High/Low/Close. MQL4's `iMA` method code `2` is SMMA (smoothed moving
   average) — mathematically Wilder's smoothing method, not a plain SMA.
2. **Heikin-Ashi transform** on the *smoothed* OHLC (not the raw OHLC — this is the detail a naive
   "just use LEAN's `HeikinAshi` indicator directly" approach would miss):
   `haClose = (maOpen+maHigh+maLow+maClose)/4`; `haOpen = (prev_haOpen+prev_haClose)/2`;
   `haHigh/haLow = max/min(smoothed extreme, haOpen, haClose)`.
3. **Pass 2 — smooth the HA output**: run `LWMA(period=2)` (MQL method code `3`) over each of the
   four HA buffers (open/high/low/close) produced by step 2.
4. **Direction**: bullish when the twice-smoothed `haClose > haOpen` (inferred — the exact
   threshold rule lives in a sibling "B"-variant indicator whose source is not in this checkout;
   see §5).

`hasTrend.mq4` (the trend-gate half) runs the *same* pipeline on a **configurable higher
timeframe** (`level` index into `periods[] = {1,5,15,30,60,240,1440,10080,43200}` minutes) and
exposes up/down as a step function — this is the `higher_tf_trend_direction` input.
`trend_direction` (primary timeframe) would run the identical pipeline at the trading timeframe.

## 3. Why this maps cleanly onto LEAN — confirmed against LEAN's own source, not assumed

Checked directly against `QuantConnect/Lean` on GitHub (not assumed from the MQL side):

- **`Indicators/HeikinAshi.cs`**: `HA_Close=(O+H+L+C)/4`, `HA_Open=(prev HA_Open+prev
  HA_Close)/2`, `HA_High/Low=max/min(raw,HA_Open,HA_Close)` — the *same* transform as step 2
  above, structurally. LEAN's built-in `HeikinAshi` indicator takes a raw bar as input, though —
  it cannot be pointed at an already-smoothed synthetic OHLC series without either (a) feeding it
  synthetic bar objects built from the pass-1 smoothed values, or (b) reimplementing the four-line
  transform directly against the smoothed series (simpler, and this transform is short enough that
  reimplementing it doesn't sacrifice correctness or reviewability).
- **`Indicators/MovingAverageType.cs`**: has `Wilders` and `LinearWeightedMovingAverage` as native
  types — the exact equivalents of MQL4's method codes `2` (SMMA/Wilder) and `3` (LWMA) used by
  pass 1 and pass 2 respectively. **Use LEAN's native `WilderMovingAverage`/
  `LinearWeightedMovingAverage` indicator classes for both smoothing passes** — do not hand-roll
  a pandas/numpy reimplementation of Wilder smoothing or LWMA; LEAN's own tested indicators are
  the correct dependency here, and matching LEAN's own moving-average semantics (warm-up,
  `IsReady`, rolling-window bookkeeping) is exactly what should be inherited rather than
  reinvented.
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
   `WilderMovingAverage` + `LinearWeightedMovingAverage`, hand-written 4-line HA transform between
   them) registered against a `TradeBarConsolidator` at the configured higher timeframe.
2. Expose `trend_direction` (primary-timeframe instance of the same pipeline) and
   `higher_tf_trend_direction` (higher-timeframe instance) as the two F1 feature keys this
   candidate populates — `trend_strength` is out of scope for this candidate (ADX-style, unrelated
   technique; whatever perception-layer story eventually builds the EMA/ADX default candidate
   presumably supplies it, and F1 doesn't require both keys from the same source).
3. Add a `perception_source` (or similarly-named) config selector so a strategy config can choose
   this HAS-based candidate instead of the eventual default, per the user's "second candidate, not
   a replacement" decision.
4. Wire both candidates through `algo-analyze`'s existing ablation-table machinery (already built,
   `docs/stories/done/2026-09-24-ablation-table`) — no new ablation infrastructure needed, just a
   second config variant to run through it.
5. Gherkin scenarios (per this repo's Gherkin-only rule): the HA-transform math against known
   input/output pairs (hand-computed, same style as `trail_stop.feature`), and a warm-up-period
   scenario asserting the filter correctly reports "not ready"/abstains rather than emitting a
   wrong-but-plausible value before enough bars have accumulated (fail-fast policy).

## 5. Open questions — do not guess past these, resolve at implementation time

- **The exact "B"-variant threshold/classification rule is not in this checkout.** Only
  `outerHAS.mq4` (the full pipeline) and `hasTrend.mq4` (which calls a sibling `trendMtfHasB1`
  indicator via `iCustom`, source not present) are available. §2 step 4's "bullish when
  `haClose > haOpen`" is the best available reconstruction from the shared HA-transform logic, not
  a confirmed byte-exact rule — flag this honestly in the implementation's docstring, the way
  `trail_stop.py` used to (and got corrected once better evidence turned up) — don't repeat that
  mistake by stating this as fact.
- **`spockfx-engine`'s `period2=1` vs MQL's `MaPeriod2=2`** — one bar's difference in the second
  smoothing pass's period, not reconciled. Could be a real parameter tune between the two systems,
  or a typo/decompilation artifact (spockfx-engine's source here is Procyon-decompiled, not
  original). Pick one, document the choice, don't silently average or guess a third value.
- **Exact module location for this perception-layer code** — no `perception/` package exists yet
  in `algo_backtest`; decide at implementation time whether this lives alongside F1, in a new
  package, or as part of whatever 04a/04h's real indicator wiring introduces for the EMA/ADX
  default, so the two candidates share a consistent integration shape.

## Definition of done

- HAS-based `trend_direction`/`higher_tf_trend_direction` implementation built on LEAN's native
  `WilderMovingAverage`/`LinearWeightedMovingAverage`, not a hand-rolled reimplementation.
- Config-selectable alongside (not replacing) the default perception source.
- Wired through the existing ablation-table machinery; at least one ablation run comparing both
  candidates exists.
- The two open questions in §5 resolved and documented (not silently guessed past).
- `make check` green.
- Move to `docs/stories/done/<YYYY-MM-DD>-has-trend-filter-ablation/` with `lessons-learned.md`.
