Feature: OrderExecutor translates a Decision into a LEAN order and a normalized fill
  Given a Decision plus sizing context, OrderExecutor places the order through
  the algorithm's real order primitives, consumes the OnOrderEvent callback,
  and returns one normalized FillRecord (spec.md Sec 3.2). Unit-level: exercised
  against a fake algorithm double, not the real LEAN container (that is
  order_execution.feature).

  Scenario: A BUY decision places a long market order and returns the fill
    Given a fake algorithm that fills every order
    When OrderExecutor executes a BUY decision with size 1.0
    Then a market order for size 1.0 is placed
    And the fill record status is FILLED with direction LONG
    And every LEAN order primitive was called for the executed symbol
    And the fill record is
      | field            | value                     |
      | decision         | BUY                       |
      | status           | FILLED                    |
      | order_id         | 1                         |
      | fill_price       | 1.2345                    |
      | fill_time        | 2020-01-02T14:30:00+00:00 |
      | direction        | LONG                      |
      | stop_loss        | None                      |
      | take_profit      | None                      |
      | rejection_reason | None                      |

  Scenario: A SELL decision places a short market order and returns the fill
    Given a fake algorithm that fills every order
    When OrderExecutor executes a SELL decision with size 2.0
    Then a market order for size -2.0 is placed
    And the fill record status is FILLED with direction SHORT

  Rule: A caller's own Decision-shaped enum resolves by value, not by class identity
    A real caller (algos/baseline/main.py) crosses this exact class boundary: the
    filter chain's own chain.model.Decision is a separate StrEnum from this module's
    Decision, same four string values. Comparing by `is` instead of `==` silently
    treats every cross-class BUY as not-BUY (2026-09-26 PR #33 review: this fired
    every real BUY as a SELL, undetected until then).

    Scenario: A BUY from a different, value-identical Decision class still executes long
      Given a fake algorithm that fills every order
      When OrderExecutor executes a BUY decision from chain.model's own Decision class
      Then a market order for size 1.0 is placed
      And the fill record status is FILLED with direction LONG

    Scenario: A SELL from a different, value-identical Decision class still executes short
      Given a fake algorithm that fills every order
      When OrderExecutor executes a SELL decision from chain.model's own Decision class
      Then a market order for size -1.0 is placed
      And the fill record status is FILLED with direction SHORT

  Scenario Outline: HOLD and NO_TRADE place no order
    Given a fake algorithm that fills every order
    When OrderExecutor executes a <decision> decision with size 1.0
    Then no market order is placed
    And the fill record status is NONE
    And the fill record is
      | field    | value      |
      | decision | <decision> |
      | order_id | None       |

    Examples:
      | decision |
      | HOLD     |
      | NO_TRADE |

  Scenario: An order rejection is recorded, not raised
    Given a fake algorithm that rejects every order
    When OrderExecutor executes a BUY decision with size 1.0
    Then the fill record status is REJECTED with a rejection reason
    And the fill record is
      | field      | value    |
      | decision   | BUY      |
      | status     | REJECTED |
      | order_id   | 1        |
      | fill_price | None     |
      | direction  | None     |

  Scenario Outline: an order LEAN never reports on is recorded as rejected, not as a fill (<decision>)
    Given a fake algorithm that never reports an order event
    When OrderExecutor executes a <decision> decision with size 1.0
    Then the fill record is rejected with reason "<reason>"
    And the fill record is
      | field    | value      |
      | decision | <decision> |
      | order_id | 1          |

    Examples:
      | decision | reason                                  |
      | BUY      | no OnOrderEvent received for this order |
      | SELL     | no OnOrderEvent received for this order |

  Scenario: Stop-loss and take-profit levels pass through to the fill record
    Given a fake algorithm that fills every order
    When OrderExecutor executes a BUY decision with a stop distance
    Then the fill record's stop-loss and take-profit match the sizing context

  Scenario: Closing a position liquidates it and returns the fill
    Given a fake algorithm with an open position that fills every order
    When OrderExecutor closes the position
    Then the position is liquidated
    And the fill record status is FILLED
    And every LEAN order primitive was called for the executed symbol
    And the fill record is
      | field      | value                     |
      | decision   | HOLD                      |
      | status     | FILLED                    |
      | order_id   | 1                         |
      | fill_price | 1.2345                    |
      | fill_time  | 2020-01-02T14:30:00+00:00 |
      | direction  | None                      |

  Scenario: Closing a position LEAN never reports on is recorded as rejected
    Given a fake algorithm with an open position that never reports an order event
    When OrderExecutor closes the position
    Then the fill record is rejected with reason "no OnOrderEvent received for this order"
    And the fill record is
      | field    | value |
      | decision | HOLD  |
      | order_id | 1     |

  Scenario: Closing a symbol with no open position is a no-op, not an error
    Given a fake algorithm with no open position
    When OrderExecutor closes the position
    Then the fill record status is NONE

  Scenario: Closing a position that liquidates into multiple tickets fails fast
    Given a fake algorithm whose liquidation returns multiple tickets
    When OrderExecutor closes the position
    Then closing fails with a multi-ticket error
    And the executor failure is exactly "liquidate('EURUSD') returned 2 tickets; OrderExecutor.close only normalizes a single-ticket liquidation."

  Rule: The trade plan places its orders in units through the same executor (story 12)
    The chain executor sizes from F6's lot size, not a portfolio fraction, and surrounds
    the entry with a stop-market order and one limit order per target; it moves, resizes
    and cancels them through the executor so no algorithm touches a LEAN ticket directly.

    Scenario Outline: a <decision> of <quantity> units places a market order for exactly that quantity
      Given a fake algorithm that fills every order
      When OrderExecutor executes a <decision> decision for <quantity> units
      Then a market order for size <quantity> is placed
      And the fill record status is FILLED with direction <direction>

      Examples:
        | decision | quantity | direction |
        | BUY      | 150000   | LONG      |
        | SELL     | -25000   | SHORT     |
        | BUY      | 1        | LONG      |
        | SELL     | -1       | SHORT     |

    Scenario: a quantity entry records the ticket and the fill like a sized one
      Given a fake algorithm that fills every order
      When OrderExecutor executes a SELL decision for -25000 units
      Then every LEAN order primitive was called for the executed symbol
      And the fill record is
        | field      | value                     |
        | decision   | SELL                      |
        | status     | FILLED                    |
        | order_id   | 1                         |
        | fill_price | 1.2345                    |
        | fill_time  | 2020-01-02T14:30:00+00:00 |
        | direction  | SHORT                     |

    Scenario: a quantity entry LEAN never reports on is recorded as rejected
      Given a fake algorithm that never reports an order event
      When OrderExecutor executes a BUY decision for 1000 units
      Then the fill record is rejected with reason "no OnOrderEvent received for this order"
      And the fill record is
        | field    | value |
        | decision | BUY   |
        | order_id | 1     |

    Scenario Outline: a quantity whose sign contradicts the decision is refused before any order (<decision> <quantity>)
      Given a fake algorithm that fills every order
      When OrderExecutor executing a <decision> decision for <quantity> units fails
      Then no market order is placed
      And the executor failure is exactly "OrderExecutor.execute_quantity: quantity <shown> contradicts <decision> (BUY needs a positive quantity, SELL a negative one)"

      Examples:
        | decision | quantity | shown   |
        | BUY      | -1000    | -1000.0 |
        | SELL     | 1000     | 1000.0  |
        | BUY      | 0        | 0.0     |

    Scenario: a HOLD placed by quantity is refused
      Given a fake algorithm that fills every order
      When OrderExecutor executing a HOLD decision for 1000 units fails
      Then the executor failure is exactly "OrderExecutor.execute_quantity: <Decision.HOLD: 'HOLD'> places no order; only BUY/SELL"

    Scenario: the plan's stop and targets are submitted as stop-market and limit orders
      Given a fake algorithm that fills every order
      When OrderExecutor places a stop for -150000 units at 1.0984
      And OrderExecutor places a limit for -75000 units at 1.1035
      Then the fake algorithm holds a stop-market order for -150000 at 1.0984
      And the fake algorithm holds a limit order for -75000 at 1.1035
      And the executor reports 2 open orders for the symbol
      And every LEAN order primitive was called for the executed symbol
      And the executor's open orders are
        | order_id | quantity  |
        | 1        | -150000.0 |
        | 2        | -75000.0  |

    Scenario: a trailing move updates the stop ticket's price and a partial exit its quantity
      Given a fake algorithm that fills every order
      And OrderExecutor placed a stop for -150000 units at 1.0984
      When OrderExecutor moves that stop to 1.0990
      And OrderExecutor resizes that stop to -75000
      Then the stop ticket's price is 1.0990 and its quantity -75000

    Scenario: cancelling the plan's working orders cancels each ticket by id
      Given a fake algorithm that fills every order
      And OrderExecutor placed a stop for -150000 units at 1.0984
      And OrderExecutor placed a limit for -75000 units at 1.1035
      When OrderExecutor cancels every open order for the symbol
      Then every fake ticket is cancelled
      And the executor reports 0 open orders for the symbol

    Scenario: updating an order LEAN has no ticket for fails fast
      Given a fake algorithm that fills every order
      When OrderExecutor moving stop 99 to 1.0990 fails
      Then the executor failure is exactly "OrderExecutor: no order ticket for order id 99; the plan's working orders and LEAN's transaction ledger disagree"
