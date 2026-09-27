# Progress — Spec 04k (Double-Smoothed Heikin-Ashi trend filter, F1 ablation candidate)

- [ ] Pass-1 Wilder smoothing + HA transform + pass-2 LWMA smoothing pipeline built on LEAN's
      native `WilderMovingAverage`/`LinearWeightedMovingAverage` indicators (live/backtest)
- [ ] Pure-Python offline reimplementation of the same pipeline for `training.py`, plus a
      `feature_parity.feature`-style scenario proving live/offline agreement (§4 step 5)
- [ ] Higher-timeframe consolidation via `TradeBarConsolidator`/`RegisterIndicator`
- [ ] `trend_direction`/`higher_tf_trend_direction` feature keys populated for F1
- [ ] `perception_source` config selector added (this candidate alongside, not replacing, default)
- [ ] Wired through existing ablation-table machinery; at least one comparison run
- [ ] Module-location open question resolved (tie-handling and `period2` are already decided, see spec.md §5)
- [ ] `make check` green
- [ ] `lessons-learned.md` written, story moved to `docs/stories/done/`

**Status 2026-09-26: not started.** No Double-Smoothed-Heikin-Ashi, `WilderMovingAverage`,
`LinearWeightedMovingAverage` or `perception_source` code exists in `algo-backtest`. The default
EMA-based F1 feature source it would be compared against now exists (`chain/wiring.py`,
Spec 04h). Formula and all of §5's original open questions are resolved against fx-manager's
actual MetaTrader source (`trendMtfHasB1.mq4`, `Heiken_Ashi_Smoothed.mq4`): classification rule
confirmed byte-exact, tie folds into down (ported as-is; ABSTAIN-on-tie deferred to TD-61,
post-defense), `period2=2` (MQL default) chosen over spockfx-engine's divergent `1`. Also found:
this candidate needs a parity-proven offline reimplementation for `training.py`, not just the
live/backtest LEAN indicators (`spec.md` §4 step 5) — bigger than the original plan assumed. Only
the module-location question and the implementation itself remain before this can move to `done/`.

**Renamed 2026-09-26** from "HAS/JapaDragon MTF trend filter" — the old name was fx-manager's
internal codename, not descriptive to a reader without that history. See `spec.md`'s naming note.
