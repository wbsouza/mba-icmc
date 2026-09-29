Feature: Frozen-model ablation evidence preserves engine provenance and warm-up
  The QA evidence must come from completed engine artifacts and retain the
  candidate's longer warm-up rather than silently accepting premature decisions.

  Scenario: A completed run without its engine config cannot become evidence
    Given a completed baseline run with a recorded model hash
    When the ablation QA inspects the run
    Then the run is rejected for missing its engine-written config

  Scenario: The engine-written config is copied and hashed unchanged
    Given a completed baseline run with a recorded model hash
    And the run includes its resolved engine config
    When the ablation QA inspects the run
    Then evidence records and copies the original engine config

  Scenario: Paired decisions preserve the candidate's delayed start
    Given paired decision artifacts with a later and shorter candidate history
    When the ablation QA compares their decisions
    Then evidence records the observed warm-up asymmetry

  Scenario: Premature candidate decisions fail the warm-up gate
    Given paired decision artifacts with a later and shorter candidate history
    And a candidate decision is introduced at the first baseline timestamp
    When the ablation QA compares their decisions
    Then the comparison rejects the premature candidate start

  Scenario: Extra candidate observations cannot hide the warm-up row asymmetry
    Given paired decision artifacts with a later and shorter candidate history
    And extra late candidate decisions erase the row-count difference
    When the ablation QA compares their decisions
    Then the comparison rejects the missing warm-up row asymmetry
