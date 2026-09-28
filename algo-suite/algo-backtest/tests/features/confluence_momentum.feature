Feature: F1 momentum context — the allowed side from the sign of a lagged close return (story 21, T2)
  Proves the selectable F1 variant `momentum_context` in `chain/filters/f1_trend.py`
  (spec CC-06..CC-08, CC-20, CC-28; decision D8). The variant votes the side the
  20-day price momentum allows: with L = `momentum_context.lookback_bars` completed
  closes of lag (480 on H1, 120 on H4 — both 480 scheduled trading hours), the return
  `close[t] / close[t-L] - 1` is positive → BUY, negative → SELL, exactly zero →
  NEUTRAL. It never vetoes and does not inherit the original F1's cross-timeframe
  conflict veto. Until L+1 valid completed closes exist it is in WARMUP: ABSTAIN with
  reason WARMUP and no directional vote (CC-07). Once history is expected, a missing,
  nonfinite, nonpositive, duplicated or out-of-order close is a hard, explained failure
  (CC-08), never silently skipped.

  The closes come from a pure, bounded `MomentumHistory(lookback_bars)` fed one
  completed close at a time (`push(close_time, close)`, UTC close times strictly
  increasing); it keeps only the most recent L+1 closes. The integration lane (T13)
  later feeds it from the same closed-bar clock the decision path uses.

  Result contract: `filter_name` stays "F1_trend" (the runtime name the agreement
  terminal's voter map expects for `f1_trend`); the reason mentions "momentum_context";
  enrichment `momentum_return` carries the computed return once ready; metadata carries
  `momentum_lookback_bars`, `momentum_sample_count` and `momentum_status`
  ("READY" or "WARMUP").

  Rule: With L+1 valid closes the vote is the sign of close[t] / close[t-L] - 1 (CC-06, CC-28)
    Only the newest and the L-th-older close matter; every close in between is
    deliberately set to a distracting value to prove it plays no part.

    Scenario Outline: with L+1 closes, <case>
      Given a momentum context with lookback_bars <L>
      And the momentum history is fed <n> closes every <clock> minutes from 2016-03-01T00:00:00Z, the first <first>, the last <last> and every other close <middle>
      When the momentum context filter is applied at the last close
      Then the momentum vote is "<vote>" with no veto
      And the momentum filter_name is "F1_trend"
      And the momentum reason mentions "momentum_context"
      And the momentum result enriches "momentum_return" with value <return>
      And the momentum metadata "momentum_status" is "READY"
      And the momentum metadata "momentum_lookback_bars" is <L>
      And the momentum metadata "momentum_sample_count" is <n>

      Examples: H1, L = 480 (481 hourly closes)
        | case                              | L   | n   | clock | first  | last   | middle | vote    | return |
        | last above the lagged close buys  | 480 | 481 | 60    | 1.1000 | 1.1055 | 1.2000 | BUY     | 0.005  |
        | last below the lagged close sells | 480 | 481 | 60    | 1.1000 | 1.0945 | 1.0000 | SELL    | -0.005 |
        | last equal to the lagged close    | 480 | 481 | 60    | 1.1000 | 1.1000 | 1.3000 | NEUTRAL | 0.0    |

      Examples: H4, L = 120 (121 four-hourly closes)
        | case                              | L   | n   | clock | first  | last   | middle | vote    | return |
        | last above the lagged close buys  | 120 | 121 | 240   | 1.2500 | 1.2625 | 1.1000 | BUY     | 0.01   |
        | last below the lagged close sells | 120 | 121 | 240   | 1.2500 | 1.2375 | 1.4000 | SELL    | -0.01  |
        | last equal to the lagged close    | 120 | 121 | 240   | 1.2500 | 1.2500 | 0.9000 | NEUTRAL | 0.0    |

    Scenario: the history is bounded to L+1 closes, so the lagged close is the L-th older one, not the first ever pushed
      Given a momentum context with lookback_bars 2
      And the momentum history is fed these closes:
        | close_time           | close |
        | 2016-03-01T00:00:00Z | 1.0   |
        | 2016-03-01T01:00:00Z | 2.0   |
        | 2016-03-01T02:00:00Z | 3.0   |
        | 2016-03-01T03:00:00Z | 1.5   |
      When the momentum context filter is applied at the last close
      Then the momentum vote is "SELL" with no veto
      And the momentum result enriches "momentum_return" with value -0.25
      And the momentum metadata "momentum_sample_count" is 3

    Scenario: the momentum variant never vetoes, even on the original F1's conflict features
      Given a momentum context with lookback_bars 2
      And the momentum history is fed these closes:
        | close_time           | close  |
        | 2016-03-01T00:00:00Z | 1.1000 |
        | 2016-03-01T01:00:00Z | 1.1010 |
        | 2016-03-01T02:00:00Z | 1.1020 |
      And the bar's features carry trend_direction 0.8, trend_strength 30.0 and higher_tf_trend_direction -0.5
      When the momentum context filter is applied at the last close
      Then the momentum vote is "BUY" with no veto
      And the momentum reason does not mention "conflict"

  Rule: Fewer than L+1 valid closes is WARMUP: ABSTAIN, no direction, no error (CC-07)

    Scenario Outline: short of L+1 closes, <case>
      Given a momentum context with lookback_bars <L>
      And the momentum history is fed <n> closes every <clock> minutes from 2016-03-01T00:00:00Z, the first 1.1000, the last 1.2000 and every other close 1.1500
      When the momentum context filter is applied at the last close
      Then the momentum vote is "<vote>" with no veto
      And the momentum metadata "momentum_status" is "<status>"
      And the momentum metadata "momentum_sample_count" is <n>
      And the momentum reason mentions "<reason>"

      Examples:
        | case                                   | L   | n   | clock | vote    | status | reason                          |
        | H1: exactly L closes is one short      | 480 | 480 | 60    | ABSTAIN | WARMUP | WARMUP: 480 of 481 closes       |
        | H4: exactly L closes is one short      | 120 | 120 | 240   | ABSTAIN | WARMUP | WARMUP: 120 of 121 closes       |
        | two closes are two short of L+1        | 3   | 2   | 60    | ABSTAIN | WARMUP | WARMUP: 2 of 4 closes           |
        | L+1 closes end the warmup              | 3   | 4   | 60    | BUY     | READY  | momentum_context                |

    Scenario: an empty history is WARMUP, not a missing-data failure
      Given a momentum context with lookback_bars 480
      And the momentum history is fed no closes
      When the momentum context filter is applied at 2016-03-01T00:00:00Z
      Then the momentum vote is "ABSTAIN" with no veto
      And the momentum metadata "momentum_status" is "WARMUP"
      And the momentum metadata "momentum_sample_count" is 0
      And the momentum result does not enrich "momentum_return"

  Rule: Malformed price history is a hard, explained failure, never repaired or skipped (CC-08)

    Scenario Outline: pushing <case> is rejected naming the offending close
      Given a momentum context with lookback_bars 2
      And the momentum history is fed these closes:
        | close_time           | close  |
        | 2016-03-01T00:00:00Z | 1.1000 |
        | 2016-03-01T01:00:00Z | 1.1010 |
      When the momentum history is pushed close_time "<close_time>" with close <close> and fails
      Then the momentum failure names "<fragment>"
      And the momentum failure names "MomentumHistory"

      Examples:
        | case                    | close_time           | close  | fragment                                                        |
        | a NaN close             | 2016-03-01T02:00:00Z | nan    | close must be finite and > 0, got nan at 2016-03-01T02:00:00+00:00 |
        | an infinite close       | 2016-03-01T02:00:00Z | inf    | close must be finite and > 0, got inf at 2016-03-01T02:00:00+00:00 |
        | a zero close            | 2016-03-01T02:00:00Z | 0.0    | close must be finite and > 0, got 0.0 at 2016-03-01T02:00:00+00:00 |
        | a negative close        | 2016-03-01T02:00:00Z | -1.1   | close must be finite and > 0, got -1.1 at 2016-03-01T02:00:00+00:00 |
        | a duplicated close time | 2016-03-01T01:00:00Z | 1.1020 | close_time 2016-03-01T01:00:00+00:00 is not after the last close 2016-03-01T01:00:00+00:00 |
        | an out-of-order close   | 2016-03-01T00:30:00Z | 1.1020 | close_time 2016-03-01T00:30:00+00:00 is not after the last close 2016-03-01T01:00:00+00:00 |

    Scenario: a naive close time is rejected, the history is UTC end to end
      Given a momentum context with lookback_bars 2
      And the momentum history is fed no closes
      When the momentum history is pushed a naive close_time "2016-03-01T02:00:00" with close 1.1 and fails
      Then the momentum failure names "close_time must be timezone-aware UTC"

    Scenario: a rejected close leaves the history unchanged
      Given a momentum context with lookback_bars 2
      And the momentum history is fed these closes:
        | close_time           | close  |
        | 2016-03-01T00:00:00Z | 1.1000 |
        | 2016-03-01T01:00:00Z | 1.1010 |
      When the momentum history is pushed close_time "2016-03-01T02:00:00Z" with close nan and fails
      And the momentum context filter is applied at 2016-03-01T01:00:00Z
      Then the momentum metadata "momentum_sample_count" is 2
      And the momentum metadata "momentum_status" is "WARMUP"

  Rule: momentum_context.lookback_bars comes from the strategy config.yaml and is a positive integer

    Scenario Outline: a momentum_context section with lookback_bars <lookback> parses (<case>)
      Given a momentum_context section with lookback_bars <lookback>
      When the momentum-context config is parsed for strategy "confluence-a"
      Then the parsed momentum-context config has lookback_bars <lookback>
      And the momentum-context mapping records lookback_bars <lookback>

      Examples:
        | case                 | lookback |
        | registered H1 window | 480      |
        | registered H4 window | 120      |
        | the smallest lag     | 1        |

    Scenario Outline: an invalid lookback_bars fails fast naming the key and the strategy (<case>)
      Given a momentum_context section with lookback_bars <lookback>
      When parsing the momentum-context config for strategy "confluence-a" fails
      Then the momentum-context config failure names "strategy 'confluence-a': momentum_context.lookback_bars must be a positive integer"
      And the momentum-context config failure names "got <shown>"

      Examples:
        | case              | lookback | shown  |
        | zero              | 0        | 0      |
        | negative          | -480     | -480   |
        | a fraction        | 480.5    | 480.5  |
        | a whole float     | 480.0    | 480.0  |
        | a boolean         | true     | True   |
        | a string          | "480"    | '480'  |
        | null              | null     | None   |

    Scenario: a momentum_context section missing lookback_bars fails fast
      Given a momentum_context section missing "lookback_bars"
      When parsing the momentum-context config for strategy "confluence-a" fails
      Then the momentum-context config failure names "strategy 'confluence-a': momentum_context.lookback_bars is missing"

    Scenario: an unknown momentum_context key fails fast instead of being ignored
      Given a momentum_context section with lookback_bars 480 and an extra key "window_days" of 20
      When parsing the momentum-context config for strategy "confluence-a" fails
      Then the momentum-context config failure names "momentum_context has unknown keys ['window_days']"

  Rule: The original F1 trend filter is untouched when the momentum variant is not selected (CC-20)

    Scenario Outline: the original three-feature F1 keeps its <case>
      Given trend_direction <trend_direction>, trend_strength <trend_strength> and higher_tf_trend_direction <higher>
      When the original F1 trend filter is applied
      Then the original F1 recommends "<recommendation>" with veto <veto>
      And the original F1 enriches "trend_score" with value <trend_score>

      Examples:
        | case                        | trend_direction | trend_strength | higher | recommendation | veto  | trend_score |
        | direction-conflict veto     | 0.8             | 30.0           | -0.5   | NEUTRAL        | true  | absent      |
        | aligned uptrend buy         | 0.8             | 40.0           | 0.3    | BUY            | false | 0.32        |
        | aligned downtrend sell      | -0.5            | 60.0           | -0.2   | SELL           | false | -0.3        |
        | flat primary is neutral     | 0.0             | 10.0           | 0.5    | NEUTRAL        | false | 0.0         |

    Scenario: the original F1 still fails fast on a missing feature
      Given a state missing "trend_direction"
      When the original F1 trend filter is applied
      Then the original F1 raises an error naming "trend_direction"
