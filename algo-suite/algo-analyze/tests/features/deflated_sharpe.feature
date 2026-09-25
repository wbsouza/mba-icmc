Feature: Deflated Sharpe ratio
  A pure function correcting an observed (naive) Sharpe ratio for the number
  of independent trials tested (Bailey & López de Prado 2014), so a headline
  number reported after searching many strategy variants isn't inflated by
  selection bias. These scenarios exercise the pure function directly, not
  through the CLI — `cli.feature` covers `algo-analyze metrics`, which wires
  this function in against a run's headline Sharpe and trade count.

  Formula (for the golden-value scenario's expected numbers): given observed
  Sharpe SR, T trade returns, skew γ3, kurtosis γ4, and n_trials N:
    σ_SR = sqrt((1 - γ3·SR + ((γ4-1)/4)·SR²) / (T-1))
    E[max Z_N] = (1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(N·e))   [γ = Euler-Mascheroni ≈ 0.5772156649015329, N>1; E[max Z_1] = 0]
    deflated_sharpe = SR - σ_SR · E[max Z_N]

  # deflated-sharpe-01
  Scenario: Deflation penalizes many trials (golden value)
    Given an observed Sharpe of 0.5 from 100 trade returns with skew 0.0 and kurtosis 3.0
    And 50 independent trials
    When the deflated Sharpe ratio is computed
    Then it equals 0.2573452749201449 within tolerance 1e-9
    And it is lower than the observed Sharpe of 0.5

  # deflated-sharpe-02
  Scenario: A single trial is an exact no-op
    Given an observed Sharpe of 0.5 from 100 trade returns with skew 0.0 and kurtosis 3.0
    And 1 independent trial
    When the deflated Sharpe ratio is computed
    Then it equals the observed Sharpe of 0.5 exactly

  # deflated-sharpe-03
  Scenario: Zero-variance returns fail fast
    Given trade returns with zero variance
    When the deflated Sharpe ratio is computed
    Then it raises an error naming the zero-variance input
    And no NaN or infinite value is returned

  # deflated-sharpe-04
  Scenario: Closed-form computation is deterministic
    Given an observed Sharpe of 0.5 from 100 trade returns with skew 0.0 and kurtosis 3.0
    And 50 independent trials
    When the deflated Sharpe ratio is computed twice
    Then both deflated Sharpe values are byte-identical

  # deflated-sharpe-05
  Scenario Outline: Invalid closed-form inputs fail fast
    Given deflated Sharpe inputs <sharpe>, <count>, <skew>, <kurtosis>, and <trials>
    When the deflated Sharpe ratio is computed
    Then it raises an error containing "<message>"
    And no NaN or infinite value is returned

    Examples:
      | sharpe | count | skew | kurtosis | trials | message              |
      | none   | 100   | 0.0  | 3.0      | 50     | observed_sharpe      |
      | 0.5    | none  | 0.0  | 3.0      | 50     | n_returns            |
      | 0.5    | 1     | 0.0  | 3.0      | 50     | at least 2           |
      | 0.5    | 100   | 0.0  | 3.0      | 0      | n_trials             |
      | 0.5    | 100   | nan  | 3.0      | 50     | skew                 |
      | nan    | 100   | 0.0  | 3.0      | 50     | observed_sharpe      |
      | 0.5    | 100   | 0.0  | nan      | 50     | kurtosis             |
      | 3.0    | 100   | 10.0 | 1.0      | 50     | non-positive Sharpe  |
      | 1.0    | 100   | 1.0  | 1.0      | 50     | non-positive Sharpe  |

  # deflated-sharpe-06
  Scenario: Raw trade returns infer the observed Sharpe and count
    Given raw trade returns 0.02, -0.01, 0.03, 0.01, -0.02
    And 1 independent trial
    When the deflated Sharpe ratio is computed
    Then it equals 0.28934569330224724 within tolerance 1e-9

  # deflated-sharpe-07
  Scenario Outline: Malformed raw trade returns fail fast
    Given raw trade returns <returns>
    When the deflated Sharpe ratio is computed
    Then it raises an error containing "<message>"
    And no NaN or infinite value is returned

    Examples:
      | returns    | message      |
      | 0.01       | at least two |
      | 0.01, nan  | finite       |

  # deflated-sharpe-08
  Scenario: Omitting the trial count defaults to a single, no-op trial
    Given raw trade returns 0.02, -0.01, 0.03, 0.01, -0.02
    When the deflated Sharpe ratio is computed without specifying n_trials
    Then it equals 0.28934569330224724 within tolerance 1e-9

  # deflated-sharpe-09
  Scenario: Omitting skew and kurtosis defaults to a normal return distribution
    Given an observed Sharpe of 0.5 from 100 trade returns
    And 50 independent trials
    When the deflated Sharpe ratio is computed without specifying skew or kurtosis
    Then it equals 0.2573452749201449 within tolerance 1e-9

  # deflated-sharpe-10
  Scenario Outline: Boundary and non-zero-skew inputs still compute the documented formula
    Given an observed Sharpe of <sharpe> from <count> trade returns with skew <skew> and kurtosis <kurtosis>
    And <trials> independent trials
    When the deflated Sharpe ratio is computed
    Then it equals <expected> within tolerance 1e-9

    Examples:
      | sharpe | count | skew | kurtosis | trials | expected            |
      | 0.5    | 2     | 0.0  | 3.0      | 50     | -1.9143840300901647 |
      | 0.3    | 100   | 0.0  | 1.0      | 50     | 0.07122293121210274 |
      | 0.5    | 100   | 0.2  | 3.0      | 50     | 0.2683808710765412  |
