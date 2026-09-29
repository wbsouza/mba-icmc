Feature: Paired portfolio inference
  Scenario: Actual portfolio returns replace unrelated trade counts and headline Sharpe
    Given complete paired engine portfolios
    When portfolio metrics are reported with registered search history
    Then probability and moments use daily engine equity with source hashes
    And the ledger supplies the independently computed dispersion and threshold

  Scenario: Producer-emitted contracts are verified against the run manifest
    Given a run written by the backtest artifact producer with engine equity
    When portfolio metrics are reported with registered search history
    Then the contract is producer-verified and its digest equals the manifest record

  Scenario: A producer contract edited after production is rejected
    Given a run written by the backtest artifact producer with engine equity
    And the contract costs are edited after production
    When portfolio metrics are reported with registered search history
    Then portfolio inference is "error" diagnosing "does not match the run manifest digest"

  Scenario: A contract whose cost model disagrees with the manifest adapter is rejected
    Given a run written by the backtest artifact producer with engine equity
    And the manifest records a different brokerage adapter
    When portfolio metrics are reported with registered search history
    Then portfolio inference is "error" diagnosing "brokerage adapter"

  Scenario Outline: A manifest with only one producer field is still verified
    Either recorded field alone binds the contract; only a manifest with neither is declared.

    Given a run written by the backtest artifact producer with engine equity
    And the manifest keeps only its <kept> field
    And <tamper>
    When portfolio metrics are reported with registered search history
    Then portfolio inference is "error" diagnosing "<reason>"
    Examples:
      | kept | tamper | reason |
      | inference_inputs_sha256 | the contract costs are edited after production | does not match the run manifest digest |
      | broker_adapter | the contract names a different brokerage adapter | brokerage adapter |

  Scenario: Nested run identifiers are preserved in the paired report
    Given complete paired engine portfolios under "experiments/first/baseline" and "experiments/second/baseline"
    When paired portfolio significance is reported for the nested runs
    Then the report names "experiments/first/baseline" and "experiments/second/baseline"

  Scenario: Calendar-aligned portfolios can have unequal trade counts
    Given complete paired engine portfolios
    When paired portfolio significance is reported
    Then the bootstrap records effect interval settings and sensitivity

  Scenario: Seeded stationary blocks preserve paired time order
    Given complete paired engine portfolios
    When stationary resampling indices are drawn twice
    Then indices are reproducible with ordered circular continuations and pairing

  Scenario Outline: Missing or incompatible portfolio information is never filled
    Missing evidence is an unavailable report; malformed evidence is an error.

    Given complete paired engine portfolios
    And the challenger portfolio has <problem>
    When paired portfolio significance is reported
    Then portfolio inference is "<outcome>" diagnosing "<reason>"
    Examples:
      | problem | outcome | reason |
      | missing day | unavailable | missing exact UTC |
      | duplicate | error | ordered and unique |
      | NaN equity | error | finite and positive |
      | wrong symbol | error | full inclusive run dates |
      | missing contract | unavailable | inference-inputs.json |

  Scenario Outline: Insufficient or degenerate uncertainty is unavailable
    Given complete paired engine portfolios
    When block inference receives <problem>
    Then portfolio inference is "unavailable" diagnosing "<reason>"
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
