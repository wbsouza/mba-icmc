# Spec 04a — order-execution engine (Track A of Spec 04, Wave 1). Exercises the real,
# pinned LEAN container (quantconnect/lean:17748), not a mock — the point is proving
# integration with the actual open-source execution engine, per algo-backtest/SPEC.md §3.
@integration
Feature: Order execution through the LEAN engine
  Background:
    Given materialized EUR/USD minute data covering one trading day

  # order_execution-01
  Scenario Outline: A directional decision places a real market order and the fill is recorded
    Given a strategy that emits one <decision> decision at a known bar
    When the backtest runs through the order-execution engine
    Then the backtest exits successfully
    And the run reports exactly one closed trade
    And the recorded fill shows direction "<direction>"

    Examples:
      | decision | direction |
      | BUY      | LONG      |
      | SELL     | SHORT     |

  # order_execution-02
  Scenario: HOLD manages an open position without opening a new order
    Given an open position from a prior BUY
    And a strategy that emits HOLD at the current bar
    When the backtest runs through the order-execution engine
    Then no new order is placed
    And the open position remains open at the end of the run

  # order_execution-03
  Scenario: NO_TRADE places no order and creates no trade record
    Given no open position
    And a strategy that emits NO_TRADE at the current bar
    When the backtest runs through the order-execution engine
    Then the backtest exits successfully
    And the run reports zero closed trades

  # order_execution-04
  Scenario: An order rejection is recorded, not silently dropped
    Given a strategy that emits a BUY decision LEAN will reject for insufficient margin
    When the backtest runs through the order-execution engine
    Then the backtest exits successfully
    And the rejection is recorded in the run's audit trail

  # order_execution-05
  Scenario Outline: Stop-loss and take-profit levels are attached at order placement
    Given a strategy that emits <decision> with a computed stop distance
    When the backtest runs through the order-execution engine
    Then the resulting order carries a stop-loss at the computed level
    And the recorded fill's risk parameters match the computed stop distance

    Examples:
      | decision |
      | BUY      |
      | SELL     |

  # order_execution-06
  Scenario: The configured brokerage adapter is applied before the first bar
    Given the strategy config selects the "oanda" brokerage adapter
    When the backtest runs through the order-execution engine
    Then the run confirms the oanda brokerage model was applied
    And the resulting fill is recorded normally under that model

  # order_execution-07
  Scenario: A missing or unknown brokerage adapter is a hard stop
    Given the strategy config names an unknown brokerage adapter
    When the backtest starts
    Then it refuses to start before the first bar
    And the error names the invalid adapter
