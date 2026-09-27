Feature: Paired portfolio inference
  Scenario: Actual portfolio returns replace unrelated trade counts and headline Sharpe
    Given complete paired engine portfolios
    When portfolio metrics are reported with registered search history
    Then probability and moments use daily engine equity with source hashes

  Scenario: Calendar-aligned portfolios can have unequal trade counts
    Given complete paired engine portfolios
    When paired portfolio significance is reported
    Then the bootstrap records effect interval settings and sensitivity

  Scenario: Seeded stationary blocks preserve paired time order
    Given complete paired engine portfolios
    When stationary resampling indices are drawn twice
    Then indices are reproducible with ordered circular continuations and pairing

  Scenario Outline: Missing or incompatible portfolio information is never filled
    Given complete paired engine portfolios
    And the challenger portfolio has <problem>
    When paired portfolio significance is reported
    Then portfolio inference diagnoses "<reason>"
    Examples:
      | problem | reason |
      | missing day | missing exact UTC |
      | duplicate | ordered and unique |
      | NaN equity | finite and positive |
      | wrong symbol | full inclusive run dates |
      | missing contract | inference-inputs.json |

  Scenario Outline: Insufficient or degenerate uncertainty is unavailable
    Given complete paired engine portfolios
    When block inference receives <problem>
    Then portfolio inference diagnoses "<reason>"
    Examples:
      | problem | reason |
      | zero differences | degenerate |
      | constant differences | degenerate |
      | short history | 30 observations |
      | insufficient blocks | 10 expected blocks |

  Scenario: Legacy inventory preserves original files
    Given complete paired engine portfolios
    When migration inventory is generated
    Then legacy files remain unchanged and missing search history is identified
