Feature: Causal candlestick context evaluation
  Story 22, task T4 (CND-03, CND-04, CND-05, CND-06). A pure evaluator over at most
  max_history (256) closed bars that produces separately typed, causal context
  evidence: T-line (EMA), stochastic, moving-average levels and trend. Every value
  is computed from closed bars up to and including the evaluated bar; no future bar
  and no outcome label enters. Synthetic series prove arithmetic only.

  Definitions (T1 ledger parameters; sources: webinar 10:03 stochastic 12,3,3 with
  80/20, 51:23 "just simple moving average" for the smoothing; 10:49 and 26:54 T-line
  = 8-period exponential moving average; 10:16 and book 24/30 for the simple moving
  averages; the SMA(20) set is the webinar's, the book's charts use 50 and 200):
    - Close series c[1..n] are bar closes. Readiness is per indicator; a WARMUP
      indicator has value None and status WARMUP; it never yields NaN or infinity.
    - EMA(8) (ema_period p = 8): seeded like `training.ema_series`, a running simple
      mean of the first p closes, then ema[i] = c[i] * k + ema[i-1] * (1 - k) with
      k = 2 / (p + 1). READY once n >= p; its value at n = p is the plain mean.
      t_line_position: ABOVE when close > ema, BELOW when close < ema, ON when equal.
    - Stochastic (k = 12, k_smooth = 3, d = 3): raw%K[i] = 100 * (c[i] - LL) / (HH - LL)
      over the last k bars' highs and lows (HH = max high, LL = min low); slow%K =
      simple mean of the last k_smooth raw%K values; %D = simple mean of the last d
      slow%K values. raw%K READY at n >= 12, slow%K at n >= 14, %D at n >= 16.
      When HH == LL the raw%K is UNDEFINED for that bar: value None, status
      UNDEFINED, no exception, and every smoothed value that would consume it is
      UNDEFINED too. stochastic_zone from %D: OVERBOUGHT when %D > 80, OVERSOLD when
      %D < 20, NEUTRAL otherwise (exactly 80 and exactly 20 are NEUTRAL), UNDEFINED
      when %D is None.
    - Levels (sma_periods 20, 50, 200): sma_m = simple mean of the last m closes,
      READY at n >= m; distance_m = (close - sma_m) / sma_m (dimensionless, prices
      are positive so the divisor is never zero); a flat series gives exactly 0.0.
    - Trend evidence: trend = UP when t_line_position is ABOVE, DOWN when BELOW,
      FLAT when ON; WARMUP while the EMA is WARMUP. The catalog's net(3) precondition
      stays inside the catalog; the two are never merged.
    - Context status: READY when every indicator is READY, else WARMUP. UNDEFINED is
      a READY-time value state, not warmup.
    - Numeric expectations below are exact rational values; compare within 1e-9.
    - Bars in this feature are 60-minute UTC bars unless stated; a bar written as a
      single close c means (open c, high c + 0.5, low c - 0.5, close c) except where the
      stochastic rows fix high and low explicitly.

  Rule: The T-line is an EMA(8) seeded with a running mean

    Scenario Outline: EMA(8) over closes 1..10 is hand-calculated (<bars> bars)
      Given closes 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 as 60-minute bars
      When the context is evaluated after <bars> bars
      Then the ema status is "<status>" and its value is <ema>
      And the t_line_position is "<position>"

      Examples:
        | bars | status | ema  | position |
        | 1    | WARMUP | None | WARMUP   |
        | 7    | WARMUP | None | WARMUP   |
        | 8    | READY  | 4.5  | ABOVE    |
        | 9    | READY  | 5.5  | ABOVE    |
        | 10   | READY  | 6.5  | ABOVE    |

    Scenario Outline: T-line position at the three boundaries (<case>)
      Given closes <closes> as 60-minute bars
      When the context is evaluated after all bars
      Then the ema status is "READY" and its value is <ema>
      And the t_line_position is "<position>"
      And the trend is "<trend>"

      Examples:
        | case                  | closes                          | ema | position | trend |
        | rising, close above   | 1, 2, 3, 4, 5, 6, 7, 8          | 4.5 | ABOVE    | UP    |
        | falling, close below  | 8, 7, 6, 5, 4, 3, 2, 1          | 4.5 | BELOW    | DOWN  |
        | flat, close on        | 5, 5, 5, 5, 5, 5, 5, 5          | 5   | ON       | FLAT  |
        | returning to the mean | 1, 2, 3, 4, 5, 6, 7, 8, 4.5     | 4.5 | ON       | FLAT  |

  Rule: The stochastic is 12,3,3 with simple smoothing and exact zone boundaries

    Scenario Outline: Stochastic 12,3,3 readiness and hand-calculated values (<bars> bars)
      Given 16 bars with open 15, high 20 and low 10 whose closes are 15 x12, 18, 12, 19.5, 13.5
      When the context is evaluated after <bars> bars
      Then the raw stochastic K is <raw> with status "<raw_status>"
      And the slow stochastic K is <slow> with status "<slow_status>"
      And the stochastic D is <d> with status "<d_status>"
      And the stochastic_zone is "<zone>"

      Examples:
        | bars | raw  | raw_status | slow | slow_status | d    | d_status | zone      |
        | 11   | None | WARMUP     | None | WARMUP      | None | WARMUP   | UNDEFINED |
        | 12   | 50   | READY      | None | WARMUP      | None | WARMUP   | UNDEFINED |
        | 13   | 80   | READY      | None | WARMUP      | None | WARMUP   | UNDEFINED |
        | 14   | 20   | READY      | 50   | READY       | None | WARMUP   | UNDEFINED |
        | 15   | 95   | READY      | 65   | READY       | None | WARMUP   | UNDEFINED |
        | 16   | 35   | READY      | 50   | READY       | 55   | READY    | NEUTRAL   |

    Scenario Outline: Zones use strict inequalities at 80 and 20 (<case>)
      Given 16 bars with open 15, high 20 and low 10 and every close <close>
      When the context is evaluated after all bars
      Then the stochastic D is <d> with status "READY"
      And the stochastic_zone is "<zone>"

      Examples:
        | case                 | close | d   | zone       |
        | exactly 80           | 18    | 80  | NEUTRAL    |
        | just above 80        | 18.1  | 81  | OVERBOUGHT |
        | top of the range     | 20    | 100 | OVERBOUGHT |
        | exactly 20           | 12    | 20  | NEUTRAL    |
        | just below 20        | 11.9  | 19  | OVERSOLD   |
        | bottom of the range  | 10    | 0   | OVERSOLD   |

    Scenario: A zero-range stochastic window is UNDEFINED, never NaN and never an exception
      Given 16 flat bars (1000, 1000, 1000, 1000)
      When the context is evaluated after all bars
      Then the raw stochastic K is None with status "UNDEFINED"
      And the stochastic D is None with status "UNDEFINED"
      And the stochastic_zone is "UNDEFINED"
      And the ema status is "READY" and its value is 1000
      And the t_line_position is "ON"
      And no context value is NaN or infinite

    Scenario: The stochastic recovers once the window regains a range
      Given 16 flat bars (15, 15, 15, 15) followed by 16 bars with open 15, high 20, low 10 and close 15
      When the context is evaluated after all bars
      Then the raw stochastic K is 50 with status "READY"
      And the slow stochastic K is 50 with status "READY"
      And the stochastic D is 50 with status "READY"

  Rule: Moving-average levels report normalized distances with per-period readiness

    Scenario Outline: SMA 20/50/200 distances on a two-level series (<bars> bars)
      Given 100 bars closing at 8 followed by 100 bars closing at 12, as 60-minute bars
      When the context is evaluated after <bars> bars
      Then the sma distances are: 20 -> <d20>, 50 -> <d50>, 200 -> <d200>
      And the level statuses are: 20 -> "<s20>", 50 -> "<s50>", 200 -> "<s200>"
      And the context status is "<status>"

      Examples:
        | bars | d20  | d50  | d200 | s20    | s50    | s200   | status |
        | 19   | None | None | None | WARMUP | WARMUP | WARMUP | WARMUP |
        | 20   | 0    | None | None | READY  | WARMUP | WARMUP | WARMUP |
        | 50   | 0    | 0    | None | READY  | READY  | WARMUP | WARMUP |
        | 199  | 0    | 0    | None | READY  | READY  | WARMUP | WARMUP |
        | 200  | 0    | 0    | 0.2  | READY  | READY  | READY  | READY  |

    Scenario: The SMA(20) distance is hand-calculated on a mixed window
      Given 10 bars closing at 8 followed by 10 bars closing at 12, as 60-minute bars
      When the context is evaluated after all bars
      Then the sma distances are: 20 -> 0.2, 50 -> None, 200 -> None

  Rule: Configuration and inputs fail fast without touching state

    Scenario Outline: Invalid context configuration is rejected (<case>)
      Given a context configuration with <field> set to <value>
      When the context configuration is validated
      Then context configuration validation rejects mentioning "<field>"

      Examples:
        | case                        | field              | value          |
        | zero EMA period             | ema_period         | 0              |
        | negative EMA period         | ema_period         | -8             |
        | boolean EMA period          | ema_period         | true           |
        | fractional EMA period       | ema_period         | 2.5            |
        | string EMA period           | ema_period         | "8"            |
        | zero stochastic K           | stochastic_k       | 0              |
        | zero K smoothing            | stochastic_k_smooth| 0              |
        | zero D                      | stochastic_d       | 0              |
        | overbought below oversold   | overbought         | 10             |
        | overbought equal oversold   | overbought         | 20             |
        | overbought above 100        | overbought         | 101            |
        | oversold below 0            | oversold           | -1             |
        | empty SMA periods           | sma_periods        | []             |
        | duplicate SMA periods       | sma_periods        | [20, 20, 200]  |
        | zero SMA period             | sma_periods        | [0, 50, 200]   |
        | SMA period above 256        | sma_periods        | [20, 50, 257]  |
        | SMA periods not a list      | sma_periods        | 200            |

    Scenario: A context longer than max_history is rejected instead of silently shortened
      Given a candle configuration with max_history 199 and sma_periods "20,50,200"
      When the candle configuration is validated
      Then candle configuration validation rejects mentioning "200"

    Scenario: A rejected bar leaves the context state untouched
      Given closes 1, 2, 3, 4, 5, 6, 7, 8 as 60-minute bars
      When a bar with OHLC [9, 8, 10, 9] is offered to the context
      Then the context rejects it mentioning "ordering" and a remedy
      And the context after the next valid close 9 has ema 5.5 and status "READY" for the ema

    Scenario: Context beyond 256 bars keeps only the last 256 closed bars
      Given 300 bars closing at 8 followed by 200 bars closing at 12, as 60-minute bars
      When the context is evaluated after all bars
      Then the context history_count is 256
      And the sma distances are: 20 -> 0, 50 -> 0, 200 -> 0

  Rule: Evidence is separately typed and causal

    Scenario: Geometry, trend, levels and confirmation are distinct typed fields
      Given 200 bars closing at 8 followed by 16 bars with open 15, high 20, low 10 and close 15
      When the context is evaluated after all bars
      Then the context evidence exposes distinct fields ema, stochastic, levels and trend
      And each field carries its own status
      And the context evidence carries no pattern hit and no confirmation field

    Scenario: Future bars cannot change an already evaluated prefix
      Given closes 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 as 60-minute bars
      When the same prefix is evaluated before a rising suffix and before a falling suffix
      Then the per-bar context evidence over the prefix is identical under both suffixes
      And the final prefix ema is 6.5

    Scenario: Every context value carries the availability close_time of its bar
      Given closes 1, 2, 3, 4, 5, 6, 7, 8 as 60-minute bars ending at "2024-01-01T08:00:00+00:00"
      When the context is evaluated after all bars
      Then the context evidence close_time is "2024-01-01T08:00:00+00:00"

    Scenario: The context evaluator exposes its bound history
      Given closes 1, 2, 3, 4, 5, 6, 7, 8 as 60-minute bars
      When the context is evaluated after all bars, keeping the evaluator
      Then the context evaluator's history holds 8 bars
      And the ema status is "READY" and its value is 4.5
