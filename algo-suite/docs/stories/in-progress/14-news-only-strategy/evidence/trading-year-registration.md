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

Control registered 06:58 UTC, before running: `short-when-flat-h1` / `-h4` — the reversed-sign rule's
chain with thresholds that make F4 recommend SELL on every bar (sign −1, sell threshold above any
intensity, buy unreachable), so the account is short whenever flat, with the same plan and risk guard.
If it matches or beats the reversed-sign rule, the rule's profit is drift, not timing. Trial count 14.

Correction, 07:15 UTC: the `short-when-flat-*` cells were mis-specified (F4 said SELL on every bar and
sign −1 turned that into BUY), so they are in fact a *long-whenever-flat* control; kept and reported as
such (H1 −29.0 %, H4 −14.5 %). The intended control is `always-short-h1` / `-h4` (F4 says BUY on every
bar, sign −1 → SELL), registered before running. Trial count 16. The H1 long-whenever-flat run also
exposed an engine limitation: on 2016-09-21 a stop-market and a limit target filled in the same minute
bar, leaving an unplanned position; recorded as technical debt (same-bar OCO double fill).

## Timestamp audit (added 2026-09-28 11:30 UTC)

The "registered HH:MM UTC" times in the paragraphs above are the times those paragraphs were
written, not the times the cells were fixed. The file modification times of the job directory
(now `experiment-test-archives/pre-rename-session-1/2026-09-28-trading-year/`) give the actual
order, all UTC:

| stage | cells fixed (`plan*.tsv` + strategy configs) | launched (first run log) | finished (`exit-status*.txt`) | paragraph written |
|---|---|---|---|---|
| ten main cells | 06:12:24 | 06:12:41 | 06:21:48 | "06:25" |
| supplement (`q10-atr-stop`, `h1-vol-0.8`) | 06:21:02 | 06:21:03 | 06:24:49 | "06:50" |
| long-whenever-flat control (`short-when-flat-*`) | 06:30:03 | 06:30:04 | 06:31:33 | "06:58" |
| always-short control | 06:32:58 | 06:32:59 | 06:34:26 | "07:15" |
| both-sides cells | 07:03:25 | 07:03:28 | 07:31:35 | "07:05" |
| gated cells | 07:04:05 | 07:04:07 | 07:31:35 | "07:10" |

`paired-inference.md` was produced at 06:23:17 and `results.md` at 06:35:01. What the record
supports: every cell was fixed in its plan file and strategy configs seconds before its launch,
so no cell was chosen after its own outcome; the primary comparison (hybrid vs price-only at H1
on the untouched months, paired daily equity) was pre-specified in the one-year protocol
(Chapter 4, `subsec:one-year-protocol`) before this job existed; the supplement cells were chosen
from the earlier tuning sweeps' development windows, as stated. What the record does not
support: that the registration paragraphs of the first four stages were written before those
stages' outcomes existed. The two controls were, by design, a reaction to the reversed-sign
rule's result, as Chapter 4 says. Chapter 4 and the experiment registry carry this note.
