Feature: Reproducible perception quality gates
  Scenario: Native coverage uses the host executable line universe
    Given host perception coverage and native traced lines
    When the perception coverage is merged
    Then native statements count as covered without counting nonexecutable trace lines

  Scenario: Missing native adapter coverage fails closed
    Given host perception coverage and native traced lines
    And the native adapter trace is absent
    When the perception coverage is merged
    Then merging fails because native adapter evidence is missing

  Scenario: The offline gate rejects a runtime dependency in pure math
    Given a pure perception module importing QuantConnect
    When the perception architecture gate runs
    Then the dependency gate fails

  Scenario: Mutation subprocess memory caps have a public interface
    Given systemd-run is available
    When the mutation command is memory capped
    Then its child scope has a memory limit and preserves the command
