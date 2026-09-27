# Progress — Spec 04k (Double-Smoothed Heikin-Ashi trend filter, F1 ablation candidate)

- [ ] Pass-1 Wilder smoothing + HA transform + pass-2 LWMA smoothing pipeline built on LEAN's
      native `WilderMovingAverage`/`LinearWeightedMovingAverage` indicators
- [ ] Higher-timeframe consolidation via `TradeBarConsolidator`/`RegisterIndicator`
- [ ] `trend_direction`/`higher_tf_trend_direction` feature keys populated for F1
- [ ] `perception_source` config selector added (this candidate alongside, not replacing, default)
- [ ] Wired through existing ablation-table machinery; at least one comparison run
- [ ] §5's tie-handling decision, `period2` choice and module-location question resolved and documented
- [ ] `make check` green
- [ ] `lessons-learned.md` written, story moved to `docs/stories/done/`

**Status 2026-09-26: not started.** No Double-Smoothed-Heikin-Ashi, `WilderMovingAverage`,
`LinearWeightedMovingAverage` or `perception_source` code exists in `algo-backtest`. The default
EMA-based F1 feature source it would be compared against now exists (`chain/wiring.py`,
Spec 04h). See the dated notes in `spec.md` §1 — the formula and both of §5's original open
questions are now resolved against fx-manager's actual MetaTrader source (`trendMtfHasB1.mq4`,
`Heiken_Ashi_Smoothed.mq4`); only the module-location question and the implementation itself
remain.

**Renamed 2026-09-26** from "HAS/JapaDragon MTF trend filter" — the old name was fx-manager's
internal codename, not descriptive to a reader without that history. See `spec.md`'s naming note.
