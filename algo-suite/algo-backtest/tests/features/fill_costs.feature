Feature: Fill costs — pip-spread slippage and per-lot commission
  Story 12 item C. Every fill pays a configured half-spread per side and a per-lot
  commission pro rata on the filled quantity (specs.md §14.5–14.7, strategy A05). The
  numbers come from the strategy's `execution` section (`spread_pips`,
  `commission_per_lot`), never from code constants; zero means "leave LEAN's default
  model in place". The math is a pure, typed module (`engine/costs.py`); the LEAN
  adapters (`engine/fill_models.py`) only call it.

  Rule: Slippage per side is half the configured spread, in price units

    Scenario Outline: half the spread in pips, converted with the pip size
      Given a configured spread of <spread_pips> pips
      And a pip size of <pip_size>
      When I compute the per-side slippage price
      Then the slippage price is <expected>

      Examples:
        | spread_pips | pip_size | expected |
        | 1.0         | 0.0001   | 0.00005  |
        | 0.3         | 0.0001   | 0.000015 |
        | 2.0         | 0.01     | 0.01     |
        | 0.0         | 0.0001   | 0.0      |

    Scenario Outline: a negative spread or a non-positive pip size fails fast
      Given a configured spread of <spread_pips> pips
      And a pip size of <pip_size>
      When I compute the per-side slippage price
      Then the fill-cost computation fails naming "<field>"

      Examples:
        | spread_pips | pip_size | field       |
        | -1.0        | 0.0001   | spread_pips |
        | 1.0         | 0.0      | pip_size    |
        | 1.0         | -0.0001  | pip_size    |

  Rule: Commission is the per-lot rate pro rata on the absolute filled quantity, per side

    Scenario Outline: commission on a partial lot, either direction
      Given a filled quantity of <quantity> units
      And a standard lot of <lot_notional_units> units
      And a commission of <commission_per_lot> per lot
      When I compute the commission amount
      Then the commission amount is <expected>

      Examples:
        | quantity  | lot_notional_units | commission_per_lot | expected |
        | 25000.0   | 100000.0           | 7.0                | 1.75     |
        | -25000.0  | 100000.0           | 7.0                | 1.75     |
        | 100000.0  | 100000.0           | 7.0                | 7.0      |
        | 250000.0  | 100000.0           | 3.5                | 8.75     |
        | 25000.0   | 100000.0           | 0.0                | 0.0      |
        | 0.0       | 100000.0           | 7.0                | 0.0      |

    Scenario Outline: a negative commission or a non-positive lot size fails fast
      Given a filled quantity of 25000.0 units
      And a standard lot of <lot_notional_units> units
      And a commission of <commission_per_lot> per lot
      When I compute the commission amount
      Then the fill-cost computation fails naming "<field>"

      Examples:
        | lot_notional_units | commission_per_lot | field              |
        | 100000.0           | -7.0               | commission_per_lot |
        | 0.0                | 7.0                | lot_notional_units |
        | -100000.0          | 7.0                | lot_notional_units |

  Rule: A pip is ten times the minimum price variation of a fractional-pip FX quote

    Scenario Outline: pip size derived from LEAN's symbol properties
      Given a minimum price variation of <min_price_variation>
      When I derive the pip size
      Then the pip size is <expected>

      Examples:
        | min_price_variation | expected |
        | 0.00001             | 0.0001   |
        | 0.001               | 0.01     |

    Scenario Outline: a non-positive minimum price variation fails fast
      Given a minimum price variation of <min_price_variation>
      When I derive the pip size
      Then the fill-cost computation fails naming "min_price_variation"

      Examples:
        | min_price_variation |
        | 0.0                 |
        | -0.00001            |

  Rule: The LEAN adapters return the pure-math results in LEAN's own types

    Scenario: the slippage model returns the per-side slippage price for any order
      Given a pip-spread slippage model with spread 1.0 pips and pip size 0.0001
      When LEAN asks the model for the slippage approximation of an order of 25000.0 units
      Then the slippage approximation is 0.00005

    Scenario Outline: the fee model returns the pro-rata commission in the given account currency
      Given a per-lot fee model charging <commission_per_lot> per <lot_notional_units>-unit lot in "<currency>"
      When LEAN asks the model for the fee of an order of <quantity> units
      Then the order fee is <expected> "<currency>"

      Examples:
        | commission_per_lot | lot_notional_units | quantity  | currency | expected |
        | 7.0                | 100000.0           | 25000.0   | USD      | 1.75     |
        | 7.0                | 100000.0           | -50000.0  | USD      | 3.5      |
        | 5.0                | 100000.0           | 20000.0   | EUR      | 1.0      |

  Rule: Fill costs are applied to every subscribed security, and zero leaves LEAN's defaults

    Scenario: both costs configured apply both models to every security and log each
      Given an algorithm subscribed to "EURUSD" with minimum price variation 0.00001
      And the algorithm is subscribed to "USDJPY" with minimum price variation 0.001
      When fill costs of 1.0 spread pips and 7.0 commission per lot are applied under tag "T"
      Then every security carries a pip-spread slippage model
      And the "EURUSD" slippage model uses pip size 0.0001
      And the "USDJPY" slippage model uses pip size 0.01
      And every security carries a per-lot fee model
      And every fee model charges in the algorithm's account currency "USD"
      And the log has a "T_FILL_COSTS|model=slippage" line for each security
      And the log has a "T_FILL_COSTS|model=fee" line for each security

    Scenario: the fee model follows the algorithm's account currency, not a fixed one
      Given an algorithm subscribed to "EURUSD" with minimum price variation 0.00001
      And the algorithm's account currency is "EUR"
      When fill costs of 0.0 spread pips and 7.0 commission per lot are applied under tag "T"
      Then every fee model charges in the algorithm's account currency "EUR"

    Scenario: a commission without a lot size fails fast before any model is touched
      Given an algorithm subscribed to "EURUSD" with minimum price variation 0.00001
      When fill costs of 1.0 spread pips and 7.0 commission per lot are applied without a lot size
      Then applying fill costs fails naming "lot_notional_units"
      And no security carries a pip-spread slippage model
      And no security carries a per-lot fee model

    Scenario: a spread alone needs no lot size
      Given an algorithm subscribed to "EURUSD" with minimum price variation 0.00001
      When fill costs of 1.0 spread pips and 0.0 commission per lot are applied without a lot size
      Then every security carries a pip-spread slippage model
      And no security carries a per-lot fee model

    Scenario: an explicit pip size overrides the derived one
      Given an algorithm subscribed to "EURUSD" with minimum price variation 0.00001
      When fill costs of 1.0 spread pips are applied with an explicit pip size of 0.001
      Then the "EURUSD" slippage model uses pip size 0.001

    Scenario: a zero spread leaves the slippage model alone but still applies the commission
      Given an algorithm subscribed to "EURUSD" with minimum price variation 0.00001
      When fill costs of 0.0 spread pips and 7.0 commission per lot are applied under tag "T"
      Then no security carries a pip-spread slippage model
      And every security carries a per-lot fee model
      And the log has no "T_FILL_COSTS|model=slippage" line

    Scenario: a zero commission leaves the fee model alone but still applies the spread
      Given an algorithm subscribed to "EURUSD" with minimum price variation 0.00001
      When fill costs of 1.0 spread pips and 0.0 commission per lot are applied under tag "T"
      Then every security carries a pip-spread slippage model
      And no security carries a per-lot fee model
      And the log has no "T_FILL_COSTS|model=fee" line

    Scenario: both zero applies nothing and logs nothing
      Given an algorithm subscribed to "EURUSD" with minimum price variation 0.00001
      When fill costs of 0.0 spread pips and 0.0 commission per lot are applied under tag "T"
      Then no security carries a pip-spread slippage model
      And no security carries a per-lot fee model
      And the log has no "T_FILL_COSTS" line

    Scenario: applying costs before any subscription fails fast
      Given an algorithm with no subscribed securities
      When fill costs of 1.0 spread pips and 7.0 commission per lot are applied under tag "T"
      Then applying fill costs fails naming "no subscribed securities"

    Scenario Outline: a negative cost is rejected before any model is touched
      Given an algorithm subscribed to "EURUSD" with minimum price variation 0.00001
      When fill costs of <spread_pips> spread pips and <commission_per_lot> commission per lot are applied under tag "T"
      Then applying fill costs fails naming "<field>"
      And no security carries a pip-spread slippage model
      And no security carries a per-lot fee model

      Examples:
        | spread_pips | commission_per_lot | field              |
        | -1.0        | 7.0                | spread_pips        |
        | 1.0         | -7.0               | commission_per_lot |
