Feature: Backend API over the results database
  The TypeScript backend (server/) opens results.sqlite read-only with Node's built-in
  SQLite and answers JSON on /api/...; the React app only ever calls these endpoints.
  Unknown runs and trades answer 404 with an error message; the API is read-only.

  Background:
    Given the backend serves the fixture database

  Scenario Outline: every endpoint answers JSON with the rows the views need
    When I GET "<path>"
    Then the status is 200
    And the JSON <shape>

    Examples:
      | path                                                       | shape                                                                   |
      | /api/health                                                | has schema_version 1 and runs 1                                         |
      | /api/runs                                                  | is a list of 1 item                                                     |
      | /api/runs/20260928T010000-fixture                          | has strategy "hybrid", bar_minutes 60, closed_trades 2 and win_rate 0.5 |
      | /api/runs/20260928T010000-fixture/equity                   | is a list of 5 items                                                    |
      | /api/runs/20260928T010000-fixture/monthly                  | is a list of 2 items                                                    |
      | /api/runs/20260928T010000-fixture/parameters               | is a list of 10 items                                                   |
      | /api/runs/20260928T010000-fixture/trades                   | is a list of 2 items                                                    |
      | /api/runs/20260928T010000-fixture/decision-summary         | is a list of 3 items                                                    |
      | /api/runs/20260928T010000-fixture/trades/1                 | has 8 filters, 5 bars and 0 trail moves                                 |
      | /api/runs/20260928T010000-fixture/trades/5                 | has 8 filters, 5 bars and 1 trail moves                                 |

  Scenario: the run's parameter provenance and the trade detail come through the client
    When the client asks for the parameters of run "20260928T010000-fixture"
    Then the parameter "meta_learner.theta_high" is "0.55" from "h4-base/config.yaml"
    When the client asks for trade "1" of run "20260928T010000-fixture"
    Then the trade's exit kind is "target" and its F3 pattern is "hammer"

  Scenario Outline: unknown resources are refused with a message
    When I GET "<path>"
    Then the status is <status>
    And the error says "<error>"

    Examples:
      | path                                            | status | error                           |
      | /api/runs/nope                                  | 404    | run nope not found              |
      | /api/runs/20260928T010000-fixture/trades/99     | 404    | trade 99 of run                 |
      | /api/runs/20260928T010000-fixture/nothing       | 404    | route /api/runs/                |
      | /api/whatever                                   | 404    | route /api/whatever not found   |

  Scenario: the API is read-only
    When I POST "/api/runs"
    Then the status is 405

  Scenario: the client reports an unreachable backend
    When the client points at a closed port and asks for the runs
    Then the client failure says "backend unreachable"

  Scenario Outline: the server refuses a file that is not a current results database
    Given an SQLite file whose schema_version is <version>
    When the backend opens it expecting failure
    Then the open failure says "<message>"

    Examples:
      | version | message                                              |
      | none    | is not a results database                            |
      | 7       | schema version 7 is not the 1 this server reads      |

  Scenario Outline: the CLI parses its flags and refuses unknown ones
    When I parse the CLI arguments "<argv>"
    Then the parsed options are <outcome>

    Examples:
      | argv                                        | outcome                                        |
      | --db results.sqlite                         | db results.sqlite, port 8787, static none      |
      | --db x.sqlite --static dist --port 9000     | db x.sqlite, port 9000, static dist            |
      | --static dist                               | an error containing "--db <results.sqlite>"    |
      | --db x.sqlite --bogus 1                     | an error containing "unknown flag --bogus"     |
