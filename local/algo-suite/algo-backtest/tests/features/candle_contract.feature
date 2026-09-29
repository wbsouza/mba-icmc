Feature: Candle evidence and configuration contract
  Story 22, task T2 (CND-02, CND-03). One immutable, versioned contract shared by the
  catalog (T3), the context evaluator (T4), the sequence evaluator (T5) and the F3
  policy (T6): `CandleConfig`, `PatternHit`, `CandleEvidence` and the closed-bar
  validator that every recognizer runs before advancing state. Synthetic fixtures
  prove mechanics only; nothing here is market-performance evidence.

  Contract (the coder's T1 ledger may refine names, never these outcomes):
    - A bar is (close_time, open, high, low, close). Prices are finite positive reals
      (int, float, numpy real; booleans rejected) with low <= min(open, close) and
      max(open, close) <= high. close_time is a timezone-aware UTC datetime, the END
      of the bar's bucket, aligned to the configured timeframe (close_time minus the
      UTC midnight of its day is a whole multiple of timeframe_minutes).
    - Bars enter strictly increasing by close_time; an equal close_time is a duplicate.
      A rejected bar raises ValueError naming the offending field and a remedy and
      leaves the history untouched (history_count unchanged, the next valid bar accepted).
    - CandleConfig fields: catalog_version (non-empty str, default "1"),
      enabled_rules (non-empty, unique, every id in the admitted catalog below),
      max_history (int, 1..256, default 256, at least the longest lookback of any
      enabled rule or context indicator; never silently shortened), timeframe_minutes
      (positive int divisor of 1440), context (ema_period 8, stochastic_k 12,
      stochastic_k_smooth 3, stochastic_d 3, overbought 80, oversold 20,
      sma_periods (20, 50, 200)), sequence (doji_engulfing: true), policy_mode
      (legacy | advisory | required_entry, default legacy).
    - PatternHit(id, polarity in {-1, 0, 1}, rule_version non-empty str,
      status READY | WARMUP). A WARMUP hit has polarity 0.
    - CandleEvidence(schema_version, catalog_version, pair, timeframe_minutes,
      close_time, history_count, status READY | WARMUP, hits tuple sorted by id with
      unique ids, context (ContextEvidence | None), confirmation).
    - Both dataclasses are frozen: attribute assignment raises.

  The admitted catalog (T1 ledger IDs; lookback = closed bars needed including the
  current one; the six legacy rules are the existing TA-Lib recognizers, so their
  lookback is TA-Lib's lookback plus one: CDLENGULFING 2 + 1, CDLHAMMER and
  CDLSHOOTINGSTAR 11 + 1, CDLMORNINGSTAR and CDLEVENINGSTAR 12 + 1). The longest
  lookback a configuration needs is the maximum over its enabled rules, ema_period,
  stochastic_k + stochastic_k_smooth + stochastic_d - 2 and its sma_periods:

    | id                | polarity | lookback | origin |
    | bearish_engulfing | -1       | 3        | legacy |
    | bearish_harami    | -1       | 2        | new    |
    | bearish_kicker    | -1       | 2        | new    |
    | bullish_engulfing | 1        | 3        | legacy |
    | bullish_harami    | 1        | 2        | new    |
    | bullish_kicker    | 1        | 2        | new    |
    | dark_cloud_cover  | -1       | 2        | new    |
    | doji              | 0        | 1        | new    |
    | doji_dragonfly    | 0        | 1        | new    |
    | doji_gravestone   | 0        | 1        | new    |
    | doji_long_legged  | 0        | 1        | new    |
    | evening_star      | -1       | 13       | legacy |
    | hammer            | 1        | 12       | legacy |
    | hanging_man       | -1       | 5        | new    |
    | inverted_hammer   | 1        | 5        | new    |
    | morning_star      | 1        | 13       | legacy |
    | piercing_line     | 1        | 2        | new    |
    | shooting_star     | -1       | 12       | legacy |
    | spinning_top      | 0        | 1        | new    |

  Story 23's bigalow-extended-signals addendum (BEXT-01, BEXT-02, BEXT-04) admits three
  further ids to the catalog above (usable via enabled_rules) without adding them to the
  default configuration, so this feature's frozen fixtures stay byte-identical:

    | id                          | polarity | lookback | origin |
    | bearish_counterattack_line  | -1       | 2        | new    |
    | bullish_counterattack_line  | 1        | 2        | new    |
    | methods_rising              | 1        | 4        | new    |

  Rule: The default configuration enables the Story 22 catalog and is immutable

    Scenario: The default configuration lists every default-enabled rule with its polarity and lookback
      Given the default candle configuration
      Then the configuration has catalog_version "1", max_history 256 and policy_mode "legacy"
      And the enabled rules are exactly, in id order:
        | id                | polarity | lookback |
        | bearish_engulfing | -1       | 3        |
        | bearish_harami    | -1       | 2        |
        | bearish_kicker    | -1       | 2        |
        | bullish_engulfing | 1        | 3        |
        | bullish_harami    | 1        | 2        |
        | bullish_kicker    | 1        | 2        |
        | dark_cloud_cover  | -1       | 2        |
        | doji              | 0        | 1        |
        | doji_dragonfly    | 0        | 1        |
        | doji_gravestone   | 0        | 1        |
        | doji_long_legged  | 0        | 1        |
        | evening_star      | -1       | 13       |
        | hammer            | 1        | 12       |
        | hanging_man       | -1       | 5        |
        | inverted_hammer   | 1        | 5        |
        | morning_star      | 1        | 13       |
        | piercing_line     | 1        | 2        |
        | shooting_star     | -1       | 12       |
        | spinning_top      | 0        | 1        |
      And the context parameters are ema_period 8, stochastic 12,3,3, overbought 80, oversold 20 and sma_periods 20,50,200

    Scenario: Configuration and evidence are frozen
      Given the default candle configuration
      And a READY candle evidence with one hit "doji"
      When any attribute of the configuration or the evidence is assigned
      Then the assignment raises an immutability error and the values are unchanged

    Scenario: The Story 23 extended-signal ids are admitted but excluded from the default
      Given the default candle configuration
      Then the admitted catalog includes, in id order:
        | id                         | polarity | lookback |
        | bearish_counterattack_line | -1       | 2        |
        | bullish_counterattack_line | 1        | 2        |
        | methods_rising             | 1        | 4        |
      And the admitted catalog is sorted by id
      And none of those ids are in the default enabled rules

  Rule: Configuration bounds fail fast with the field and a remedy

    Scenario Outline: max_history is an integer in 1..256 that covers every enabled lookback (<case>)
      Given a candle configuration with max_history <value>, enabled rules "<rules>", ema_period <ema>, stochastic <stoch> and sma_periods "<smas>"
      When the candle configuration is validated
      Then candle configuration validation <outcome> mentioning "<mention>"

      Examples:
        | case                                  | value | rules                      | ema | stoch  | smas       | outcome | mention     |
        | default upper bound                   | 256   | all                        | 8   | 12,3,3 | 20,50,200  | accepts | max_history |
        | exactly the SMA(200) lookback         | 200   | all                        | 8   | 12,3,3 | 20,50,200  | accepts | max_history |
        | one short of SMA(200)                 | 199   | all                        | 8   | 12,3,3 | 20,50,200  | rejects | 200         |
        | exactly the stochastic lookback (16)  | 16    | doji                       | 8   | 12,3,3 | 5          | accepts | max_history |
        | one short of the stochastic lookback  | 15    | doji                       | 8   | 12,3,3 | 5          | rejects | 16          |
        | exactly the star lookback             | 13    | morning_star,evening_star  | 8   | 1,1,1  | 5          | accepts | max_history |
        | one short of the star lookback        | 12    | morning_star,evening_star  | 8   | 1,1,1  | 5          | rejects | 13          |
        | exactly the hammer lookback           | 12    | hammer                     | 8   | 1,1,1  | 5          | accepts | max_history |
        | one short of the hammer lookback      | 11    | hammer                     | 8   | 1,1,1  | 5          | rejects | 12          |
        | exactly the engulfing lookback        | 8     | bullish_engulfing          | 8   | 1,1,1  | 5          | accepts | max_history |
        | one short of the EMA lookback         | 7     | doji                       | 8   | 1,1,1  | 5          | rejects | 8           |
        | sma_period exactly at the 256 bound   | 256   | doji                       | 8   | 1,1,1  | 256        | accepts | max_history |
        | above the 256 bound                   | 257   | all                        | 8   | 12,3,3 | 20,50,200  | rejects | 256         |
        | zero                                  | 0     | doji                       | 8   | 1,1,1  | 5          | rejects | max_history |
        | negative                              | -1    | doji                       | 8   | 1,1,1  | 5          | rejects | max_history |
        | boolean                               | true  | doji                       | 8   | 1,1,1  | 5          | rejects | max_history |
        | fractional                            | 2.5   | doji                       | 8   | 1,1,1  | 5          | rejects | max_history |
        | string                                | "256" | doji                       | 8   | 1,1,1  | 5          | rejects | max_history |

    Scenario Outline: enabled_rules must be a non-empty list of unique admitted ids (<case>)
      Given a candle configuration whose enabled_rules is <rules>
      When the candle configuration is validated
      Then candle configuration validation <outcome> mentioning "<mention>"

      Examples:
        | case                 | rules                          | outcome | mention           |
        | unknown id           | ["doji_star"]                  | rejects | doji_star         |
        | wrong case           | ["Hammer"]                     | rejects | Hammer            |
        | empty id             | [""]                           | rejects | enabled_rules     |
        | duplicate id         | ["doji", "hammer", "doji"]     | rejects | doji              |
        | empty list           | []                             | rejects | enabled_rules     |
        | scalar               | "doji"                         | rejects | enabled_rules     |
        | non-string entry     | ["doji", 7]                    | rejects | enabled_rules     |
        | valid subset         | ["hammer", "doji"]             | accepts | enabled_rules     |

    Scenario Outline: policy_mode is one of the three registered modes (<value>)
      Given a candle configuration with policy_mode <value>
      When the candle configuration is validated
      Then candle configuration validation <outcome> mentioning "policy_mode"

      Examples:
        | value            | outcome |
        | "legacy"         | accepts |
        | "advisory"       | accepts |
        | "required_entry" | accepts |
        | "required"       | rejects |
        | "Legacy"         | rejects |
        | ""               | rejects |
        | null             | rejects |
        | 1                | rejects |

    Scenario Outline: timeframe_minutes is a positive divisor of 1440 (<value>)
      Given a candle configuration with timeframe_minutes <value>
      When the candle configuration is validated
      Then candle configuration validation <outcome> mentioning "timeframe_minutes"

      Examples:
        | value | outcome |
        | 1     | accepts |
        | 60    | accepts |
        | 240   | accepts |
        | 1440  | accepts |
        | 7     | rejects |
        | 0     | rejects |
        | -60   | rejects |
        | true  | rejects |
        | 1.5   | rejects |

    Scenario Outline: catalog_version must be a non-empty string (<value>)
      Given a candle configuration with catalog_version <value>
      When the candle configuration is validated
      Then candle configuration validation <outcome> mentioning "catalog_version"

      Examples:
        | value | outcome |
        | "1"   | accepts |
        | "2a"  | accepts |
        | ""    | rejects |
        | 1     | rejects |
        | null  | rejects |

  Rule: Pattern hits carry a bounded polarity, a rule version and their own readiness

    Scenario Outline: PatternHit validation (<case>)
      Given a pattern hit with id <id>, polarity <polarity>, rule_version <version> and status <status>
      When the pattern hit is validated
      Then pattern hit validation <outcome> mentioning "<mention>"

      Examples:
        | case                    | id                  | polarity | version | status   | outcome | mention      |
        | bullish ready           | "bullish_engulfing" | 1        | "1"     | "READY"  | accepts | polarity     |
        | bearish ready           | "shooting_star"     | -1       | "1"     | "READY"  | accepts | polarity     |
        | neutral ready           | "doji"              | 0        | "1"     | "READY"  | accepts | polarity     |
        | warming up              | "hammer"            | 0        | "1"     | "WARMUP" | accepts | status       |
        | warmup with a polarity  | "hammer"            | 1        | "1"     | "WARMUP" | rejects | polarity     |
        | polarity too large      | "doji"              | 2        | "1"     | "READY"  | rejects | polarity     |
        | polarity too small      | "doji"              | -2       | "1"     | "READY"  | rejects | polarity     |
        | fractional polarity     | "doji"              | 0.5      | "1"     | "READY"  | rejects | polarity     |
        | boolean polarity        | "doji"              | true     | "1"     | "READY"  | rejects | polarity     |
        | wrong sign for the rule | "hammer"            | -1       | "1"     | "READY"  | rejects | hammer       |
        | unknown id              | "doji_star"         | 0        | "1"     | "READY"  | rejects | doji_star    |
        | empty version           | "doji"              | 0        | ""      | "READY"  | rejects | rule_version |
        | unknown status          | "doji"              | 0        | "1"     | "ready"  | rejects | status       |

  Rule: Fibonacci evidence carries a level only when READY and from the registered ratios

    Scenario Outline: FibonacciEvidence validation (<case>)
      Given a fibonacci evidence with status <status>, swing status <swing_status> and level <level>
      When the fibonacci evidence is validated
      Then fibonacci evidence validation <outcome> mentioning "<mention>"

      Examples:
        | case                          | status   | swing_status | level | outcome | mention |
        | ready with an admitted level  | "READY"  | "READY"      | 0.5   | accepts | level   |
        | ready with no level           | "READY"  | "READY"      | null  | accepts | level   |
        | ready with an unlisted level  | "READY"  | "READY"      | 0.4   | rejects | level   |
        | warmup with a stray level     | "WARMUP" | "WARMUP"     | 0.5   | rejects | level   |

  Rule: Evidence keeps hits in stable id order with UTC timing and bounded history

    Scenario Outline: Evidence hits must be sorted by id and unique (<case>)
      Given candle evidence whose hit ids are <ids>
      When the candle evidence is validated
      Then candle evidence validation <outcome> mentioning "<mention>"

      Examples:
        | case            | ids                                   | outcome | mention |
        | empty           | []                                    | accepts | hits    |
        | single          | ["doji"]                              | accepts | hits    |
        | sorted          | ["bullish_harami", "doji", "hammer"]  | accepts | hits    |
        | unsorted        | ["doji", "bullish_harami"]            | rejects | order   |
        | duplicate       | ["doji", "doji"]                      | rejects | doji    |
        | unknown         | ["doji", "doji_star"]                 | rejects | doji_star |

    Scenario Outline: Evidence close_time must be timezone-aware UTC (<case>)
      Given candle evidence whose close_time is <close_time>
      When the candle evidence is validated
      Then candle evidence validation <outcome> mentioning "close_time"

      Examples:
        | case            | close_time                 | outcome |
        | aware UTC       | 2024-01-01T10:00:00+00:00  | accepts |
        | naive           | 2024-01-01T10:00:00        | rejects |
        | other offset    | 2024-01-01T10:00:00+01:00  | rejects |
        | not a datetime  | "2024-01-01"               | rejects |

    Scenario Outline: Evidence status and history_count are consistent with the configuration (<case>)
      Given candle evidence with status <status>, history_count <count> and max_history <max>
      When the candle evidence is validated
      Then candle evidence validation <outcome> mentioning "<mention>"

      Examples:
        | case                     | status   | count | max | outcome | mention       |
        | ready at the bound       | "READY"  | 256   | 256 | accepts | history_count |
        | warming with one bar     | "WARMUP" | 1     | 256 | accepts | history_count |
        | zero bars                | "WARMUP" | 0     | 256 | accepts | history_count |
        | above the bound          | "READY"  | 257   | 256 | rejects | history_count |
        | above a smaller bound    | "READY"  | 13    | 12  | rejects | history_count |
        | negative                 | "READY"  | -1    | 256 | rejects | history_count |
        | boolean                  | "READY"  | true  | 256 | rejects | history_count |
        | unknown status           | "DONE"   | 1     | 256 | rejects | status        |

    Scenario Outline: Evidence status agrees with its hits' readiness (<case>)
      Given candle evidence with status <status> whose hits are <hits>
      When the candle evidence is validated
      Then candle evidence validation <outcome> mentioning "status"

      Examples:
        | case                              | status   | hits                            | outcome |
        | ready with only ready hits        | "READY"  | doji:READY,hammer:READY         | accepts |
        | ready with no hits                | "READY"  |                                 | accepts |
        | warming with one warming hit      | "WARMUP" | doji:READY,hammer:WARMUP        | accepts |
        | ready with a warming hit          | "READY"  | doji:READY,hammer:WARMUP        | rejects |
        | warming with only ready hits      | "WARMUP" | doji:READY                      | rejects |
        | warming with no hits              | "WARMUP" |                                 | rejects |

  Rule: Sequence evidence confirmation fields agree with its state

    Scenario Outline: SequenceEvidence confirmation fields must agree with its state (<case>)
      Given a sequence evidence with state <state>, confirmed_direction <direction> and confirmation_time <confirmation_time>
      When the sequence evidence is validated
      Then sequence evidence validation <outcome> mentioning "confirmation"

      Examples:
        | case                         | state       | direction | confirmation_time            | outcome |
        | idle, nothing set            | "IDLE"      | null      | null                          | accepts |
        | confirmed, both set          | "CONFIRMED" | 1         | "2024-01-01T01:00:00+00:00"  | accepts |
        | confirmed missing time       | "CONFIRMED" | 1         | null                          | rejects |
        | confirmed missing direction  | "CONFIRMED" | null      | "2024-01-01T01:00:00+00:00"  | rejects |
        | idle with a stray direction  | "IDLE"      | 1         | null                          | rejects |
        | idle with a stray time       | "IDLE"      | null      | "2024-01-01T01:00:00+00:00"  | rejects |

  Rule: The closed-bar validator rejects malformed bars before any state advances

    Scenario Outline: Every price must be a finite positive real number (<field> = <value>)
      Given a candle history with 5 valid 60-minute bars
      And a next bar whose "<field>" price is <value>
      When the next bar is offered to the candle history
      Then the candle history rejects it mentioning "<field>" and a remedy
      And the candle history still holds 5 bars and accepts the following valid bar

      Examples:
        | field | value        |
        | open  | "10"         |
        | high  | true         |
        | low   | null         |
        | close | NaN          |
        | open  | Infinity     |
        | low   | -Infinity    |
        | high  | 0            |
        | close | -1           |
        | open  | huge_integer |
        | low   | numpy_bool   |
        | close | complex      |

    Scenario Outline: Impossible OHLC ordering is rejected (<prices>)
      Given a candle history with 5 valid 60-minute bars
      And a next bar with OHLC <prices>
      When the next bar is offered to the candle history
      Then the candle history rejects it mentioning "ordering" and a remedy
      And the candle history still holds 5 bars and accepts the following valid bar

      Examples:
        | prices          |
        | [11, 10, 8, 9]  |
        | [9, 10, 8, 11]  |
        | [7, 10, 8, 9]   |
        | [9, 10, 8, 7]   |
        | [9, 8, 10, 9]   |

    Scenario Outline: close_time must be aware UTC, aligned, and strictly increasing (<case>)
      Given a candle history with 5 valid 60-minute bars ending at "2024-01-01T10:00:00+00:00"
      And a next valid bar whose close_time is <close_time>
      When the next bar is offered to the candle history
      Then the candle history <outcome> mentioning "<mention>"
      And the candle history still holds <held> bars

      Examples:
        | case              | close_time                 | outcome | mention    | held |
        | next hour         | 2024-01-01T11:00:00+00:00  | accepts | close_time | 6    |
        | duplicate         | 2024-01-01T10:00:00+00:00  | rejects | duplicate  | 5    |
        | earlier           | 2024-01-01T09:00:00+00:00  | rejects | order      | 5    |
        | misaligned        | 2024-01-01T10:30:00+00:00  | rejects | aligned    | 5    |
        | naive             | 2024-01-01T11:00:00        | rejects | UTC        | 5    |
        | non-UTC offset    | 2024-01-01T12:00:00+01:00  | rejects | UTC        | 5    |
        | skipped hour      | 2024-01-01T12:00:00+00:00  | accepts | close_time | 6    |

    Scenario: A skipped expected bar is accepted by the history but flagged as a stream gap
      Given a candle history with 5 valid 60-minute bars ending at "2024-01-01T10:00:00+00:00"
      When a valid bar closing at "2024-01-01T12:00:00+00:00" is offered to the candle history
      Then the candle history holds 6 bars
      And the history reports a gap of 1 missing expected bar before the last bar

    Scenario: History is bounded by max_history and evicts the oldest bar first
      Given a candle configuration with max_history 12, enabled rules "hammer", ema_period 8, stochastic 1,1,1 and sma_periods "5"
      And a candle history built from that configuration
      And the candle history's config has max_history 12
      When 17 valid consecutive 60-minute bars are offered
      Then the candle history holds 12 bars
      And the retained bars are the last 12 offered bars in order

    Scenario: A rejected bar in a full history neither consumes nor evicts anything
      Given a candle configuration with max_history 12, enabled rules "hammer", ema_period 8, stochastic 1,1,1 and sma_periods "5"
      And a candle history built from that configuration holding 12 valid bars
      When a bar with OHLC [9, 8, 10, 9] is offered to the candle history
      Then the candle history rejects it mentioning "ordering" and a remedy
      And the retained bars are unchanged
      And the next valid bar is accepted and evicts exactly the oldest bar
