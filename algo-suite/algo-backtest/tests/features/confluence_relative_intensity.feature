Feature: F4 relative intensity — direction from the frozen monthly quantiles (story 21, T4)
  Proves the third `direction_source` of `chain/filters/f4_news_context.py`,
  `intensity_relative` (spec CC-09..CC-12, CC-14, CC-20, CC-31; decisions D1..D3).
  F4 keeps its veto first (`event_intensity_veto_threshold`, an explicit `null` disables
  it as today). Once the veto has not fired, the current bar's event intensity I is
  compared with the decision month's frozen snapshot from `chain/intensity_history.py`
  (T3), injected explicitly — F4 never computes quantiles itself. With the registered
  `intensity_sign: -1`: I >= q90 → SELL, I <= q10 → BUY, strictly between → NEUTRAL
  (CC-11). `intensity_sign: 1` is the same rule unswapped (I >= q90 → BUY, I <= q10 →
  SELL), consistent with the static `intensity` mode. Equal quantiles are a degenerate
  snapshot: HOLD for every I, not a configuration error (CC-12). A WARMUP snapshot is
  HOLD with no fixed-threshold fallback (CC-14). The current intensity must have been
  available no later than the decision time; a later availability is a causal
  violation and raises (D2). Static `intensity` and `sentiment` modes are unchanged
  (CC-20).

  Result contract in relative mode: `filter_name` "f4_news_context" as today; enrichment
  `news_event_intensity` as today; the reason names the snapshot cutoff and the vote;
  metadata carries `sentiment_source_present` (as today) plus the snapshot provenance:
  `intensity_snapshot_cutoff`, `intensity_snapshot_status`, `intensity_q_low`,
  `intensity_q_high`, `intensity_sample_count`, `intensity_source_hash` (CC-31).

  Background:
    Given an in-memory news index with no sentiment source

  Rule: With sign -1 a high intensity sells, a low one buys and the interior is neutral (CC-11)

    Scenario Outline: intensity <intensity> against q10 0.2 / q90 0.8 with sign -1 is <recommendation> (<case>)
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-04-05T10:00:00Z" is <intensity>, available at "2016-04-05T10:00:00Z"
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's recommendation is "<recommendation>"
      And relative F4's result does not veto
      And relative F4's filter_name is "f4_news_context"
      And relative F4 enriches "news_event_intensity" with value <intensity>
      And relative F4's reason mentions "<reason>"

      Examples:
        | case                                 | intensity | recommendation | reason                       |
        | exactly at q90 sells                 | 0.8       | SELL           | >= q90 0.8                   |
        | above q90 sells                      | 0.95      | SELL           | intensity_sign=-1: SELL      |
        | exactly at q10 buys                  | 0.2       | BUY            | <= q10 0.2                   |
        | below q10 buys                       | 0.05      | BUY            | intensity_sign=-1: BUY       |
        | just above q10 is neutral            | 0.2001    | NEUTRAL        | : NEUTRAL                    |
        | midway is neutral                    | 0.5       | NEUTRAL        | cutoff 2016-04-01T00:00:00+00:00 |
        | just below q90 is neutral            | 0.7999    | NEUTRAL        | : NEUTRAL                    |

    Scenario Outline: intensity <intensity> with sign 1 is the unswapped mapping (<case>)
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign 1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-04-05T10:00:00Z" is <intensity>, available at "2016-04-05T10:00:00Z"
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's recommendation is "<recommendation>"
      And relative F4's result does not veto

      Examples:
        | case                 | intensity | recommendation |
        | at q90 buys          | 0.8       | BUY            |
        | at q10 sells         | 0.2       | SELL           |
        | interior is neutral  | 0.5       | NEUTRAL        |

    Scenario: the vote carries the snapshot's provenance for the audit trail
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-04-05T10:00:00Z" is 0.95, available at "2016-04-05T10:00:00Z"
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's metadata "intensity_snapshot_cutoff" is "2016-04-01T00:00:00+00:00"
      And relative F4's metadata "intensity_snapshot_status" is "READY"
      And relative F4's metadata "intensity_q_low" is 0.2
      And relative F4's metadata "intensity_q_high" is 0.8
      And relative F4's metadata "intensity_sample_count" is 30
      And relative F4's metadata "intensity_source_hash" is "ab12"
      And relative F4's metadata "sentiment_source_present" is false

  Rule: The decision month selects the snapshot; the month boundary is the fixed UTC cutoff (CC-09, CC-10)

    Scenario Outline: the same intensity 0.7 is <recommendation> at <timestamp> because <case>
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And a READY intensity snapshot for cutoff "2016-05-01T00:00:00Z" with q10 0.4, q90 0.6, sample_count 30 and source_hash "cd34"
      And the event intensity at "<timestamp>" is 0.7, available at "<timestamp>"
      When relative F4 applies to timestamp "<timestamp>" for pair "EURUSD"
      Then relative F4's recommendation is "<recommendation>"
      And relative F4's metadata "intensity_snapshot_cutoff" is "<cutoff>"

      Examples:
        | case                              | timestamp            | recommendation | cutoff                    |
        | April's q90 0.8 is not reached    | 2016-04-30T23:00:00Z | NEUTRAL        | 2016-04-01T00:00:00+00:00 |
        | May's q90 0.6 is crossed          | 2016-05-01T00:00:00Z | SELL           | 2016-05-01T00:00:00+00:00 |
        | still May on the Sunday open      | 2016-05-01T22:00:00Z | SELL           | 2016-05-01T00:00:00+00:00 |

    Scenario: a decision month without a snapshot fails fast naming the month
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-06-03T10:00:00Z" is 0.7, available at "2016-06-03T10:00:00Z"
      When relative F4 applies to timestamp "2016-06-03T10:00:00Z" for pair "EURUSD" and fails
      Then the relative F4 failure names "no intensity snapshot for cutoff 2016-06-01T00:00:00+00:00"

  Rule: Equal quantiles are a degenerate snapshot: HOLD for every intensity (CC-12)

    Scenario Outline: q10 == q90 == 0.5 holds at intensity <intensity> (<case>)
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.5, q90 0.5, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-04-05T10:00:00Z" is <intensity>, available at "2016-04-05T10:00:00Z"
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's recommendation is "HOLD"
      And relative F4's result does not veto
      And relative F4's reason mentions "degenerate snapshot: q10 == q90 == 0.5"

      Examples:
        | case                | intensity |
        | below both          | 0.4       |
        | exactly on both     | 0.5       |
        | above both          | 0.6       |

  Rule: A WARMUP snapshot holds; no static threshold is substituted (CC-14)

    Scenario Outline: WARMUP holds at intensity <intensity> (<case>)
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a WARMUP intensity snapshot for cutoff "2016-04-01T00:00:00Z" with sample_count 11
      And the event intensity at "2016-04-05T10:00:00Z" is <intensity>, available at "2016-04-05T10:00:00Z"
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's recommendation is "HOLD"
      And relative F4's result does not veto
      And relative F4's reason mentions "WARMUP"
      And relative F4's metadata "intensity_snapshot_status" is "WARMUP"
      And relative F4's metadata "intensity_q_low" is null
      And relative F4's metadata "intensity_q_high" is null

      Examples:
        | case                       | intensity |
        | an extreme high intensity  | 5.0       |
        | a low intensity above the veto | -0.4  |

  Rule: The veto still fires first, and a disabled veto never fires, in relative mode

    Scenario: an active high-risk event vetoes before the snapshot is consulted
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-04-05T10:00:00Z" is -0.7, available at "2016-04-05T10:00:00Z"
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's result vetoes
      And relative F4's recommendation is "ABSTAIN"
      And relative F4's reason mentions "active high-risk event"

    Scenario: with the veto disabled a very low intensity is simply a BUY under sign -1
      Given a news_context section with direction_source intensity_relative, veto null and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-04-05T10:00:00Z" is -5.0, available at "2016-04-05T10:00:00Z"
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's result does not veto
      And relative F4's recommendation is "BUY"

  Rule: The current intensity must be available no later than the decision time (D2)

    Scenario Outline: an intensity available at <available_at> is usable for a decision at 10:00 (<case>)
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-04-05T10:00:00Z" is 0.95, available at "<available_at>"
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's recommendation is "SELL"

      Examples:
        | case                     | available_at         |
        | published an hour before | 2016-04-05T09:00:00Z |
        | published at the minute  | 2016-04-05T10:00:00Z |

    Scenario: an intensity that became available after the decision time is a causal violation
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-04-05T10:00:00Z" is 0.95, available at "2016-04-05T10:01:00Z"
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD" and fails
      Then the relative F4 failure names "available at 2016-04-05T10:01:00+00:00, after the decision time 2016-04-05T10:00:00+00:00"

    Scenario: a decision minute without an availability record fails fast naming the minute
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      And the event intensity at "2016-04-05T10:00:00Z" is 0.95, available at "2016-04-05T10:00:00Z"
      And the event intensity at "2016-04-05T11:00:00Z" is 0.95
      When relative F4 applies to timestamp "2016-04-05T11:00:00Z" for pair "EURUSD" and fails
      Then the relative F4 failure names "no availability record for the event_intensity at 2016-04-05T11:00:00+00:00"
      And the relative F4 failure names "point-in-time provenance for every decision minute"

    Scenario: relative mode built without a snapshot source fails fast at construction
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      When relative F4 is built without a snapshot source and fails
      Then the relative F4 failure names "direction_source intensity_relative needs an intensity snapshot source"

    Scenario: relative mode built without an availability source fails fast at construction
      Given a news_context section with direction_source intensity_relative, veto -0.5 and intensity_sign -1
      And a READY intensity snapshot for cutoff "2016-04-01T00:00:00Z" with q10 0.2, q90 0.8, sample_count 30 and source_hash "ab12"
      When relative F4 is built without an availability source and fails
      Then the relative F4 failure names "direction_source intensity_relative needs the current intensity's availability"
      And the relative F4 failure names "availability is never inferred"

  Rule: The news_context section accepts intensity_relative and refuses the static thresholds under it

    Scenario Outline: a news_context section with direction_source intensity_relative parses (<case>)
      Given a news_context section with direction_source intensity_relative, veto <veto>, sentiment null and intensity_sign <sign>
      When the news-context config is parsed for strategy "confluence-a"
      Then the parsed news-context config has direction_source "intensity_relative", buy null, sell null and sign <parsed_sign>
      And the news-context mapping records direction_source "intensity_relative" and intensity_sign <parsed_sign>
      And the news-context mapping has no key "intensity_buy_threshold"

      Examples:
        | case                     | veto | sign   | parsed_sign |
        | registered sign -1       | -0.5 | -1     | -1          |
        | unswapped sign           | -0.5 | 1      | 1           |
        | sign omitted defaults 1  | null | absent | 1           |

    Scenario Outline: an invalid relative section fails fast naming the key and the strategy (<case>)
      Given a news_context section with direction_source <source>, intensity_buy_threshold <buy>, intensity_sell_threshold <sell> and intensity_sign <sign>
      When parsing the news-context config for strategy "confluence-a" fails
      Then the news-context config failure names "<message>"

      Examples:
        | case                              | source             | buy    | sell   | sign | message                                                                                                                        |
        | static thresholds under relative  | intensity_relative | 0.9    | 0.3    | -1   | strategy 'confluence-a': news_context declares ['intensity_buy_threshold', 'intensity_sell_threshold'] but direction_source is 'intensity_relative' |
        | one static threshold under relative | intensity_relative | absent | 0.3  | -1   | strategy 'confluence-a': news_context declares ['intensity_sell_threshold'] but direction_source is 'intensity_relative'      |
        | sign 0 under relative             | intensity_relative | absent | absent | 0    | strategy 'confluence-a': news_context.intensity_sign must be 1 or -1, got 0                                                   |
        | unknown source lists all three    | quantile           | absent | absent | 1    | strategy 'confluence-a': news_context.direction_source must be one of ['intensity', 'intensity_relative', 'sentiment'], got 'quantile' |

  Rule: The static intensity and sentiment modes are byte-for-byte the story-14 behaviour (CC-20)

    Scenario Outline: static intensity mode still decides from its fixed thresholds without any snapshot (<case>)
      Given a news_context section with direction_source intensity, veto -0.5, buy 0.9, sell 0.3 and intensity_sign <sign>
      And no intensity snapshot source
      And the event intensity at "2016-04-05T10:00:00Z" is <intensity>
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's recommendation is "<recommendation>"
      And relative F4's result does not veto
      And relative F4's metadata has no key "intensity_snapshot_cutoff"

      Examples:
        | case                         | sign | intensity | recommendation |
        | above the buy threshold buys | 1    | 1.4       | BUY            |
        | sign -1 swaps it into a sell | -1   | 1.4       | SELL           |
        | between the thresholds       | 1    | 0.6       | NEUTRAL        |

    Scenario Outline: sentiment mode still decides from per-symbol polarity (<case>)
      Given a news_context section with direction_source sentiment, veto -0.5 and sentiment threshold 0.15
      And no intensity snapshot source
      And the event intensity at "2016-04-05T10:00:00Z" is 0.56
      And the sentiment polarity for "EURUSD" at "2016-04-05T10:00:00Z" is <polarity>
      When relative F4 applies to timestamp "2016-04-05T10:00:00Z" for pair "EURUSD"
      Then relative F4's recommendation is "<recommendation>"
      And relative F4's result does not veto

      Examples:
        | case                              | polarity | recommendation |
        | positive polarity buys            | 0.42     | BUY            |
        | negative polarity sells           | -0.3     | SELL           |
        | polarity under the threshold      | 0.05     | ABSTAIN        |

    Scenario: a section without direction_source still defaults to sentiment
      Given a news_context section with event_intensity_veto_threshold=-0.5, sentiment_direction_threshold=0.15
      When the news-context config is parsed for strategy "hybrid"
      Then the parsed news-context config has direction_source "sentiment", buy null, sell null and sign 1
