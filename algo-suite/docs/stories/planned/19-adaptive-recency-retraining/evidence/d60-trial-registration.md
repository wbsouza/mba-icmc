# 2026-09-28 D60 trial — 60-day training window refreshed every month (registered before any run; exploratory)

User proposal: "train on the 60 days before the trading interval, keep training as time passes, see if
it works better". Cheap trial with the existing tools, no engine change:

- For each month M of the trading year 2016-03..2017-02: fit the H1 and H4 price-only F7 models on the
  60 calendar days before M (family fit to M−8 days, combiner on M−7..M−3, held-out M−2..M−1, the
  trainer's own split), take the 10 %/90 % quantiles of the combiner's validation p̂ as the month's
  thresholds, and simulate month M alone from $10,000 with that model and those thresholds.
- Chain: monthly returns compounded into one curve; daily returns concatenated for the paired test.
  A position open at a month end is closed by the run's end, which the frozen comparator does not do;
  this is the trial's known bias and is reported, not corrected.
- Comparators: session-2 `h1-q10-base` and `h4-q10-base` (frozen 2015 model, January-2016 thresholds).
- Endpoints, all exploratory (the year has been viewed; the monthly pre-check chose the window):
  1. prediction quality per month on the decision bars (hit rate of p̂ > 0.5, log-loss, hit on the cut bars);
  2. chained year return and the month table;
  3. paired daily returns D60 minus frozen on the untouched months Nov–Feb (block 4/2, 999, seed 42)
     and on the year (block 5/3).
- Cells: 12 months × 2 clocks = 24 runs, 24 fits. Same costs, risk guard and Heikin-Ashi H4 plan as
  session 2. Row counts per fit are recorded (H4 has about 360 rows in 60 days, below story 19's
  1,000-row minimum; reported as such). Trial count 2 (one chained account per clock).
