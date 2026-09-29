# Story 14 — news-only strategy (registered 2026-09-28 05:40 UTC, before any outcome)

## Question

Does the news signal alone, with the same risk guard and money management as the price chain,
carry any directional edge? This is the cleanest test of the thesis question: no price filter is
in the loop, so the comparison against the price-only baseline and the price+news hybrid isolates
the news family.

## Design

- Chain: `f4_news_context → f5_risk_guard → f6_capital_mgmt → f7_meta_learner`; F1/F2/F3 absent.
- Signal: F7 trained on the news family only (`meta_learner.families: [news]`), i.e. the GDELT
  event-intensity feature at decision time (`news_event_intensity`; the lexicon sentiment half
  remains missing, TD-48). F4 vetoes when intensity ≤ −0.5.
- Money management and risk: the Heikin-Ashi H4 template values (risk 3 %, swing stop with 50 %
  cut, floor 5 pips, targets 4R/6R closing 50 % each, trail 2R → +0.1R, portfolio-at-risk 0.18,
  two concurrent trades, leverage 30); execution spread 1 pip, commission 0, `close_on_veto` false.
- Clocks: H1 (`news-only`) and H4 (`news-only-h4`), label horizon one bar.
- Splits: fit 2015-03-02..2015-12-31, combiner calibrated on January 2016, February 2016 held out.
- Thresholds: 0.55/0.45 registered; if the January validation band cannot reach them (as with the
  H1/H4 price models), symmetric quantile thresholds at 5 % and 10 % per side of the January
  distribution are used and reported as such — decided from the calibration JSON, never from a
  2016-03+ outcome.
- Simulation: one $10,000 account per cell, 2016-03-01..2016-12-31. Rank on March..October; read
  November and December last.
- Comparators, same clocks and splits: price-only baseline (`h1-candle-vol-off` / H4 talib-off
  cells) and hybrid (`h1-hybrid-vol-off` / H4 hybrid talib-off), already simulated.
- Rule-only arm (added 2026-09-28 06:05 UTC, before any cell ran): `news-rule` — F4 alone decides
  direction from the event-intensity reading (BUY at or above the January-2016 90 % quantile,
  SELL at or below the 10 % quantile, veto at ≤ −0.5), no F7; the chain terminates on F4. Both
  sign conventions are registered as cells because the mapping from cooperation/conflict to
  EUR/USD direction is not known a priori. Same money management, risk guard and clocks.
- Primary comparison: news-only vs price-only baseline at H1, paired daily equity on the two
  untouched months. Trial count for this story: 10 cells (news-only 2 clocks × 3 thresholds;
  news-rule 2 clocks × 2 signs).

## Out of scope

FinBERT / text sentiment (needs the GKG quotation export; separate story), any change to the
event feature, any post-hoc threshold change.
