Feature: Persistent local cache
  A two-tier read-through cache: an in-process memory tier (from the cache
  factory) in front of a durable disk tier. A value computed once is reused
  within a process (memory) and across processes or restarts (disk), so nothing
  is computed twice.

  Scenario: a value is computed once and reused from memory
    Given a local cache in a fresh directory
    When I get key "k" computing document 1
    And I get key "k" computing document 2
    Then both reads are document 1
    And the document was computed 1 time

  Scenario: caching a non-model value is rejected (fail fast)
    Given a local cache in a fresh directory
    When I cache a non-model value at key "bad"
    Then caching fails with a type error

  Scenario: a value persists to disk for a new cache instance
    Given a local cache in a fresh directory
    When I get key "k" computing document 1
    And a second local cache opens the same directory
    And I get key "k" from the second cache computing document 2
    Then the second read is document 1
    And the document was computed 1 time
