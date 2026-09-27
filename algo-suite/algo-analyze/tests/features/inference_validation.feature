Feature: Inference rejects malformed evidence instead of fabricating certainty
  Scenario Outline: Artifact schema and coverage are validated explicitly
    Given valid inference evidence
    And artifact <artifact> has <change>
    When the evidence is analyzed
    Then the evidence diagnostic includes "<diagnostic>"
    Examples:
      | artifact | change | diagnostic |
      | main.json | invalid JSON | invalid JSON |
      | main.json | nonobject | JSON object |
      | main.json | absent | missing main.json |
      | main.json | missing charts | lacks Strategy Equity |
      | main.json | nonlist values | must be a list |
      | main.json | malformed point | equity points require |
      | main.json | boolean timestamp | integer Unix seconds |
      | main.json | text equity | must be numeric |
      | main.json | zero equity | finite and positive |
      | main.json | overflow return | derived portfolio returns |
      | run.json | unsuccessful | successful run manifest |
      | run.json | missing symbol | string start, end, symbol |
      | run.json | reversed dates | end must be after start |
      | inference-inputs.json | wrong timezone | calendar-day UTC |
      | inference-inputs.json | empty costs | nonempty costs |
      | selection.json | missing n_trials | selection manifest requires |
      | selection.json | wrong frequency | nonannualized calendar-day |
      | selection.json | boolean n_trials | positive integer |
      | selection.json | excessive n_trials | cannot exceed |
      | selection.json | empty provenance | provenance must be nonempty |

  Scenario: Candle close is used for portfolio mark to market
    Given valid inference evidence
    And artifact main.json has candle points
    When the evidence is analyzed
    Then the evidence has 120 daily observations and a finite probability

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
