Feature: Instrument value object
  A frozen, asset-agnostic Instrument carries a per-asset-class details spec.
  Forex is the only asset class implemented for the TCC, with a closed registry
  of the two target pairs.

  Scenario Outline: a registered forex pair exposes its own unit, precision and details
    When I build the instrument "<symbol>"
    Then its unit is "pip"
    And its unit_size is <unit_size>
    And its digits is <digits>
    And its price_increment is <price_increment>
    And its details base is "<base>" and quote is "<quote>"

    Examples:
      | symbol | unit_size | digits | price_increment | base | quote |
      | EURUSD | 0.0001    | 5      | 0.00001         | EUR  | USD   |
      | AUDUSD | 0.0001    | 5      | 0.00001         | AUD  | USD   |
      | GBPUSD | 0.0001    | 5      | 0.00001         | GBP  | USD   |
      | NZDUSD | 0.0001    | 5      | 0.00001         | NZD  | USD   |
      | USDCAD | 0.0001    | 5      | 0.00001         | USD  | CAD   |
      | USDJPY | 0.01      | 3      | 0.001           | USD  | JPY   |

  Scenario: a forex instrument carries its LEAN identity
    When I build the instrument "EURUSD"
    Then its security_type is "forex"
    And its market is "oanda"
    And its lot_size is 100000

  Scenario: USD/JPY rounds to its own precision, not EUR/USD's
    When I build the instrument "USDJPY"
    Then rounding 110.123456 yields 110.123

  Scenario: an unknown symbol raises instead of defaulting
    When I build the instrument "XAUUSD"
    Then construction fails with an unknown-symbol error
