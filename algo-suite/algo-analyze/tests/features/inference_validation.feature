Feature: Inference rejects malformed evidence instead of fabricating certainty
  Scenario Outline: Artifact schema and coverage are validated on a declared channel
    Invalid evidence is an error (CLI exit 2); valid evidence that cannot support
    inference is an explicit unavailable report. The channel is part of the contract.

    Given valid inference evidence
    And artifact <artifact> has <change>
    When the evidence is analyzed
    Then the evidence is "<outcome>" mentioning "<diagnostic>"
    Examples:
      | artifact | change | outcome | diagnostic |
      | main.json | invalid JSON | error | invalid JSON |
      | main.json | nonobject | error | JSON object |
      | main.json | absent | unavailable | missing main.json |
      | main.json | missing charts | unavailable | lacks Strategy Equity |
      | main.json | nonlist values | error | must be a list |
      | main.json | malformed point | error | equity points require |
      | main.json | boolean timestamp | error | integer Unix seconds |
      | main.json | text equity | error | must be numeric |
      | main.json | zero equity | error | finite and positive |
      | main.json | overflow return | error | derived portfolio returns |
      | main.json | duplicate | error | ordered and unique |
      | main.json | mismatching Return series | error | engine daily Return series |
      | main.json | text Return percent | error | Return points require |
      | main.json | malformed Return point | error | Return points require |
      | main.json | null Return series | error | Return series must be an object |
      | main.json | null Return values | error | Return values must be a list |
      | main.json | empty Return object | error | Return values must be a list |
      | main.json | duplicate Return timestamps | error | Return timestamps must be unique |
      | run.json | unsuccessful | error | successful run manifest |
      | run.json | missing symbol | error | string start, end, symbol |
      | run.json | reversed dates | error | end must be after start |
      | inference-inputs.json | wrong timezone | error | calendar-day UTC |
      | inference-inputs.json | empty costs | error | nonempty costs |
      | selection.json | missing n_trials | error | selection manifest requires |
      | selection.json | wrong frequency | error | nonannualized calendar-day |
      | selection.json | boolean n_trials | error | positive integer |
      | selection.json | excessive n_trials | error | cannot exceed |
      | selection.json | empty provenance | error | provenance must be nonempty |
      | selection.json | scalar JSON | error | JSON object |
      | selection.json | ledger with text sharpe | error | finite daily_sharpe |
      | selection.json | ledger with NaN sharpe | error | finite daily_sharpe |
      | selection.json | single trial ledger | error | at least two trials |
      | selection.json | ledger below declared n_trials | error | cannot exceed |
      | selection.json | ledger with text n_trials | error | positive integer |
      | selection.json | nonlist trials | error | trials must be a list |
      | selection.json | null trials | error | trials must be a list |
      | selection.json | ledger declaring dispersion | error | must not also declare |

  Scenario: Candle rows use the end-stamped close as the daily mark
    LEAN stamps each equity candlestick with its END time and schedules a
    sample at every midnight, so the close of the midnight candle is the mark.

    Given valid inference evidence
    And artifact main.json has candle points
    When the evidence is analyzed
    Then the evidence reproduces the line-series moments

  Scenario: A consistent engine Return series is accepted
    Given valid inference evidence
    And artifact main.json has consistent Return series
    When the evidence is analyzed
    Then the evidence has 120 daily observations and a finite probability

  Scenario: Fewer than four daily returns leave DSR unavailable, not invalid
    Given valid inference evidence
    And the run window covers only three daily returns
    When the evidence is analyzed
    Then the evidence is "unavailable" mentioning "at least four"

  Scenario: Portfolio pairs cannot mix cost assumptions
    Given valid inference evidence
    When paired evidence has different cost assumptions
    Then the evidence diagnostic includes "incompatible portfolio"

  Scenario: Unsupported sensitivity length remains visible
    Given valid inference evidence
    When paired evidence has an unsupported sensitivity length
    Then the primary inference is available and the sensitivity explains insufficient blocks

  Scenario: Invalid reports do not stop the read-only migration inventory
    Given valid inference evidence
    And artifact run.json has absent
    When the evidence inventory is generated
    Then the inventory identifies one invalid run

  Scenario Outline: Resampling requires valid prespecified settings
    Given valid inference evidence
    When block settings are <problem>
    Then the evidence diagnostic includes "<diagnostic>"
    Examples:
      | problem | diagnostic |
      | duplicated | unique block lengths |
      | missing rule | unique block lengths |
      | zero resamples | n_resamples |
      | negative seed | seed |
      | invalid alpha | alpha must lie |
      | unresolved alpha | cannot resolve |
      | unequal lengths | equal lengths |
      | nonfinite returns | finite one-dimensional |
      | difference overflow | differences and their mean must be finite |

  Scenario Outline: Moment calculations diagnose unsupported samples
    Given valid inference evidence
    When return moments receive <problem>
    Then the evidence diagnostic includes "<diagnostic>"
    Examples:
      | problem | diagnostic |
      | short history | at least four |
      | nonfinite history | finite daily returns |
      | constant history | zero return variance |
      | centering overflow | centering overflow |

  Scenario Outline: DSR arithmetic rejects nonrepresentable finite inputs
    Given valid inference evidence
    When DSR receives <problem>
    Then the evidence diagnostic includes "<diagnostic>"
    Examples:
      | problem | diagnostic |
      | huge Sharpe | sampling variance overflow |
      | huge variance | finite and positive |
      | huge skew | Pearson kurtosis |
      | threshold overflow | threshold must be finite |
      | missing provenance | provenance is required |

  Scenario Outline: Missing portfolio data cannot conceal invalid command settings
    Given valid inference evidence
    When significance CLI receives <option> without portfolio data
    Then the CLI rejects the setting with "<diagnostic>"
    Examples:
      | option | diagnostic |
      | --resamples 0 | n_resamples |
      | --seed -1 | seed |
      | --block-length 0 | block_length |

  Scenario: Dependency gates reject forbidden core imports
    When inference dependency contracts are checked against boundary violations
    Then the architecture checker rejects each violation and accepts permitted imports

  Scenario: Uncovered core code fails the quality gate
    When the inference quality gate sees an unexecuted numerical module
    Then the quality checker reports coverage below its fixed threshold
