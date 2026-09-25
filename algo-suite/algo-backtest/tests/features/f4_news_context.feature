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

    Scenario: Zero polarity at a zero direction threshold recommends SELL, not BUY
      Given the real January 2020 GDELT event-feature Parquet
      And a real SymbolSentimentFeature row for "EURUSD" at "2020-01-15T00:05:00+00:00" with polarity 0
      And a news-context veto threshold of -0.5 and sentiment threshold 0
      When F4 applies to timestamp "2020-01-15T00:05:00+00:00" for pair "EURUSD"
      Then F4's recommendation is "SELL"

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

  Rule: news_context.* thresholds resolve via the shared algo_core.config loader

    Scenario: a configured news_context section resolves both thresholds
      Given a news_context config with event_intensity_veto_threshold=-0.5, sentiment_direction_threshold=0.15
      When the news-context config is loaded
      Then the loaded config has event_intensity_veto_threshold -0.5
      And the loaded config has sentiment_direction_threshold 0.15

    Scenario: an explicitly null threshold disables that half of the filter
      Given a news_context config with event_intensity_veto_threshold=null, sentiment_direction_threshold=0.15
      When the news-context config is loaded
      Then the loaded config has event_intensity_veto_threshold null

    Scenario: a missing news_context section fails fast
      Given a news_context config missing "event_intensity_veto_threshold"
      When the news-context config is loaded
      Then loading the config fails naming "event_intensity_veto_threshold"
