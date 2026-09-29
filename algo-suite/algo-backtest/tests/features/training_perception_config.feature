Feature: Training uses the strategy perception config without replacing the frozen model
  Scenario: Baseline training retains its existing default output
    When baseline training arguments are parsed without a strategy override
    Then training selects baseline and its bundled model output

  Scenario: DSHA retraining requires an explicit separate output
    When baseline-dsha training arguments omit the output path
    Then training fails with an explicit output-path instruction

  Scenario: DSHA retraining accepts an explicit output
    When baseline-dsha training arguments specify a separate model output
    Then training selects baseline-dsha and the requested output
