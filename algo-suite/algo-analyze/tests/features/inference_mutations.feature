Feature: Independently constrained statistical equations
  Scenario Outline: DSR matches high precision nonnormal and single trial references
    Given the independent DSR reference <fixture>
    When the registered DSR equation is evaluated
    Then its probability matches the frozen 80 digit value

    Examples:
      | fixture |
      | zero |
      | single |
      | skewed |
      | negative |
      | many |

  Scenario Outline: Estimated moments agree with an exact asymmetric sample
    Given the asymmetric four observation sample scaled by <scale>
    When the portfolio moments are estimated
    Then the sample Sharpe skew and Pearson kurtosis match exact references

    Examples:
      | scale |
      | 1 |
      | 1e-200 |
      | 1e200 |

  Scenario: Finite huge positive returns have representable centered moments
    Given four huge distinct positive returns
    When the portfolio moments are estimated
    Then the large return moments are finite and correct

  Scenario: Stationary bootstrap equals an independent sequential block construction
    Given a registered asymmetric paired time series
    When the seeded stationary bootstrap is computed
    Then its indices and inference match an independent sequential oracle

  Scenario: Pearson moment feasibility tolerates only numerical roundoff
    Given DSR moments on the Pearson feasibility boundary
    When the boundary DSR equation is evaluated
    Then it accepts moment rounding within the documented tolerance

  Scenario: Daily portfolio returns retain flat periods and use previous portfolio equity
    Given a portfolio with exact daily equity of 100 110 110 99 100
    When its portfolio returns are loaded
    Then the four daily returns are 0.1 0 -0.1 and 1/99

  Scenario: Pair alignment rejects timestamps independently of identical metadata
    Given two portfolio series with identical metadata but different timestamps
    When the pair alignment is validated
    Then pair alignment rejects the shifted calendar grid

  Scenario: Finite observations whose sum overflows cannot yield inference
    Given large finite paired differences whose mean overflows
    When the large difference bootstrap is requested
    Then it rejects the nonfinite mean before resampling

  Scenario Outline: Resampling uncertainty remains valid at representational boundaries
    Given a valid bootstrap sample at the <boundary> boundary
    When the boundary bootstrap is computed
    Then the boundary inference remains available and finite

    Examples:
      | boundary |
      | precision |
      | tiny units |
      | alpha resolution |

  Scenario: Interval endpoint overflow is diagnosed even with finite radius and effect
    Given a finite bootstrap sample with an unrepresentable interval endpoint
    When the extreme interval is computed
    Then the interval endpoint overflow is rejected

  Scenario Outline: Selection manifest counts cannot use boolean values
    Given a portfolio with exact daily equity of 100 110 110 99 100
    When its selection history uses boolean <count>
    Then the selection count is rejected as a noninteger

    Examples:
      | count |
      | trial_count |
      | interim_looks |

  Scenario: Arbitrary alpha boundaries preserve p value and interval compatibility
    Given a bootstrap with exactly 6 extreme errors in 199 draws
    When its paired interval is evaluated at alpha 0.035
    Then p equals alpha and its interval contains zero

  Scenario: High alpha inversion still uses the full Monte Carlo probability grid
    Given a bootstrap with 98 extreme errors in 100 draws
    When its paired interval is evaluated at alpha 0.99
    Then its rejected null agrees with an interval excluding zero
