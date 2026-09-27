@integration
Feature: Training features equal the live algorithm's features, numerically
  scripts/train_*_meta_learner.py computes F1/F2 features in plain Python
  (algo_backtest.training) while the live algorithm reads LEAN's own EMA/RSI/MACD
  (engine/chain_algorithm.py). Both go through chain.wiring.price_features, but that
  only shares the formula — this proves the inputs agree too, bar by bar, from the
  first bar the live algorithm decides on.

  LEAN only delivers bars while the exchange is open (e.g. never in the daily
  16:58-17:03 New York break) and fills a missing open minute forward from the
  previous close; training mirrors both (training.lean_bar_stream).

  Scenario Outline: On a sine-wave day <with_gaps> every live decision bar has a training row with the same price features
    Given a one-day EUR/USD minute sine cycle on 2014-05-07 <with_gaps> materialized to lean-data
    When the feature-parity probe replays "20140507" in the LEAN container
    Then the backtest exits successfully
    And the live algorithm's first decision bar is the first training row's bar
    And every live decision bar's price features match its training row to 9 decimal places

    Examples:
      | with_gaps                                   |
      | with every minute present                   |
      | with minutes 06:00-06:04 and 12:30 missing  |

  Scenario: F4's live news lookup equals the training row's news feature for every bar
    Given a one-day EUR/USD minute sine cycle on 2014-05-07 with every minute present materialized to lean-data
    And GDELT event features whose intensity differs every minute from 2014-05-07 through 2014-05-08T00:00
    When the news-parity probe replays "20140507" in the LEAN container
    Then the backtest exits successfully
    And for every live decision bar F4 looked up the training row's news_event_intensity to 9 decimal places

  Scenario Outline: DSHA training matches native decisions with <with_gaps>
    Given a one-day EUR/USD minute sine cycle on 2014-05-07 <with_gaps> materialized to lean-data
    And training and live perception use strategy "baseline-dsha"
    When the feature-parity probe replays "20140507" in the LEAN container
    Then the backtest exits successfully
    And the live algorithm's first decision bar is the first training row's bar
    And every live decision bar's price features match its training row to 9 decimal places

    Examples:
      | with_gaps                                  |
      | with every minute present                  |
      | with minutes 06:00-06:04 and 12:30 missing  |

  Scenario Outline: Configured DSHA smoothing matches native readiness and features
    Given a one-day EUR/USD minute sine cycle on 2014-05-07 with minutes 06:00-06:04 and 12:30 missing materialized to lean-data
    And training and live perception use strategy "baseline-dsha"
    And DSHA smoothing uses periods <first>/<second> and <minutes>-minute buckets
    When the feature-parity probe replays "20140507" in the LEAN container
    Then the backtest exits successfully
    And the live algorithm's first decision bar is the first training row's bar
    And every live decision bar's price features match its training row to 9 decimal places

    Examples:
      | first | second | minutes |
      | 1     | 1      | 7       |
      | 3     | 4      | 90      |

  Scenario: DSHA training preserves native tie-as-down behavior
    Given a one-day EUR/USD minute sine cycle on 2014-05-07 with every minute present materialized to lean-data
    And all materialized quotes have a constant midpoint
    And training and live perception use strategy "baseline-dsha"
    When the feature-parity probe replays "20140507" in the LEAN container
    Then the backtest exits successfully
    And the live algorithm's first decision bar is the first training row's bar
    And every live decision bar's price features match its training row to 9 decimal places
    And every ready DSHA training and live direction is down on ties
