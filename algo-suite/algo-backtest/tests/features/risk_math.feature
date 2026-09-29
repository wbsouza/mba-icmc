Feature: Fixed-fractional lot-size calculation
  Ports the EJB version's lot-size formula (specs.md §14.5, the legacy money-management façade):
  `lotSize = (accountBalance * risk) / (pipValue * stopLossPips)`. `risk` is a caller-supplied
  fraction (specs.md §14.7 quotes 3% as the reference strategy's tuned value, not a hardcoded constant) —
  the function itself carries no default and no magic numbers.

  Rule: The lot size is the fixed-fractional formula, computed exactly

    Scenario: a 3% risk on a 10000 balance with a 20-pip stop sizes to 15 lots
      Given an account balance of 10000.0
      And a risk fraction of 0.03
      And a pip value of 1.0
      And a stop-loss distance of 20.0 pips
      When I compute the lot size
      Then the computed lot size is 15.0

    Scenario Outline: the formula holds across balances, risk fractions, pip values and stops
      Given an account balance of <balance>
      And a risk fraction of <risk>
      And a pip value of <pip_value>
      And a stop-loss distance of <stop_loss_pips> pips
      When I compute the lot size
      Then the computed lot size is <expected>

      Examples:
        | balance | risk | pip_value | stop_loss_pips | expected |
        | 5000.0  | 0.01 | 10.0      | 25.0           | 0.2      |
        | 20000.0 | 0.02 | 1.0       | 40.0           | 10.0     |
        | 1000.0  | 0.03 | 0.5       | 15.0           | 4.0      |

  Rule: Non-positive pip value or stop-loss distance fails fast

    Scenario Outline: a non-positive pip value or stop distance is rejected
      Given an account balance of 10000.0
      And a risk fraction of 0.03
      And a pip value of <pip_value>
      And a stop-loss distance of <stop_loss_pips> pips
      When I compute the lot size
      Then computing the lot size fails with a non-positive-input error

      Examples:
        | pip_value | stop_loss_pips |
        | 0.0       | 20.0           |
        | -1.0      | 20.0           |
        | 1.0       | 0.0            |
        | 1.0       | -5.0           |

  Rule: A non-positive account balance or risk fraction fails fast

    Scenario Outline: a non-positive balance or risk is rejected
      Given an account balance of <balance>
      And a risk fraction of <risk>
      And a pip value of 1.0
      And a stop-loss distance of 20.0 pips
      When I compute the lot size
      Then computing the lot size fails with a non-positive-input error

      Examples:
        | balance  | risk  |
        | 0.0      | 0.03  |
        | -10000.0 | 0.03  |
        | 10000.0  | 0.0   |
        | 10000.0  | -0.03 |
