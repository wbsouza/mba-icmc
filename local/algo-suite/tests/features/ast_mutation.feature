# Scenario: ast_mutation-01 flips each supported operator kind exactly once
# Scenario: ast_mutation-02 counts every mutation kind present in one file
# Scenario: ast_mutation-03 no matching nodes yields no mutants
# Scenario: ast_mutation-04 targets only the Nth matching node when index > 0
# Scenario: ast_mutation-05 propagates a syntax error instead of swallowing it
# Scenario: ast_mutation-06 mutate_file writes the mutant and returns the original source
Feature: AST-level mutant generation and application

  Background:
    Given an isolated fake workspace root

  Scenario Outline: flips each supported operator kind exactly once
    Given a source file containing "<source>"
    When mutants are generated for that file
    Then exactly 1 mutant is generated
    And applying mutant 0 produces source containing "<mutated>"

    Examples:
      | source      | mutated  |
      | x = a < b   | a >= b   |
      | x = a <= b  | a > b    |
      | x = a > b   | a <= b   |
      | x = a >= b  | a < b    |
      | x = a == b  | a != b   |
      | x = a != b  | a == b   |
      | x = a and b | a or b   |
      | x = a or b  | a and b  |
      | x = not a   | x = a    |
      | x = a + b   | a - b    |
      | x = a - b   | a + b    |
      | x = a * b   | a / b    |
      | x = a / b   | a * b    |

  Scenario: counts every mutation kind present in one file
    Given a source file containing:
      """
      def f(a, b):
          if a < b and not a:
              return a + b
          return a - b
      """
    When mutants are generated for that file
    Then the generated mutant kinds are:
      | kind    | count |
      | compare | 1     |
      | boolop  | 1     |
      | not     | 1     |
      | arith   | 2     |

  Scenario: no matching nodes yields no mutants
    Given a source file containing:
      """
      x = 1
      y = 2
      """
    When mutants are generated for that file
    Then exactly 0 mutants are generated

  Scenario: targets only the Nth matching node when index > 0
    Given a source file containing:
      """
      x = a < b
      y = c < d
      """
    When mutants are generated for that file
    Then exactly 2 mutants are generated
    When mutant 1 is applied to a fresh parse of that file
    Then the result contains "a < b"
    And the result contains "c >= d"

  Scenario: propagates a syntax error instead of swallowing it
    Given a source file containing "def f(:"
    When mutants are generated for that file
    Then a SyntaxError is raised

  Scenario: mutate_file writes the mutant and returns the original source
    Given a source file containing "x = a < b"
    When mutants are generated for that file
    And mutant 0 is applied via mutate_file
    Then mutate_file returns the original source unchanged
    And the file on disk now contains "a >= b"
