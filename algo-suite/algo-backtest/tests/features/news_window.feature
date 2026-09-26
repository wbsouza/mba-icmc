Feature: F4 news-context coverage over a backtest's decision window
  A minute bar is decided at its end, so a run over the inclusive [start, end] days
  evaluates F4 at decision minutes start 00:01 through (end + 1) 00:00 UTC — one
  minute past the last requested day, possibly in the next month's partition.
  load_news_context_window merges every partition that window touches, and
  news_coverage_problems lets the run CLI reject a news-driven run on the host,
  before any LEAN container starts, when F4 would fail on any of those minutes.

  Rule: Every partition the decision window touches is merged into one index

    Scenario: A window spanning a month boundary covers both sides of it
      Given GDELT event features for 2020-01 at intensity 1.5 and for 2020-02 at intensity -2.5
      When the news-context window 2020-01-31 to 2020-02-01 is loaded for "EURUSD"
      Then the index has event_intensity 1.5 at "2020-01-31T23:59:00+00:00"
      And the index has event_intensity -2.5 at "2020-02-01T00:00:00+00:00"

    Scenario: A window ending on a month's last day includes the next month's first decision minute
      Given GDELT event features for 2020-01 at intensity 1.5 and for 2020-02 at intensity -2.5
      When the news-context window 2020-01-30 to 2020-01-31 is loaded for "EURUSD"
      Then the index has event_intensity -2.5 at "2020-02-01T00:00:00+00:00"

  Rule: Coverage is checked against the decision window, not the requested days alone

    Scenario: A run ending on a month's last day needs the next month's partition
      Given GDELT event features for 2020-01 at intensity 1.5 only
      When news coverage is checked for 2020-01-30 to 2020-01-31
      Then the coverage problems name the missing 2020-02 partition
      And the build command is "algo-score events --kind gdelt --from 2020-01-30 --to 2020-02-01"

    Scenario: Features built only through the run's last day miss the final decision minute
      Given GDELT event features for 2020-01 built only from 2020-01-01 through 2020-01-15
      When news coverage is checked for 2020-01-10 to 2020-01-15
      Then the coverage problems name decision minute "2020-01-16T00:00:00+00:00"

    Scenario: Features covering the whole decision window have no problems
      Given GDELT event features for 2020-01 at intensity 1.5 only
      When news coverage is checked for 2020-01-10 to 2020-01-15
      Then there are no coverage problems

    Scenario: Loading a window with an unbuilt month fails naming the build command
      Given GDELT event features for 2020-01 at intensity 1.5 only
      When loading the news-context window 2020-01-31 to 2020-02-01 fails
      Then the window failure names "algo-score events --kind gdelt"

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
