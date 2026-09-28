# Story 14 progress

- [x] Trainer accepts a families subset that includes `news`; four-filter chain wires offline (feat/14-news-only-strategy, 872aa69..2000b7d, 1,541 scenarios green)
- [x] Bundled strategies `news-only` (H1) and `news-only-h4` with README, provenance resolves
- [x] Models trained (H1 4,739 rows, H4 1,030) and thresholds calibrated on January 2016 (band 0.525–0.529 / 0.5245–0.5265; `evidence/news-only-calibration-20260928T0545Z.json`)
- [x] Six news-only cells simulated 2016-03-01..2016-12-31 (job `2026-09-28-news-only`, 22:32–22:39 PT); `evidence/news-only-cells-20260928T0545Z.md` + parameters appendix. Result: fixed thresholds 0 trades; calibrated H1 −42.6/−38.5 %, H4 −22.1/−14.4 %; no cell positive in both untouched months.
- [ ] Rule-only arm (news-rule, 4 cells) — code in progress (F4 intensity rule, F7-less terminal)
- [x] Chapter 4 paragraph (registration written 2026-09-28 before any outcome; news-only results appended; rule arm pending)
- [ ] PR
