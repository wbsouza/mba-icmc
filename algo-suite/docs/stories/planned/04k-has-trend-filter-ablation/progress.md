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
