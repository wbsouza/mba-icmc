Feature: Cache backend factory
  The cache backend is selected by name (registry + factory method), so a future
  Redis/Aerospike backend slots in behind the same Cache port without touching
  callers. Only the in-process LRU is registered for now.

  Scenario: the default backend name builds the in-process LRU
    When I build the cache backend "lru"
    Then it is an in-process LRU cache

  Scenario: an unknown backend name is rejected
    When I build the cache backend "redis"
    Then building the backend fails
