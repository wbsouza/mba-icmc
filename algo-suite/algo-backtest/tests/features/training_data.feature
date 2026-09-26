Feature: F7 training data assembled over a multi-month window, on the live feature contract
  `algo_backtest.training` backs scripts/train_{baseline,hybrid}_meta_learner.py. It
  loads every month a `--from`..`--test-end` window touches (so a model can be fit
  on e.g. 6 months and tested on the next 6), builds rows through the same
  `chain.wiring.price_features` the live algorithm uses, keys news lookups on each
  bar's decision time (bar start + 1 minute, LEAN's `self.time` in on_data), and
  persists a model document whose embedded provenance makes it traceable.

  Rule: A window loads every month it touches, and only its own days

    Scenario: A window crossing a month boundary loads bars from both months
      Given EUR/USD m1 bars from "2015-02-27T00:00:00+00:00" to "2015-03-02T23:59:00+00:00"
      When bars are loaded for the window 2015-02-28 to 2015-03-01
      Then the first loaded bar is at "2015-02-28T00:00:00+00:00"
      And the last loaded bar is at "2015-03-01T23:59:00+00:00"

    Scenario: A month missing from the middle of the window fails fast
      Given EUR/USD m1 bars from "2015-02-27T00:00:00+00:00" to "2015-02-28T23:59:00+00:00"
      When loading bars for the window 2015-02-28 to 2015-03-01 fails
      Then the training failure names "month=03"

  Rule: Training rows share the live feature contract

    Scenario: Price-only rows carry exactly the live price-feature keys
      Given EUR/USD m1 bars from "2015-02-27T00:00:00+00:00" to "2015-02-27T01:59:00+00:00"
      When price-only training rows are built for the window 2015-02-27 to 2015-02-27
      Then every row's features have exactly the live price-feature keys
      And there are 105 rows

    Scenario: News features are looked up at each bar's decision time, not its start
      Given EUR/USD m1 bars from "2015-02-27T23:00:00+00:00" to "2015-02-28T00:30:00+00:00"
      And event intensity 1.0 through "2015-02-27T23:59:00+00:00" and -3.0 from "2015-02-28T00:00:00+00:00"
      When news training rows are built
      Then the row for the bar starting "2015-02-27T23:58:00+00:00" has news_event_intensity 1.0
      And the row for the bar starting "2015-02-27T23:59:00+00:00" has news_event_intensity -3.0
      And every row's news_sentiment_score is missing

    Scenario: A decision time without an event-intensity value fails fast
      Given EUR/USD m1 bars from "2015-02-27T23:00:00+00:00" to "2015-02-28T00:30:00+00:00"
      And event intensity 1.0 through "2015-02-27T23:30:00+00:00" only
      When building news training rows fails
      Then the training failure names "no GDELT event_intensity at decision time"

  Rule: A saved model carries the provenance that makes it traceable

    Scenario: The saved model document embeds data-root-relative input hashes and provenance
      Given EUR/USD m1 bars from "2015-02-27T00:00:00+00:00" to "2015-02-27T00:30:00+00:00"
      When a model is saved with provenance strategy "hybrid"
      Then the saved model reloads
      And the provenance lists the 2015-02 price partition relative to the data root with its hash
      And the provenance's strategy is "hybrid"
