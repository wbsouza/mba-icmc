Feature: Monte-Carlo permutation significance test
  A pure function compares two strategies' trade-return samples with Aronson's
  Monte-Carlo Permutation Test. It is deterministic when seeded, fails fast
  rather than under-sampling, and remains library-level only until the later
  integration lane wires the CLI.

  # significance-mcp-01
  Scenario: Fixed seed produces a reproducible p-value
    Given baseline returns 0.010, 0.012, 0.011, 0.013, 0.010, 0.014
    And comparison returns 0.030, 0.033, 0.031, 0.034, 0.032, 0.035
    And 499 permutations with seed 12345
    When the permutation test is computed twice
    Then both p-values are byte-identical
    And both reject-null decisions are identical

  # significance-mcp-02
  Scenario: A large return-distribution difference rejects the null
    Given baseline returns -0.040, -0.035, -0.030, -0.025, -0.020, -0.015
    And comparison returns 0.045, 0.050, 0.055, 0.060, 0.065, 0.070
    And 499 permutations with seed 7
    When the permutation test is computed
    Then the p-value is below 0.05
    And the null hypothesis is rejected

  # significance-mcp-03
  Scenario: Identical distributions do not reject the null
    Given baseline returns 0.010, -0.005, 0.015, 0.000, 0.020, -0.010
    And comparison returns 0.010, -0.005, 0.015, 0.000, 0.020, -0.010
    And 499 permutations with seed 99
    When the permutation test is computed
    Then the p-value equals 1.0 exactly
    And the null hypothesis is not rejected

  # significance-mcp-04
  Scenario: Too few permutations fail fast with a clear minimum
    Given baseline returns 0.010, 0.012, 0.011
    And comparison returns 0.030, 0.033, 0.031
    And 99 permutations with seed 1
    When the permutation test is computed
    Then it raises an error containing "n_permutations"
    And it raises an error containing "at least 100"

  # significance-mcp-05
  Scenario: The minimum permutation count is accepted
    Given baseline returns 0.010, 0.012, 0.011
    And comparison returns 0.030, 0.033, 0.031
    And 100 permutations with seed 1
    When the permutation test is computed
    Then no permutation error is raised

  # significance-mcp-06
  Scenario: Non-finite returns fail fast
    Given baseline returns 0.010, NaN, 0.011
    And comparison returns 0.030, 0.033, 0.031
    And 100 permutations with seed 1
    When the permutation test is computed
    Then it raises an error containing "finite returns"

  # significance-mcp-07
  Scenario: Undersized samples fail fast
    Given baseline returns 0.010
    And comparison returns 0.030, 0.033
    And 100 permutations with seed 1
    When the permutation test is computed
    Then it raises an error containing "at least two returns"

  # significance-mcp-08
  Scenario: Boolean permutation settings fail fast
    Given baseline returns 0.010, 0.012
    And comparison returns 0.030, 0.033
    And boolean permutation settings
    When the permutation test is computed
    Then it raises an error containing "n_permutations"
