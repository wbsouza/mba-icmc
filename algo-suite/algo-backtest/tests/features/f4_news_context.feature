Feature: F4 — News-context filter
  Proves the F4 news-context filter (specs.md §11.3.2: "Recommends direction by net
  sentiment; vetoes on active high-risk events") against **real** Spec 03 (`algo-score`)
  Parquet outputs — not hand-invented fixture values.

  The event-feature scenarios below write the real, materialized January-2020 GDELT
  daily Goldstein Scale values (`data/parquet/events/_features/gdelt/year=2020/
  month=01/data.parquet`, built by `algo-score events --kind gdelt`, 44640 real rows)
  through the same `algo_core.repository.parquet.ParquetRepository` writer + the real
  `GdeltFeature`/`SymbolSentimentFeature` models Spec 03 uses — the real repository
  round-trip and the real production data, not a synthetic invented fixture. 2020-01-01
  is genuinely the month's most conflictual day (event_intensity -1.579, the Soleimani-
  strike news cycle); 2020-01-15 is genuinely calm (0.562).

  Per-symbol sentiment (`SymbolSentimentFeature`) is not yet materialized for this pilot
  month — see `f4_news_context.py`'s module docstring and `docs/technical-debt.md`
  TD-48 (GDELT Web News NGrams 3.0 full-month backfill is ~500 GB / ~90 hours at the
  current adapter's throughput). Sentiment-direction scenarios below write real-shaped
  `SymbolSentimentFeature` rows through the same repository round-trip to prove F4's
  direction logic ahead of that data landing for real.

  Rule: F4 vetoes when the real GDELT event_intensity crosses the configured threshold

    Scenario: The real most-conflictual January 2020 day vetoes
      Given the real January 2020 GDELT event-feature Parquet
      And a news-context veto threshold of -0.5 and no sentiment threshold
      When F4 applies to timestamp "2020-01-01T00:05:00+00:00" for pair "EURUSD"
      Then F4's result vetoes
      And F4's filter_name is "f4_news_context"
      And F4's reason mentions "active high-risk event"
      And F4's recommendation is "ABSTAIN"
      And F4 enriches "news_event_intensity" with value -1.5791368337311142
      And F4's metadata "sentiment_source_present" is false

    Scenario: An event_intensity exactly at the veto threshold vetoes (boundary is inclusive)
      Given the real January 2020 GDELT event-feature Parquet
      And a news-context veto threshold of -1.5791368337311142 and no sentiment threshold
      When F4 applies to timestamp "2020-01-01T00:05:00+00:00" for pair "EURUSD"
      Then F4's result vetoes

    Scenario: A real calm January 2020 day does not veto
      Given the real January 2020 GDELT event-feature Parquet
      And a news-context veto threshold of -0.5 and no sentiment threshold
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's result does not veto
      And F4's filter_name is "f4_news_context"
      And F4's recommendation is "ABSTAIN"
      And F4's reason mentions "no clear net sentiment signal"
      And F4 enriches "news_event_intensity" with value 0.5615042436044383

  Rule: F4 recommends a direction from real-shaped per-symbol sentiment, else ABSTAINs

    Scenario: Positive net sentiment above the direction threshold recommends BUY
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-15T00:05:00+00:00" with polarity 0.42
      And a news-context veto threshold of -0.5 and sentiment threshold 0.15
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's recommendation is "BUY"
      And F4's result does not veto
      And F4's filter_name is "f4_news_context"
      And F4 enriches "news_sentiment_score" with value 0.42
      And F4 enriches "news_event_intensity" with value 0.5615042436044383
      And F4's reason mentions "net sentiment"

    Scenario: Sentiment for a different pair in the same Parquet file is ignored
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "USDJPY" at "2020-01-15T00:05:00+00:00" with polarity 0.9
      And a news-context veto threshold of -0.5 and sentiment threshold 0.15
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's recommendation is "ABSTAIN"

    Scenario: Negative net sentiment above the direction threshold recommends SELL
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-15T00:05:00+00:00" with polarity -0.3
      And a news-context veto threshold of -0.5 and sentiment threshold 0.15
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's recommendation is "SELL"
      And F4's filter_name is "f4_news_context"
      And F4 enriches "news_sentiment_score" with value -0.3

    Scenario: Sentiment magnitude exactly at the direction threshold still recommends (boundary is inclusive)
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-15T00:05:00+00:00" with polarity 0.15
      And a news-context veto threshold of -0.5 and sentiment threshold 0.15
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's recommendation is "BUY"

    Scenario: Zero polarity at a zero direction threshold ABSTAINs, never a directional guess
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-15T00:05:00+00:00" with polarity 0
      And a news-context veto threshold of -0.5 and sentiment threshold 0
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's recommendation is "ABSTAIN"

    Scenario: Sentiment below the direction threshold ABSTAINs rather than guess
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-15T00:05:00+00:00" with polarity 0.05
      And a news-context veto threshold of -0.5 and sentiment threshold 0.15
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's recommendation is "ABSTAIN"

    Scenario: A disabled sentiment threshold ABSTAINs even with real sentiment present
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-15T00:05:00+00:00" with polarity 0.9
      And a news-context veto threshold of -0.5 and no sentiment threshold
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's recommendation is "ABSTAIN"

    Scenario: A high-risk event vetoes even with strong positive sentiment
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-01T00:05:00+00:00" with polarity 0.9
      And a news-context veto threshold of -0.5 and sentiment threshold 0.15
      When F4 applies to timestamp "2020-01-01T00:05:00+00:00" for pair "EURUSD"
      Then F4's result vetoes
      And F4's recommendation is "ABSTAIN"
      And F4 enriches "news_event_intensity" with value -1.5791368337311142

  Rule: The sentiment index only ever indexes rows matching both the queried pair and a real polarity

    Scenario: A null-polarity row for the queried pair is excluded from the loaded index
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-15T00:05:00+00:00" with a null polarity
      When the news-context index is loaded for "EURUSD"
      Then the loaded index has no sentiment entry for "EURUSD" at "2020-01-15T00:05:00+00:00"

  Rule: The mandatory GDELT event-feature Parquet must exist — a missing file fails fast

    Scenario: Loading the index for a month with no materialized GDELT event Parquet fails fast
      Given no GDELT event-feature Parquet exists for 2020-02
      When loading the news-context index for 2020-02 fails
      Then the failure names "missing real Spec 03 GDELT event-feature Parquet"

  Rule: A timestamp outside the materialized month fails fast, never silently ABSTAINs

    Scenario: Applying F4 to an uncovered minute fails fast
      Given the real January 2020 GDELT event-feature Parquet
      And a news-context veto threshold of -0.5 and no sentiment threshold
      When F4 applies to timestamp "2020-02-01T00:05:00+00:00" for pair "EURUSD" and fails
      Then the failure names "no GDELT event_intensity"

  Rule: The absent sentiment Parquet is a tracked, auditable state, not a silent gap

    Scenario: A result's metadata records whether the sentiment source file was present
      Given the real January 2020 GDELT event-feature Parquet
      And a news-context veto threshold of -0.5 and no sentiment threshold
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's metadata "sentiment_source_present" is false

    Scenario: A result's metadata records a present sentiment source file
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-15T00:05:00+00:00" with polarity 0.42
      And a news-context veto threshold of -0.5 and sentiment threshold 0.15
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's metadata "sentiment_source_present" is true

  Rule: A disabled threshold never gates on that half of the filter

    Scenario: A null veto threshold means F4 never vetoes
      Given the real January 2020 GDELT event-feature Parquet
      And a news-context veto threshold of null and no sentiment threshold
      When F4 applies to timestamp "2020-01-01T00:05:00+00:00" for pair "EURUSD"
      Then F4's result does not veto

  Rule: F4's thresholds come from the strategy config.yaml news_context section

    Scenario Outline: a complete news_context section parses into a NewsContextConfig (<case>)
      Given a news_context section with event_intensity_veto_threshold=<veto>, sentiment_direction_threshold=<direction>
      When the news-context config is parsed for strategy "hybrid"
      Then the parsed news-context config has event_intensity_veto_threshold <veto>
      And the parsed news-context config has sentiment_direction_threshold <direction>

      Examples:
        | case                         | veto | direction |
        | both thresholds set          | -0.5 | 0.15      |
        | veto disabled by null        | null | 0.15      |
        | direction disabled by null   | -0.5 | null      |
        | both disabled                | null | null      |
        | stricter veto                | -2.0 | 0.3       |

    Scenario Outline: a news_context section missing <key> fails fast naming the key and the strategy
      Given a news_context section missing "<key>"
      When parsing the news-context config for strategy "hybrid" fails
      Then the news-context config failure names "strategy 'hybrid': news_context.<key> is missing"

      Examples:
        | key                            |
        | event_intensity_veto_threshold |
        | sentiment_direction_threshold  |

    Scenario Outline: a non-numeric news_context value fails fast (<key>)
      Given a news_context section whose "<key>" is the string "soon"
      When parsing the news-context config for strategy "hybrid" fails
      Then the news-context config failure names "strategy 'hybrid': news_context.<key> must be a number"

      Examples:
        | key                            |
        | event_intensity_veto_threshold |
        | sentiment_direction_threshold  |

  Rule: With direction_source intensity, F4's direction comes from the event intensity itself (story 14)
    The veto still fires first; between the two thresholds F4 is NEUTRAL, and intensity_sign
    -1 swaps BUY and SELL so the Goldstein sign convention is a registered cell, not a guess.

    Scenario Outline: intensity <intensity> with buy <buy>, sell <sell>, sign <sign> recommends <recommendation> (<case>)
      Given a materialized GDELT event_intensity of <intensity> at "2020-01-15T00:05:00+00:00"
      And a news-context config with veto -0.5, direction_source intensity, buy <buy>, sell <sell>, sign <sign>
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's recommendation is "<recommendation>"
      And F4's result <veto>
      And F4 enriches "news_event_intensity" with value <intensity>
      And F4's reason mentions "<reason>"

      Examples:
        | case                              | intensity | buy | sell | sign | recommendation | veto          | reason                                     |
        | at the buy threshold buys         | 0.9       | 0.9 | 0.3  | 1    | BUY            | does not veto | intensity_buy_threshold=0.9                |
        | above the buy threshold buys      | 1.4       | 0.9 | 0.3  | 1    | BUY            | does not veto | event_intensity=1.4000                     |
        | at the sell threshold sells       | 0.3       | 0.9 | 0.3  | 1    | SELL           | does not veto | intensity_sell_threshold=0.3               |
        | below the sell threshold sells    | -0.2      | 0.9 | 0.3  | 1    | SELL           | does not veto | : SELL                                     |
        | between the thresholds is neutral | 0.6       | 0.9 | 0.3  | 1    | NEUTRAL        | does not veto | : NEUTRAL                                  |
        | sign -1 swaps a buy into a sell   | 1.4       | 0.9 | 0.3  | -1   | SELL           | does not veto | intensity_sign=-1                          |
        | sign -1 swaps a sell into a buy   | -0.2      | 0.9 | 0.3  | -1   | BUY            | does not veto | intensity_sign=-1                          |
        | sign -1 keeps neutral neutral     | 0.6       | 0.9 | 0.3  | -1   | NEUTRAL        | does not veto | : NEUTRAL                                  |
        | the veto still fires first        | -0.7      | 0.9 | -1.0 | 1    | ABSTAIN        | vetoes        | active high-risk event                     |
        | veto at the boundary beats a sell | -0.5      | 0.9 | 0.3  | -1   | ABSTAIN        | vetoes        | event_intensity=-0.5000 <= veto threshold  |

    Scenario Outline: a news_context section with direction_source intensity parses its thresholds and sign (<case>)
      Given a news_context section with direction_source <source>, intensity_buy_threshold <buy>, intensity_sell_threshold <sell> and intensity_sign <sign>
      When the news-context config is parsed for strategy "news-rule"
      Then the parsed news-context config has direction_source "<source>", buy <buy>, sell <sell> and sign <sign>

      Examples:
        | case                    | source    | buy | sell | sign   |
        | placeholders, sign 1    | intensity | 0.9 | 0.3  | 1      |
        | negative band, sign -1  | intensity | 0.0 | -1.0 | -1     |
        | sign omitted defaults 1 | intensity | 0.9 | 0.3  | absent |

    Scenario: a news_context section without direction_source defaults to sentiment with no intensity thresholds
      Given a news_context section with event_intensity_veto_threshold=-0.5, sentiment_direction_threshold=0.15
      When the news-context config is parsed for strategy "hybrid"
      Then the parsed news-context config has direction_source "sentiment", buy null, sell null and sign 1

    Scenario Outline: an invalid direction-source section fails fast naming the key and the strategy (<case>)
      Given a news_context section with direction_source <source>, intensity_buy_threshold <buy>, intensity_sell_threshold <sell> and intensity_sign <sign>
      When parsing the news-context config for strategy "news-rule" fails
      Then the news-context config failure names "<message>"

      Examples:
        | case                         | source    | buy    | sell   | sign   | message                                                                                                             |
        | missing buy threshold        | intensity | absent | 0.3    | 1      | strategy 'news-rule': news_context.intensity_buy_threshold is missing                                              |
        | missing sell threshold       | intensity | 0.9    | absent | 1      | strategy 'news-rule': news_context.intensity_sell_threshold is missing                                             |
        | buy equal to sell            | intensity | 0.3    | 0.3    | 1      | strategy 'news-rule': news_context.intensity_buy_threshold (0.3) must be strictly above intensity_sell_threshold (0.3) |
        | buy below sell               | intensity | 0.1    | 0.3    | 1      | strategy 'news-rule': news_context.intensity_buy_threshold (0.1) must be strictly above intensity_sell_threshold (0.3) |
        | non-numeric buy threshold    | intensity | soon   | 0.3    | 1      | strategy 'news-rule': news_context.intensity_buy_threshold must be a number                                        |
        | unknown source               | goldstein | 0.9    | 0.3    | 1      | strategy 'news-rule': news_context.direction_source must be one of ['intensity', 'intensity_relative', 'sentiment'], got 'goldstein'      |
        | sign 0                       | intensity | 0.9    | 0.3    | 0      | strategy 'news-rule': news_context.intensity_sign must be 1 or -1, got 0                                            |
        | sign true                    | intensity | 0.9    | 0.3    | true   | strategy 'news-rule': news_context.intensity_sign must be 1 or -1, got True                                         |
        | thresholds under sentiment   | sentiment | 0.9    | 0.3    | 1      | strategy 'news-rule': news_context declares ['intensity_buy_threshold', 'intensity_sell_threshold'] but direction_source is 'sentiment' |
