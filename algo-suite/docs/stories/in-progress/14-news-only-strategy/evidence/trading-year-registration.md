# 2026-09-28 trading-year comparison (registered 06:25 UTC, before any cell ran)

One year of training (fit 2015-03-02..2015-12-31, combiner calibrated January 2016, February
2016 held out; the models already trained for each arm are reused unchanged) and one year of
trading, 2016-03-01..2017-02-28, one $10,000 account per cell, same costs, risk guard and
Heikin-Ashi H4 money-management template across arms. Arms at H1 and H4: price-only baseline
(TA-Lib candles on, activity off), hybrid (same + F4 and the news family), news-only (F7 on the
news family, 10 % quantile thresholds), news-rule with both sign conventions (thresholds at the
January-2016 90/10 % intensity quantiles). Ten cells. March..October 2016 is development data;
November 2016..February 2017 are the untouched months, read last. Primary comparison: hybrid vs
price-only at H1, paired daily equity on the untouched months (block 4, sensitivity 2, 999
resamples, seed 42); news-only and the two rule signs are secondary; the reversed-sign rule is
carried as a registered cell, not as a post-hoc pick. Trial count for this job: 10.

Supplement registered 06:50 UTC, before viewing (same year, same rules): `q10-atr-stop` (H4, the
first positive H4 cell over March..October) and `h1-vol-0.8` (H1 with the activity gate at 0.8, the
best fixed-threshold H1 cell) — two more cells, trial count 12.
