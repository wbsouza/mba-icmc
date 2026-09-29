Feature: Logging configuration
  Shared structlog setup: a level name resolves to its standard numeric level,
  and configured logging yields usable loggers.

  Scenario Outline: a level name resolves to its standard numeric level
    When I resolve the log level "<name>"
    Then the numeric level is <value>

    Examples:
      | name    | value |
      | DEBUG   | 10    |
      | INFO    | 20    |
      | WARNING | 30    |
      | error   | 40    |

  Scenario: an unknown level name is rejected
    When I resolve the log level "VERBOSE"
    Then resolving the level fails

  Scenario: a configured logger can emit without error
    Given logging is configured at level "INFO"
    When I get a logger named "algo.test"
    Then the logger exposes info and bind
