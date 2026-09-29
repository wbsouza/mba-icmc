Feature: CLI boundary handler (run_with_logging)
  The application boundary runs a callable, turning an unhandled error into a
  process exit code 1, passing an explicit SystemExit through unchanged, and
  returning normally for a clean run.

  Scenario: an unhandled error becomes exit code 1
    When I run a callable that raises RuntimeError
    Then it exits with code 1

  Scenario: a SystemExit passes through unchanged
    When I run a callable that raises SystemExit 2
    Then it exits with code 2

  Scenario: a clean run returns normally
    When I run a callable that records a call
    Then the recorded calls are exactly one
