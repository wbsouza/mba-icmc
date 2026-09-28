# Signal-horizon check on the session-2 H1 decision log (2026-09-28, exploratory)

Source: run `h1-q10-base` of session 2 (`decisions.parquet`, every bar with F1/F2/F3 outputs), the
hourly GDELT event intensity and hourly mid closes from the M1 bars (broad-window data root).
Window 2016-03-01..2017-02-28 (already viewed; ten conditions compared; no correction applied).
Forward return = close[t+k] / close[t] − 1 in 1e-4 units ("pips"); negative means a short placed at
bar t gained. "Rule fires" = intensity ≥ 0.6294 (the session-2 January-2016 90 % cut). Momentum =
close[t] / close[t − 480 bars] − 1 (about 20 trading days) and t − 3000 bars (about 6 months).

| condition | bars | next 1 h mean | down | next 4 h mean | down |
|---|---:|---:|---:|---:|---:|
| all bars | 5668 | −0.07 | 50.3 % | −0.26 | 50.4 % |
| rule fires | 1115 | −0.93 | 51.3 % | −3.85 | 53.6 % |
| rule + F3 bearish | 63 | +1.02 | 46.0 % | −3.75 | 55.6 % |
| rule + F3 bullish | 86 | +0.54 | 47.7 % | −1.88 | 50.0 % |
| rule + no pattern | 654 | −1.27 | 52.4 % | −4.30 | 53.5 % |
| rule + F1 down | 604 | −0.27 | 51.5 % | −2.22 | 50.7 % |
| rule + F1 up | 511 | −1.71 | 51.1 % | −5.78 | 57.1 % |
| rule + F2 SELL | 339 | −0.46 | 51.0 % | −3.01 | 53.1 % |
| rule + F2 BUY | 262 | −1.34 | 51.5 % | −3.86 | 53.1 % |
| rule + 20-day momentum < 0 | 622 | −1.53 | 51.6 % | −6.25 | 55.8 % |
| rule + 20-day momentum > 0 | 493 | −0.18 | 50.9 % | −0.83 | 50.9 % |
| rule + 6-month momentum < 0 | 772 | −0.92 | 49.7 % | −3.87 | 51.7 % |
| rule + 6-month momentum > 0 | 343 | −0.96 | 54.8 % | −3.80 | 58.0 % |
| all + F3 bearish | 338 | +1.25 | 41.7 % | +1.26 | 48.8 % |
| all + F1 down | 2815 | +0.31 | 48.4 % | +0.93 | 49.0 % |
| all + F2 SELL | 1621 | +0.38 | 49.1 % | +1.95 | 49.5 % |
| all + 20-day momentum < 0 | 3360 | +0.08 | 49.4 % | +0.38 | 49.6 % |
| all + 6-month momentum < 0 | 3201 | −0.05 | 50.3 % | −0.15 | 50.4 % |
| rule, Nov–Feb only | 682 | −0.97 | 49.6 % | −4.14 | 51.6 % |
| rule + F3 bearish, Nov–Feb | 30 | +1.73 | 36.7 % | −5.28 | 53.3 % |
| rule + F1 down, Nov–Feb | 347 | +0.11 | 48.4 % | −0.94 | 46.7 % |
| rule + 20-day momentum < 0, Nov–Feb | 449 | −1.76 | 50.8 % | −7.12 | 55.0 % |

Also established here: over the trading year the intensity never went below +0.02 (January 2016
ranged −0.34..+0.74), so the session-2 rule's low cut (−0.0046) never fired; `news-rule-*-plus` was
long-only and `news-rule-*-minus` short-only in effect. The level shift between January 2016 and
the following year is to be checked against the GDELT ingestion coverage (story 08) before the
relative threshold is relied on.
