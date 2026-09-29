Feature: Published classical DSR probability
  Scenario: Frozen independent nonzero threshold reference
    Given DSR inputs SR 0.2 trials 10 dispersion 0.1
    When classical DSR is computed
    Then DSR matches the independent probability 0.6624281468307813

  Scenario: Registered single trial at zero is PSR one half
    Given DSR inputs SR 0 trials 1 dispersion 0.1
    When classical DSR is computed
    Then DSR matches the independent probability 0.5

  Scenario: More searched trials reduce probability
    Given DSR inputs SR 0.2 trials 10 dispersion 0.1
    When classical DSR is computed
    Then one hundred trials has lower probability

  Scenario: Missing dispersion is unavailable
    Given DSR inputs SR 0.2 trials 10 dispersion 0.1
    And DSR has missing dispersion
    When classical DSR is computed
    Then DSR fails mentioning "dispersion"

  Scenario Outline: Invalid input is diagnosed
    Given DSR inputs SR 0.2 trials 10 dispersion 0.1
    And invalid DSR <field> value <value>
    When classical DSR is computed
    Then DSR fails mentioning "<reason>"
    Examples:
      | field | value | reason |
      | n_returns | 1 | at least four |
      | n_trials | 0 | positive integer |
      | kurtosis | 0 | Pearson |
      | skew | NaN | finite |
      | trial_sharpe_std | -1 | nonnegative |
