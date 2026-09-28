# Story 14 progress

- [x] Trainer accepts a families subset that includes `news`; four-filter chain wires offline (feat/14-news-only-strategy, 872aa69..2000b7d, 1,541 scenarios green)
- [x] Bundled strategies `news-only` (H1) and `news-only-h4` with README, provenance resolves
- [x] Models trained (H1 4,739 rows, H4 1,030) and thresholds calibrated on January 2016 (band 0.525–0.529 / 0.5245–0.5265; `evidence/news-only-calibration-20260928T0545Z.json`)
- [x] Six news-only cells simulated 2016-03-01..2016-12-31 (job `2026-09-28-news-only`, 22:32–22:39 PT); `evidence/news-only-cells-20260928T0545Z.md` + parameters appendix. Result: fixed thresholds 0 trades; calibrated H1 −42.6/−38.5 %, H4 −22.1/−14.4 %; no cell positive in both untouched months.
- [x] Rule-only arm (news-rule, 4 cells) simulated 22:45–22:53 PT: sign +1 −47.0 % / −19.8 %; sign −1 (short-only in practice) +12.9 % H1 on 39 trades, +3.1 % H4 on 10, both positive in Nov and Dec; EUR/USD drift −3.4 % over the span is the confound. `evidence/news-cells-20260928T0600Z.md`
- [x] Chapter 4 paragraph (registration written 2026-09-28 before any outcome; news-only and rule-only results appended with the drift caveat)
- [x] Code PR #60 merged; docs on integrate/story-12-13
- [ ] Follow-up (not registered yet): matched short-only control for the sign −1 rule; a rising-euro window
