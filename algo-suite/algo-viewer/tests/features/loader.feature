Feature: SQLite loader
  The viewer opens a results.sqlite built by `algo-analyze results-db build` with sql.js
  (WASM bundled locally). Any other file, or another schema version, is refused with a
  message that says what to do.

  Scenario: the fixture database built by algo-analyze opens and answers the views' queries
    Given the fixture results database bytes
    When I open the database
    Then it holds 1 run, 2 trades and 2 entry decisions
    And the run "20260928T010000-fixture" is strategy "hybrid" on H1 with 2 trades and win rate 0.5
    And the run's parameter "meta_learner.theta_high" is "0.55" from "dragon08/config.yaml"
    And the run's decision funnel is:
      | final_decision | vetoed_by       | count |
      | NO_TRADE       | volume_strength | 1     |
      | BUY            |                 | 1     |
      | SELL           |                 | 1     |
    And trade "1" has 5 entry bars from offset -2 to 2

  Scenario: a file that is not a results database is refused
    Given the bytes of an empty SQLite database
    When I open the database expecting failure
    Then the failure says "not a results database"

  Scenario: a database of another schema version is refused
    Given the bytes of an SQLite database whose schema_version is 7
    When I open the database expecting failure
    Then the failure says "schema version 7 is not the 1 this viewer reads"
