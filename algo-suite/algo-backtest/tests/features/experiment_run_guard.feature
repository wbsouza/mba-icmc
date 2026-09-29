Feature: experiment run guards against a missing spec file
  `algo-backtest experiment run` fails fast with a clear message when the given
  --spec path does not exist, rather than raising deep inside the YAML loader.
  The guard runs before any container, so this needs no Docker.

  Scenario: a missing spec file is rejected before loading
    Given a --spec path that does not exist
    When I run the experiment-run command
    Then it exits with code 2
    And the error names the missing spec path
