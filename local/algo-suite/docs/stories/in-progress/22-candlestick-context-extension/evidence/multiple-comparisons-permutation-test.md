# Story 22 — multiple-comparisons permutation test on the per-pattern sweep

Addresses whether the per-pattern isolation sweep's one net-positive pattern
(`hanging_man`, +478.43 over 38 trades) is distinguishable from the number of
positive results expected by chance when 22 independent patterns are screened
at once. Companion evidence to the per-pattern isolation sweep (22 backtests,
one per admitted candlestick pattern, `candles-solo-<id>`, EURUSD,
`2016-03-01` to `2017-02-28`, H1, `$10,000`).

## Method

1. Pool every closed trade's `profitLoss` from all 22 individual
   `candles-solo-<id>` runs (1,026 trades total; the five neutral-polarity
   ids — `doji`, `doji_dragonfly`, `doji_gravestone`, `doji_long_legged`,
   `spinning_top` — are kept as five separate groups here, each carrying its
   own trade count, exactly as the real sweep produced them; this mirrors
   the real screen rather than pre-collapsing the shared signal, since the
   question is "how surprising is the best of 22 screened groups," not a
   claim about how many independent signals exist).
2. Record each real pattern's trade count (`sizes`, 22 integers summing to
   1,026) and its real summed `profitLoss` (`sums`); the observed best is
   `hanging_man` at `+478.43`.
3. Run 20,000 trials. Each trial reshuffles the full pooled list of 1,026
   trades (`random.shuffle`, no replacement) and re-partitions the shuffled
   list into 22 contiguous groups using the *same* 22 group sizes as the
   real patterns (so every trial's partition has identical group sizes to
   the real screen, only the assignment of trades to groups is randomized).
   The trial's score is the maximum of its 22 group sums.
4. The permutation $p$-value is the fraction of trials whose maximum group
   sum is at least as large as the real observed maximum
   ($+478.43$): $p = \#\{\text{trials}: \max \geq 478.43\} / 20000$.
5. Seed: `20260928` (matches the date this sweep and its diagnostics were
   run), for exact reproducibility.

## Script

`evidence/permutation_test.py` (this directory) reads each pattern's
`trades.json` directly from its own run directory under
`algo-suite/data/runs/candles-solo-<id>/<run-id>/trades.json` (the most
recent run directory per pattern, matching the per-pattern isolation sweep's
own run references), pools `profitLoss`, and runs the trial loop above.

```
uv run python algo-suite/docs/stories/in-progress/22-candlestick-context-extension/evidence/permutation_test.py
```

## Result (re-verified independently before this file was committed)

```
22 patterns, pooled n=1026, observed best=hanging_man sum=478.43
permutation p-value (max-of-22 >= observed): 0.9870 (19741/20000)
```

98.70% of the 20,000 reshuffles produced a best-of-22 group sum at least as
good as the one actually observed. `hanging_man`'s apparent edge is not
distinguishable from chance at this sample size and pattern count.

Per-pattern trade counts and summed profit or loss, as read directly from
each pattern's own `trades.json` (matches Table 23 of the monograph
one-for-one; `net P/L` here is the unrounded sum the script computes, the
monograph rounds to two decimals):

| Pattern id | Trades | Net P/L |
|---|---:|---:|
| `hanging_man` | 38 | 478.43 |
| `dark_cloud_cover` | 45 | -665.97 |
| `bearish_engulfing` | 76 | -787.74 |
| `evening_star` | 44 | -858.20 |
| `bearish_counterattack_line` | 39 | -934.10 |
| `morning_star` | 46 | -1097.20 |
| `doji` | 37 | -1120.08 |
| `doji_dragonfly` | 37 | -1120.08 |
| `doji_gravestone` | 37 | -1120.08 |
| `doji_long_legged` | 37 | -1120.08 |
| `spinning_top` | 37 | -1120.08 |
| `bullish_kicker` | 41 | -1422.46 |
| `shooting_star` | 39 | -1438.84 |
| `bullish_counterattack_line` | 41 | -1457.68 |
| `bullish_harami` | 54 | -1575.13 |
| `piercing_line` | 45 | -1778.90 |
| `bearish_kicker` | 44 | -1802.33 |
| `hammer` | 44 | -1954.83 |
| `bearish_harami` | 57 | -2648.48 |
| `inverted_hammer` | 42 | -2750.03 |
| `bullish_engulfing` | 74 | -2992.04 |
| `methods_rising` | 72 | -3327.39 |

Pooled trade count: 1,026 (sum of the 22 sizes above), matching the pooled
sample used by the market-context diagnostics on the same 22 runs.

## Limitations

- This is a permutation test over group *sizes* fixed to the real sweep's
  sizes, not a fully symmetric bootstrap over pattern identity; it answers
  "given these exact 22 group sizes, how often does reshuffling trade
  assignment alone produce a best group at least this good," which is the
  right question for this screen (the group sizes are a real, fixed
  property of each pattern's eligibility count, not something to
  randomize).
- The five neutral-polarity ids are kept separate here (not collapsed to one
  slot as in the combined-winners test), since collapsing them would change
  the trial's group count from 22 to 18 and understate how many independent
  screens were actually run against the pooled trade pool.
- `random.shuffle` on a list of dicts-turned-floats is not thread-safe or
  parallelized; a single seeded run is deterministic and was re-run once
  independently (by a different agent, same seed) to confirm the identical
  hit count (19741/20000) before this file was committed.
