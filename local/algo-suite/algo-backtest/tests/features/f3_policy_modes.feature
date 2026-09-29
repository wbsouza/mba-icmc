Feature: F3 explicit policy modes
  Story 22, task T6 (CND-09, CND-11, CND-12). The `pattern` section gains one key,
  `mode: legacy | advisory | required_entry` (default `legacy`). Legacy mode is
  byte-identical to the current filter: it reads `state.features["candlestick_pattern"]`
  and every scenario of f3_pattern.feature passes unchanged. The two new modes read
  the documented feature key `state.features["candle_evidence"]` (a CandleEvidence
  from candle_contract.feature, produced by the integration lane) and never touch
  `candlestick_pattern`.

  Registered eligibility (T1 ledger; sources: presentation slides 6-7 and webinar
  10:49-11:27, 26:54-27:07 "a candlestick buy signal and a close above the T-line";
  webinar 09:56-10:23 overbought above 80 / oversold below 20):
    - candidate directions = { polarity of every READY hit with polarity != 0 }
      union { confirmed_direction of a sequence CONFIRMED at this bar }.
    - direction +1 is satisfied when context is READY, t_line_position is ABOVE
      and stochastic_zone is not OVERBOUGHT and not UNDEFINED.
    - direction -1 is satisfied when context is READY, t_line_position is BELOW
      and stochastic_zone is not OVERSOLD and not UNDEFINED.
    - eligible = exactly one candidate direction and it is satisfied.
    - advisory: BUY / SELL when eligible, otherwise ABSTAIN; veto is False always,
      including on abstention (CND-11).
    - required_entry: BUY / SELL with veto False when eligible; otherwise
      recommendation ABSTAIN with veto True and a reason whose first token is one of
      the distinct codes "warmup" (evidence status WARMUP or context WARMUP),
      "neutral_only" (no candidate direction), "conflicting" (two candidate
      directions), "context" (one candidate direction not satisfied) (CND-12).
    - The reason always names the hit ids and the mode. filter_name stays "F3_pattern".
    - In advisory or required_entry mode a missing or non-CandleEvidence
      `candle_evidence` is a data-contract violation: ValueError naming
      "candle_evidence" and the mode.
  Evidence in the tables: hits are "id:polarity:status" triples; context is
  "status/t_line_position/stochastic_zone"; confirmation is the confirmed direction
  at this bar ("none", "1" or "-1").

  Rule: The mode key parses with a legacy default and rejects anything else

    Scenario Outline: pattern.mode parses (<case>)
      Given a pattern section <section>
      When the pattern config is parsed for strategy "baseline"
      Then the parsed pattern mode is "<mode>"
      And the parsed bullish patterns are "bullish_engulfing, hammer, morning_star"

      Examples:
        | case            | section                  | mode           |
        | absent          | {}                       | legacy         |
        | explicit legacy | {mode: legacy}           | legacy         |
        | advisory        | {mode: advisory}         | advisory       |
        | required entry  | {mode: required_entry}   | required_entry |

    Scenario Outline: an invalid pattern.mode fails fast (<case>)
      Given a pattern section <section>
      When parsing the pattern config for strategy "baseline" fails
      Then the pattern config failure names "<failure>"

      Examples:
        | case              | section                 | failure                                                                    |
        | unknown mode      | {mode: required}        | strategy 'baseline': pattern.mode must be one of legacy, advisory, required_entry |
        | wrong case        | {mode: Legacy}          | strategy 'baseline': pattern.mode must be one of legacy, advisory, required_entry |
        | integer           | {mode: 1}               | strategy 'baseline': pattern.mode must be one of legacy, advisory, required_entry |
        | null              | {mode: null}            | strategy 'baseline': pattern.mode must be one of legacy, advisory, required_entry |
        | list              | {mode: [advisory]}      | strategy 'baseline': pattern.mode must be one of legacy, advisory, required_entry |

    Scenario: The resolved mapping records the mode beside the vocabulary
      Given a pattern section {mode: advisory}
      When the pattern config is parsed for strategy "baseline"
      Then the pattern mapping is {"bullish_patterns": ["bullish_engulfing", "hammer", "morning_star"], "bearish_patterns": ["bearish_engulfing", "evening_star", "shooting_star"], "detector": "disabled", "mode": "advisory"}

  Rule: Legacy mode is byte-identical and ignores the new evidence key

    Scenario Outline: Legacy decisions are frozen with and without the mode key (<case>)
      Given a pattern section <section>
      And a detected candlestick pattern "<pattern>"
      When F3 is applied with that pattern config
      Then F3 recommends "<recommendation>" with reason mentioning "<pattern>"
      And F3 does not veto

      Examples:
        | case                        | section        | pattern           | recommendation |
        | default hammer              | {}             | hammer            | BUY            |
        | explicit legacy hammer      | {mode: legacy} | hammer            | BUY            |
        | default evening star        | {}             | evening_star      | SELL           |
        | explicit legacy shooting    | {mode: legacy} | shooting_star     | SELL           |

    Scenario: Legacy mode abstains on no pattern even when candle_evidence is present
      Given a pattern section {mode: legacy}
      And candle evidence with status "READY", hits "bullish_engulfing:1:READY", context "READY/ABOVE/NEUTRAL" and confirmation "none"
      And no candlestick pattern is present
      When F3 is applied with that pattern config
      Then F3 abstains with reason mentioning "no pattern"
      And F3 does not veto

    Scenario: Legacy mode still rejects an unknown candlestick_pattern name
      Given a pattern section {mode: legacy}
      And a detected candlestick pattern "not_a_real_pattern"
      When F3 is applied with that pattern config and the error is captured
      Then F3 raises an error naming "not_a_real_pattern"

    Scenario: Legacy mode produces the same FilterResult as the pre-mode filter on every legacy name
      Given a pattern section {mode: legacy}
      When F3 is applied to each of "bullish_engulfing, hammer, morning_star, bearish_engulfing, shooting_star, evening_star" and to no pattern
      Then every FilterResult equals the result of F3PatternFilter(PatternConfig()) on the same features

  Rule: Advisory mode recommends or abstains and never vetoes

    Scenario Outline: Advisory recommendations from evidence (<case>)
      Given a pattern section {mode: advisory}
      And candle evidence with status "<status>", hits "<hits>", context "<context>" and confirmation "<confirmation>"
      When F3 is applied with that pattern config
      Then F3 recommends "<recommendation>" with reason mentioning "<mention>"
      And F3 does not veto
      And F3's filter_name is "F3_pattern"

      Examples:
        | case                              | status | hits                                          | context               | confirmation | recommendation | mention           |
        | eligible long                     | READY  | bullish_engulfing:1:READY                     | READY/ABOVE/NEUTRAL   | none         | BUY            | bullish_engulfing |
        | eligible long, oversold           | READY  | hammer:1:READY,doji:0:READY                   | READY/ABOVE/OVERSOLD  | none         | BUY            | hammer            |
        | eligible short                    | READY  | dark_cloud_cover:-1:READY                     | READY/BELOW/NEUTRAL   | none         | SELL           | dark_cloud_cover  |
        | eligible short, overbought        | READY  | hanging_man:-1:READY                          | READY/BELOW/OVERBOUGHT| none         | SELL           | hanging_man       |
        | confirmed sequence alone          | READY  |                                               | READY/ABOVE/NEUTRAL   | 1            | BUY            | doji_engulfing    |
        | no hits                           | READY  |                                               | READY/ABOVE/NEUTRAL   | none         | ABSTAIN        | neutral_only      |
        | neutral only                      | READY  | doji:0:READY,spinning_top:0:READY             | READY/ABOVE/NEUTRAL   | none         | ABSTAIN        | neutral_only      |
        | conflicting hits                  | READY  | hammer:1:READY,hanging_man:-1:READY           | READY/ABOVE/NEUTRAL   | none         | ABSTAIN        | conflicting       |
        | hit against confirmation          | READY  | hammer:1:READY                                | READY/ABOVE/NEUTRAL   | -1           | ABSTAIN        | conflicting       |
        | long below the T-line             | READY  | bullish_engulfing:1:READY                     | READY/BELOW/NEUTRAL   | none         | ABSTAIN        | context           |
        | long on the T-line                | READY  | bullish_engulfing:1:READY                     | READY/ON/NEUTRAL      | none         | ABSTAIN        | context           |
        | long while overbought             | READY  | bullish_engulfing:1:READY                     | READY/ABOVE/OVERBOUGHT| none         | ABSTAIN        | context           |
        | short while oversold              | READY  | bearish_engulfing:-1:READY                    | READY/BELOW/OVERSOLD  | none         | ABSTAIN        | context           |
        | undefined stochastic              | READY  | bullish_engulfing:1:READY                     | READY/ABOVE/UNDEFINED | none         | ABSTAIN        | context           |
        | evidence warming up               | WARMUP | doji:0:READY,hammer:0:WARMUP                  | READY/ABOVE/NEUTRAL   | none         | ABSTAIN        | warmup            |
        | context warming up                | READY  | bullish_engulfing:1:READY                     | WARMUP/WARMUP/UNDEFINED | none       | ABSTAIN        | warmup            |

    Scenario: Advisory mode requires the evidence key
      Given a pattern section {mode: advisory}
      And no candle evidence is present
      When F3 is applied with that pattern config and the error is captured
      Then F3 raises an error naming "candle_evidence"
      And that error names "advisory"

  Rule: Required-entry mode grants eligibility to exactly one satisfied direction and vetoes everything else with a distinct reason

    Scenario Outline: Required-entry decisions (<case>)
      Given a pattern section {mode: required_entry}
      And candle evidence with status "<status>", hits "<hits>", context "<context>" and confirmation "<confirmation>"
      When F3 is applied with that pattern config
      Then F3 recommends "<recommendation>" with reason mentioning "<mention>"
      And F3's veto is <veto>
      And F3's filter_name is "F3_pattern"

      Examples:
        | case                              | status | hits                                          | context                | confirmation | recommendation | veto  | mention           |
        | eligible long                     | READY  | bullish_engulfing:1:READY                     | READY/ABOVE/NEUTRAL    | none         | BUY            | false | bullish_engulfing |
        | eligible long with confirmation   | READY  | bullish_engulfing:1:READY,doji:0:READY        | READY/ABOVE/OVERSOLD   | 1            | BUY            | false | bullish_engulfing |
        | eligible short                    | READY  | bearish_kicker:-1:READY                       | READY/BELOW/NEUTRAL    | none         | SELL           | false | bearish_kicker    |
        | eligible short from confirmation  | READY  | doji:0:READY                                  | READY/BELOW/NEUTRAL    | -1           | SELL           | false | doji_engulfing    |
        | evidence warming up               | WARMUP | doji:0:READY,hammer:0:WARMUP                  | READY/ABOVE/NEUTRAL    | none         | ABSTAIN        | true  | warmup            |
        | context warming up                | READY  | bullish_engulfing:1:READY                     | WARMUP/WARMUP/UNDEFINED| none         | ABSTAIN        | true  | warmup            |
        | no hits                           | READY  |                                               | READY/ABOVE/NEUTRAL    | none         | ABSTAIN        | true  | neutral_only      |
        | neutral only                      | READY  | doji:0:READY,doji_dragonfly:0:READY           | READY/ABOVE/NEUTRAL    | none         | ABSTAIN        | true  | neutral_only      |
        | conflicting hits                  | READY  | hammer:1:READY,hanging_man:-1:READY           | READY/ABOVE/NEUTRAL    | none         | ABSTAIN        | true  | conflicting       |
        | hit against confirmation          | READY  | bullish_kicker:1:READY                        | READY/ABOVE/NEUTRAL    | -1           | ABSTAIN        | true  | conflicting       |
        | long below the T-line             | READY  | bullish_engulfing:1:READY                     | READY/BELOW/NEUTRAL    | none         | ABSTAIN        | true  | context           |
        | long while overbought             | READY  | morning_star:1:READY                          | READY/ABOVE/OVERBOUGHT | none         | ABSTAIN        | true  | context           |
        | short above the T-line            | READY  | evening_star:-1:READY                         | READY/ABOVE/NEUTRAL    | none         | ABSTAIN        | true  | context           |
        | short while oversold              | READY  | shooting_star:-1:READY                        | READY/BELOW/OVERSOLD   | none         | ABSTAIN        | true  | context           |
        | undefined stochastic              | READY  | piercing_line:1:READY                         | READY/ABOVE/UNDEFINED  | none         | ABSTAIN        | true  | context           |

    Scenario: Veto reasons are distinct codes
      Given a pattern section {mode: required_entry}
      When F3 is applied to the four veto fixtures warmup, neutral_only, conflicting and context
      Then the four reasons start with four different codes "warmup", "neutral_only", "conflicting" and "context"

    Scenario: Required-entry mode requires the evidence key
      Given a pattern section {mode: required_entry}
      And no candle evidence is present
      When F3 is applied with that pattern config and the error is captured
      Then F3 raises an error naming "candle_evidence"
      And that error names "required_entry"

    Scenario: Required-entry mode rejects a malformed evidence value
      Given a pattern section {mode: required_entry}
      And the candle evidence feature is the string "bullish_engulfing"
      When F3 is applied with that pattern config and the error is captured
      Then F3 raises an error naming "candle_evidence"

    Scenario: A vetoed result carries the evidence beside the decision
      Given a pattern section {mode: required_entry}
      And candle evidence with status "READY", hits "hammer:1:READY,hanging_man:-1:READY", context "READY/ABOVE/NEUTRAL" and confirmation "none"
      When F3 is applied with that pattern config
      Then F3's veto is true
      And F3's enrichment records candle_hits "hammer,hanging_man", candle_mode "required_entry" and candle_veto_reason "conflicting"
