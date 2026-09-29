@integration
Feature: Calendar risk anchors observe every received quote minute
  Incomplete decision candles must not defer the daily or weekly equity anchor.
  The production on_data method runs inside native LEAN with unrelated work stubbed.

  Scenario Outline: Overnight losses survive incomplete candles at calendar boundaries
    Given the native production quote handler and real PnL windows
    When quote minutes cross <boundary> with midnight equity 10000 and 04:00 equity 9400
    Then every received quote updates PnL before checking candle completion
    And incomplete candles still manage the open position without evaluating the chain
    And the 04:00 daily PnL is -0.06 and weekly PnL is <weekly>
    And reading PnL again at 04:00 preserves both fractions

    Examples:
      | boundary         | weekly               |
      | an ordinary day  | -0.21666666666666667 |
      | an ISO week      | -0.06               |
      | an ISO week year | -0.06               |

  Scenario: A slice without the subscribed quote cannot reset risk anchors
    Given the native production quote handler and real PnL windows
    When a slice has no quote for the subscribed symbol
    Then no PnL update or candle or position work occurs
