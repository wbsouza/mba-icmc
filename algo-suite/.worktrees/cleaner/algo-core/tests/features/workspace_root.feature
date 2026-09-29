Feature: Fail-fast workspace-root guard (TD-7)
  Resolving the workspace root from a path with no algo-suite ancestor must
  fail loudly with a clear message, never silently guess a root.

  Scenario: resolving from a path with no algo-suite ancestor fails loudly
    Given a start path with no algo-suite ancestor
    When I resolve the workspace root from it
    Then it fails with a "workspace root" RuntimeError
