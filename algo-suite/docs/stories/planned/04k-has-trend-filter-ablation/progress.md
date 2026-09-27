# Progress — Spec 04k (HAS/JapaDragon MTF trend filter, F1 ablation candidate)

- [ ] Pass-1 Wilder smoothing + HA transform + pass-2 LWMA smoothing pipeline built on LEAN's
      native `WilderMovingAverage`/`LinearWeightedMovingAverage` indicators
- [ ] Higher-timeframe consolidation via `TradeBarConsolidator`/`RegisterIndicator`
- [ ] `trend_direction`/`higher_tf_trend_direction` feature keys populated for F1
- [ ] `perception_source` config selector added (this candidate alongside, not replacing, default)
- [ ] Wired through existing ablation-table machinery; at least one comparison run
- [ ] §5's two open questions resolved and documented
- [ ] `make check` green
- [ ] `lessons-learned.md` written, story moved to `docs/stories/done/`

**Status 2026-09-26: not started.** No HAS/Heikin-Ashi, `WilderMovingAverage`,
`LinearWeightedMovingAverage` or `perception_source` code exists in `algo-backtest`. The default
EMA-based F1 feature source it would be compared against now exists (`chain/wiring.py`,
Spec 04h). See the dated note in `spec.md` §1.
