Feature: F4 news-context index over a multi-month backtest window
  load_news_context_index reads one (year, month) partition; a backtest window may
  cross month boundaries. load_news_context_window merges every touched month into
  the one index F4 needs for the whole run, and missing_event_partitions lets the
  run CLI reject a news-driven run on the host before any LEAN container starts.

  Rule: Every touched month is merged into one index

    Scenario: A window spanning a month boundary covers both sides of it
      Given GDELT event features for 2020-01 at intensity 1.5 and for 2020-02 at intensity -2.5
      When the news-context window 2020-01-31 to 2020-02-01 is loaded for "EURUSD"
      Then the index has event_intensity 1.5 at "2020-01-31T23:59:00+00:00"
      And the index has event_intensity -2.5 at "2020-02-01T00:00:00+00:00"

  Rule: A missing month fails fast, and is reported before any container starts

    Scenario: Loading a window with an unbuilt month fails naming the build command
      Given GDELT event features for 2020-01 at intensity 1.5 only
      When loading the news-context window 2020-01-31 to 2020-02-01 fails
      Then the window failure names "algo-score events --kind gdelt"

    Scenario: Exactly the unbuilt months are reported as missing
      Given GDELT event features for 2020-01 at intensity 1.5 only
      When the missing event partitions for 2019-12-15 to 2020-02-10 are listed
      Then the missing partitions are "2019-12, 2020-02"

  Rule: A sentiment source is only claimed when every touched month had one

    Scenario: One month without sentiment Parquet makes the whole window's source absent
      Given GDELT event features for 2020-01 at intensity 1.5 and for 2020-02 at intensity -2.5
      And EURUSD sentiment Parquet exists for 2020-01 only
      When the news-context window 2020-01-31 to 2020-02-01 is loaded for "EURUSD"
      Then the window's sentiment source is absent
      And the index has sentiment 0.4 for "EURUSD" at "2020-01-31T12:00:00+00:00"

    Scenario: Sentiment Parquet in every touched month makes the source present
      Given GDELT event features for 2020-01 at intensity 1.5 and for 2020-02 at intensity -2.5
      And EURUSD sentiment Parquet exists for 2020-01 and 2020-02
      When the news-context window 2020-01-31 to 2020-02-01 is loaded for "EURUSD"
      Then the window's sentiment source is present
