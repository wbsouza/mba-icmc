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

  Scenario: A SELL decision places a short market order and returns the fill
    Given a fake algorithm that fills every order
    When OrderExecutor executes a SELL decision with size 2.0
    Then a market order for size -2.0 is placed
    And the fill record status is FILLED with direction SHORT

  Scenario Outline: HOLD and NO_TRADE place no order
    Given a fake algorithm that fills every order
    When OrderExecutor executes a <decision> decision with size 1.0
    Then no market order is placed
    And the fill record status is NONE

    Examples:
      | decision |
      | HOLD     |
      | NO_TRADE |

  Scenario: An order rejection is recorded, not raised
    Given a fake algorithm that rejects every order
    When OrderExecutor executes a BUY decision with size 1.0
    Then the fill record status is REJECTED with a rejection reason

  Scenario: Stop-loss and take-profit levels pass through to the fill record
    Given a fake algorithm that fills every order
    When OrderExecutor executes a BUY decision with a stop distance
    Then the fill record's stop-loss and take-profit match the sizing context

  Scenario: Closing a position liquidates it and returns the fill
    Given a fake algorithm with an open position that fills every order
    When OrderExecutor closes the position
    Then the position is liquidated
    And the fill record status is FILLED

  Scenario: Closing a symbol with no open position is a no-op, not an error
    Given a fake algorithm with no open position
    When OrderExecutor closes the position
    Then the fill record status is NONE

  Scenario: Closing a position that liquidates into multiple tickets fails fast
    Given a fake algorithm whose liquidation returns multiple tickets
    When OrderExecutor closes the position
    Then closing fails with a multi-ticket error
