Feature: Offline RSI preserves LEAN's decimal loss guard
  LEAN RelativeStrengthIndex.ComputeNextValue returns 100 when
  Math.Round(averageLoss, 10) is zero, using decimal midpoint-to-even rounding.
  Otherwise the divisor remains the original unrounded average loss.

  Scenario Outline: Wilder RSI crosses the native guard on the sine probe fixture
    Given the first <count> midpoint closes from the native sine-35 minute fixture
    When offline RSI is calculated with period 3
    Then its last RSI matches native <expected> within 1e-9 absolute and zero relative tolerance
    Examples:
      | count | expected          |
      | 192   | 99.99982204875077 |
      | 193   | 99.9998853502878  |
      | 194   | 100              |
      | 195   | 100              |

  Scenario Outline: Only the zero check rounds average loss
    Given Wilder average gain <gain> and average loss <loss>
    When offline RSI evaluates those averages
    Then it matches the decimal midpoint-to-even loss guard
    Examples:
      | gain          | loss                 |
      | 0             | 0                    |
      | 0.00006       | 0                    |
      | 0.00006       | 0.000000000049999999 |
      | 0.00006       | 0.00000000005       |
      | 0.00006       | nextafter(5e-11)    |
      | 0.00006       | 0.000000000050000001 |
      | 0.00006       | 0.00000000006       |
      | 0.00006       | 0.00000000015       |
      | 0             | 0.0000000001        |
      | 0.00000000004 | 0.00006             |
