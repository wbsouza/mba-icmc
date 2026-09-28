# Story 21 — confluence chain: filter sequence, thresholds by rule, exits matched to the signal horizon (planned)

Status: planned, 2026-09-28. Owner: unassigned. No code or run yet. Baseline: `main` after PRs
#74–#81 (session-2 evidence, story 20; decision log in the viewer, PR #75/#80).

## Question

The session-2 rule cells were one-sided by accident (the January-2016 low cut on the event intensity
was never reached in the trading year) and their profit equalled the always-short control. A check on
the session-2 H1 decision log (5,668 bars, every bar with F1/F2/F3 outputs, the hourly intensity and
the next 1 and 4 hourly closes; `evidence/signal-horizon-check.md`) showed:

| condition | bars | next 4 h, mean pips | share down |
|---|---:|---:|---:|
| all bars | 5,668 | −0.3 | 50.4 % |
| intensity ≥ 0.6294 (rule fires) | 1,115 | −3.9 | 53.6 % |
| + F3 bearish candle | 63 | −3.8 | 55.6 % |
| + F1 trend down | 604 | −2.2 | 50.7 % |
| + F2 RSI/MACD sell | 339 | −3.0 | 53.1 % |
| + 20-day momentum down | 622 | −6.3 | 55.8 % |
| + 20-day momentum up | 493 | −0.8 | 50.9 % |
| 20-day momentum down alone, all bars | 3,360 | +0.4 | 49.6 % |
| F3 bearish alone, all bars | 338 | +1.3 | 48.8 % |

Two readings, both exploratory (the year had been viewed; ten conditions compared): the signal bars
carry a short-horizon tilt of about 4 pips over 4 hours that the reported trades never captured,
because the money-management template holds each short for days with 4R/6R targets, so the trade
becomes the drift; and 20-day momentum in the same direction doubles the tilt while adding nothing on
its own. Candlestick confirmation adds nothing and leans the wrong way at H1.

Third reading, established after the story was drafted (`evidence/signal-horizon-check.md`, last
section): January 2016, the calibration month of every session, is the only month in twenty-four with
negative intensity values (GDELT coverage uniform), so every absolute news threshold was taken from an
outlier month; the low cut was never reached again and the rule cells were one-sided by construction.
Absolute cuts on the intensity are regime bets (share of bars above the high cut swings 0–87 % by
month).

Question: does a chain whose sequence is a contract (context → trigger → confirmation → risk →
horizon-matched exit) and whose thresholds are set by a rule on trailing data, not by outcome search,
beat its controls on a registered protocol?

## Chain contract

| position | role | filter | limits and thresholds, set by rule |
|---|---|---|---|
| 1 | context: allowed side | 20-day price momentum sign (F1 variant `momentum_context`, lookback in bars registered: 480 H1 / 120 H4) | sign only |
| 2 | trigger | F4, direction from the event intensity against a trailing 30-day quantile (`direction_source: intensity_relative`) | 90 % / 10 % quantiles of the trailing span, recomputed at each UTC month start from closed bars only |
| 3 | confirmation (arm B only) | F2 RSI/MACD agreement | midline 50, histogram threshold 0 (as today) |
| 4 | account risk | F5 | unchanged (daily −5 %, weekly −15 %, 2 concurrent, leverage 30, portfolio at risk 0.18) |
| 5 | sizing and exit | F6 with a bar-count exit and an ATR stop | risk 3 %, stop 2 × ATR(14), exit after 4 bars (the measured signal horizon), no targets, no trail |

Terminal rule: `agreement` (new): the side allowed by position 1, proposed by position 2 and, in
arm B, confirmed by position 3 must coincide; otherwise HOLD. F5/F6 keep their vetoes. Both sides may
fire in the same run.

## Engine work (small, each with Gherkin scenarios)

- `terminal_filter: agreement` in `chain/terminal.py`: BUY only if every voting filter says BUY or
  abstains and every required filter voted; same for SELL; else HOLD. Required filters named in YAML.
- F1 variant `momentum_context`: sign of close[t] / close[t − lookback] − 1 from closed bars; emits
  BUY/SELL as the allowed side, never a veto.
- F4 `direction_source: intensity_relative`: thresholds are quantiles of the trailing window of the
  intensity, refreshed monthly, never reading the current bar's window end.
- F6 `exit_after_bars`: close at the open of bar t + N when the position is still open; stop stays.
  (`close_on_veto` unchanged.)

## Cells (session-2 protocol: EUR/USD, $10,000, OANDA costs, 2016-03-01..2017-02-28, Mar–Oct
development, Nov–Feb read last; exploratory label because the year was inspected)

| cell | chain |
|---|---|
| A | momentum context → intensity trigger → F5 → F6 time exit |
| B | A + F2 confirmation |
| A-plan | as A but with the Heikin-Ashi H4 plan (4R/6R, trail) instead of the time exit: isolates the exit |
| T-only | intensity trigger alone (relative thresholds) → F5 → F6 time exit: isolates the context |
| M-only | momentum context alone → F5 → F6 time exit: isolates the trigger |
| always-short / always-long | drift controls with the time exit |

Both clocks (H1, H4), so 14 cells. Primary comparison: A vs T-only on the untouched months, paired
daily equity (stationary bootstrap, block 4/2, 999 resamples, seed 42). Secondary: A vs A-plan (exit
horizon), B vs A (confirmation), A vs always-short (drift). Prediction-quality endpoint alongside:
next-4-bar directional hit rate on the bars where each chain would enter, on the untouched months.

## Not done here

- No threshold search: quantile shares (90/10), lookbacks (20 days, 4-bar exit, ATR 14 × 2) are
  registered before the runs from the check above and from common practice; changing any of them is
  a new registered cell.
- No candlestick confirmation arm (the check says no); story 13's extension owns candlesticks.
- Session timing (London/New York opens), support/resistance and Bollinger context: listed for
  story 16's contest, not here.
- Adaptive thresholds beyond the monthly trailing quantile: story 19.

## Acceptance

- Engine additions merged with scenarios: agreement terminal, momentum context, relative intensity
  thresholds, bar-count exit; `explain-strategy` shows every parameter with provenance.
- Registration (job README + Chapter 4 paragraph) before any cell runs; results, paired inference,
  reproduction of the controls; viewer shows the cells with the decision log.
- Chapter 4: one subsection; Chapter 5: the signal-horizon lesson (a signal must be traded on its
  own horizon) whatever the outcome.
