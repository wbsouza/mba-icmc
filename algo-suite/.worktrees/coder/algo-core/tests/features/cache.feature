Feature: Read-through cache
  Expensive derived values go through a read-through cache: a key is computed
  once on a miss, stored, and returned from cache on every later access. This is
  the keystone of "compute each bar exactly once" (docs/parquet-evaluation.md).

  Scenario: a repeated key is computed once and reused
    Given an empty in-process cache
    When I get key "feat:EURUSD:v1" computing 42
    And I get key "feat:EURUSD:v1" computing 99
    Then the results in order are 42 and 42
    And key "feat:EURUSD:v1" was computed 1 time

  Scenario: distinct keys are computed independently
    Given an empty in-process cache
    When I get key "a" computing 1
    And I get key "b" computing 2
    Then key "a" holds 1
    And key "b" holds 2
    And key "a" was computed 1 time

  Scenario: over capacity, the least-recently-used key is evicted, not the most-recent
    Given an in-process cache with capacity 2
    When I get key "a" computing 1
    And I get key "b" computing 2
    And I get key "a" computing 99
    And I get key "c" computing 3
    And I get key "b" computing 20
    Then key "a" was computed 1 time
    And key "b" was computed 2 times
