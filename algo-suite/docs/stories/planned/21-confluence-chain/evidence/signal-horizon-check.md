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

## Candlestick patterns as the trigger (same log, same year, exploratory)

"Right" = the next close moved the pattern's way. Continuation reading = trade the pattern's own
direction; reversal reading = the classic context (bearish after a rise, bullish after a fall; prior
move = last 24 bars). Pattern counts over the year: bullish_engulfing 294, bearish_engulfing 291,
hammer 123, shooting_star 41, evening_star 6, morning_star 6.

| condition | bars | next 1 h mean | right | next 4 h mean | right |
|---|---:|---:|---:|---:|---:|
| bullish pattern → BUY | 423 | −0.18 | 49.4 % | +1.24 | 51.1 % |
| bearish pattern → SELL | 338 | −1.25 | 41.7 % | −1.26 | 48.8 % |
| bearish after 24-bar rise → SELL | 153 | −1.03 | 42.5 % | −1.14 | 51.6 % |
| bearish after 24-bar fall → SELL | 185 | −1.43 | 41.1 % | −1.36 | 46.5 % |
| bullish after 24-bar fall → BUY | 203 | +0.46 | 51.7 % | +2.33 | 54.2 % |
| bullish after 24-bar rise → BUY | 220 | −0.77 | 47.3 % | +0.23 | 48.2 % |
| bearish + F1 up (reversal) → SELL | 141 | +0.26 | 46.1 % | +1.74 | 53.2 % |
| bearish + F1 down (continuation) → SELL | 197 | −2.32 | 38.6 % | −3.41 | 45.7 % |
| bullish + F1 down (reversal) → BUY | 196 | +0.21 | 51.0 % | +2.47 | 56.1 % |
| bullish + F1 up (continuation) → BUY | 227 | −0.52 | 48.0 % | +0.17 | 46.7 % |
| bearish → SELL, intensity ≥ 0.6294 (news last) | 63 | −1.02 | 46.0 % | +3.75 | 55.6 % |
| bearish → SELL, intensity < 0.6294 | 275 | −1.30 | 40.7 % | −2.41 | 47.3 % |
| bullish → BUY, intensity ≥ 0.6294 | 86 | +0.54 | 52.3 % | −1.88 | 50.0 % |
| bullish → BUY, intensity < 0.6294 | 337 | −0.36 | 48.7 % | +2.04 | 51.3 % |
| bearish_engulfing → SELL | 291 | −1.87 | 38.8 % | −2.67 | 46.0 % |
| bullish_engulfing → BUY | 294 | −0.55 | 48.6 % | +1.33 | 52.4 % |
| hammer → BUY | 123 | +0.89 | 51.2 % | +1.06 | 47.2 % |
| shooting_star → SELL | 41 | +2.71 | 58.5 % | +6.34 | 63.4 % |
| evening_star → SELL | 6 | +2.08 | 66.7 % | +14.99 | 83.3 % |
| morning_star → BUY | 6 | −4.14 | 50.0 % | +0.43 | 66.7 % |

Reading: as continuation signals the patterns lean the wrong way at H1 (bearish engulfing: price
rises on the next bar 61 % of the time, n = 291). In context (bullish after a fall, bullish in an
F1 downtrend) the bullish side shows 54–56 % at 4 h; the shooting star works as intended on 41
cases. Bigalow's context rules and the fuller TA-Lib catalogue are the story-13 extension and the
story-16 contest; this table is the reason the confluence chain does not use pattern confirmation.

## Support and resistance as location (same log, exploratory)

Levels: the highest high and lowest low of the previous 60 H1 bars; classic daily pivots
(P, R1/R2, S1/S2) from the previous UTC day. "Near" = within 10 pips. "Right" = moved away from
the level (mean-reversion reading) or through it (breakout reading), as labelled.

| condition | bars | next 1 h mean | right | next 4 h mean | right | next 24 h mean | right |
|---|---:|---:|---:|---:|---:|---:|---:|
| near 60-bar high → SELL (fade) | 327 | +0.10 | 52.6 % | +0.82 | 52.9 % | +13.13 | 59.3 % |
| near 60-bar low → BUY (fade) | 463 | +0.43 | 54.2 % | +1.38 | 53.8 % | +3.24 | 52.9 % |
| near pivot R1/R2 → SELL | 977 | +0.34 | 52.9 % | +0.71 | 52.5 % | +2.40 | 51.4 % |
| near pivot S1/S2 → BUY | 1002 | −0.24 | 49.8 % | −0.12 | 48.6 % | +3.09 | 51.3 % |
| near 60-bar high → BUY (breakout) | 327 | −0.10 | 47.4 % | −0.82 | 47.1 % | −13.13 | 40.4 % |
| near 60-bar low → SELL (breakdown) | 463 | −0.43 | 45.8 % | −1.38 | 46.0 % | −3.24 | 46.9 % |
| near 60-bar high + bearish pattern → SELL | 13 | −1.41 | 30.8 % | +4.89 | 61.5 % | +28.78 | 69.2 % |
| near 60-bar low + bullish pattern → BUY | 32 | +0.30 | 56.2 % | +2.51 | 59.4 % | +7.75 | 56.2 % |
| near pivot R + bearish pattern → SELL | 46 | −1.01 | 43.5 % | +2.69 | 47.8 % | +8.41 | 52.2 % |
| near pivot S + bullish pattern → BUY | 66 | +0.42 | 45.5 % | +0.33 | 48.5 % | +3.35 | 50.0 % |
| near 60-bar low + bullish + intensity < 0.6294 → BUY | 22 | −0.42 | 54.5 % | +3.83 | 59.1 % | +11.34 | 54.5 % |
| near 60-bar high + bearish + intensity < 0.6294 → SELL | 12 | −1.45 | 33.3 % | +4.38 | 58.3 % | +28.66 | 66.7 % |
| bullish pattern, not near a low → BUY | 391 | −0.22 | 48.8 % | +1.13 | 50.4 % | +0.74 | 52.7 % |
| bearish pattern, not near a high → SELL | 325 | −1.24 | 42.2 % | −1.51 | 48.3 % | +0.30 | 48.6 % |

Reading: swing levels carry a mean-reversion tilt (fading a 60-bar high or low is right 53–59 %
of the time at 4 and 24 h; the breakout reading is its mirror); pivots carry little. Location plus
a same-side pattern strengthens the bullish side at the low (59 % at 4 h, n = 32); samples are
small and the 24-h "sell at the high" figure benefits from the euro's decline in the last months.
This is why story 21 puts support/resistance at the start of the chain (location) and at the end
(targets), and why story 16's contest keeps it as a component.
