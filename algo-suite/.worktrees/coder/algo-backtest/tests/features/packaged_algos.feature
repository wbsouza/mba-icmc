Feature: Bundled LEAN algorithms are syntactically valid
  The algorithm files under src/.../algos/ are excluded from ruff and mypy (they
  `import AlgorithmImports`, which only resolves inside the LEAN container), yet they
  ship as production code run by lean-smoke. A syntax check keeps a shipped algorithm
  from silently breaking outside the normal quality gate.

  Scenario: every bundled algorithm parses
    When I parse every bundled algorithm file
    Then they are all syntactically valid
