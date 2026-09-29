Feature: Per-currency attribution
  Routes a scored article to the FX currency (or currencies) it concerns —
  ECB→EUR, Fed→USD, BOJ→JPY — so algo-score can derive per-pair sentiment
  (EURUSD/USDJPY) from the per-currency streams. Scorer-agnostic: applies to
  any scorer's output, exercised here against the lexicon (lm) scorer built
  in this task.

  # attribution-01
  Scenario Outline: route an article to the currency it concerns
    Given an article about <subject>
    When attribution runs
    Then it contributes to currency <currency>

    Examples:
      | subject               | currency |
      | the ECB raising rates | EUR      |
      | an FOMC decision      | USD      |
      | BOJ intervention      | JPY      |

  # attribution-02
  Scenario: USD-macro news feeds both pairs
    Given an FOMC article attributed to USD
    When the feature layer forms pair features
    Then both EURUSD and USDJPY consume the USD sentiment stream

  # attribution-03
  Scenario: Article with no attributable currency is dropped
    Given an article concerning none of EUR, USD, JPY
    When attribution runs
    Then it is excluded from per-currency output
    And it is counted in the run report, not raised as an error
