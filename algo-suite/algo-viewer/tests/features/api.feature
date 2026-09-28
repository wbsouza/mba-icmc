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
      | /api/health                                                | has schema_version 2 and runs 1                                         |
      | /api/runs                                                  | is a list of 1 item                                                     |
      | /api/runs/20260928T010000-fixture                          | has strategy "hybrid", bar_minutes 60, closed_trades 2 and win_rate 0.5 |
      | /api/runs/20260928T010000-fixture/equity                   | is a list of 5 items                                                    |
      | /api/runs/20260928T010000-fixture/monthly                  | is a list of 2 items                                                    |
      | /api/runs/20260928T010000-fixture/parameters               | is a list of 13 items                                                   |
      | /api/runs/20260928T010000-fixture/trades                   | is a list of 2 items                                                    |
      | /api/runs/20260928T010000-fixture/decision-summary         | is a list of 5 items                                                    |
      | /api/runs/20260928T010000-fixture/open-positions           | is a list of 1 item                                                     |
      | /api/runs/20260928T010000-fixture/decisions                | is a decision log of 5 bars in 4 groups, page 1                         |
      | /api/runs/20260928T010000-fixture/decisions?mode=all&size=2&page=2 | is a decision log of 7 bars in 6 groups, page 2                 |
      | /api/runs/20260928T010000-fixture/decisions/7              | is the chain of a bar vetoed by "f4_news_context" with 4 filters        |
      | /api/runs/20260928T010000-fixture/trades/1                 | has 8 filters, 5 bars and 0 trail moves                                 |
      | /api/runs/20260928T010000-fixture/trades/1                 | has 1 event(s) while open                                               |
      | /api/runs/20260928T010000-fixture/trades/5                 | has 0 event(s) while open                                               |
      | /api/runs/20260928T010000-fixture/trades/5                 | has 8 filters, 5 bars and 1 trail moves                                 |

  Scenario: the run's parameter provenance and the trade detail come through the client
    When the client asks for the parameters of run "20260928T010000-fixture"
    Then the parameter "meta_learner.theta_high" is "0.55" from "h4-base/config.yaml"
    When the client asks for trade "1" of run "20260928T010000-fixture"
    Then the trade's exit kind is "target" and its F3 pattern is "hammer"

  Scenario Outline: pattern examples are the most recent entries that carried the pattern
    When I GET "<path>"
    Then the status is <status>
    And the JSON <shape>

    Examples:
      | path                                          | status | shape                                                          |
      | /api/patterns/hammer/examples?limit=3         | 200    | lists the example run "20260928T010000-fixture" trade "1" buy 500 |
      | /api/patterns/hammer/examples                 | 200    | is a list of 1 item                                            |
      | /api/patterns/evening_star/examples?limit=3   | 200    | is a list of 0 items                                           |
      | /api/patterns/hammer/examples?limit=0         | 400    | says "limit must be an integer between 1 and 50"               |
      | /api/patterns/hammer/examples?limit=x         | 400    | says "limit must be an integer between 1 and 50"               |

  Scenario: example selection takes distinct entry times, preferring runs not chosen yet
    Given these candidate examples, most recent first:
      | run_id | trade_id | entry_time                | direction | profit |
      | A      | 9        | 2016-12-23T09:00:00+00:00 | sell      | -57.6  |
      | B      | 9        | 2016-12-23T09:00:00+00:00 | sell      | -60.4  |
      | C      | 9        | 2016-12-23T09:00:00+00:00 | sell      | -59.1  |
      | A      | 7        | 2016-12-12T00:00:00+00:00 | sell      | -79.5  |
      | B      | 7        | 2016-12-12T00:00:00+00:00 | sell      | -79.1  |
      | A      | 5        | 2016-11-02T13:00:00+00:00 | buy       | 99.2   |
      | A      | 2        | 2016-05-02T13:00:00+00:00 | buy       | 85.6   |
    When I select 3 examples
    Then the chosen examples are A/9, B/7, A/5
    When I select 5 examples
    Then the chosen examples are A/9, B/7, A/5, A/2

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
      | 7       | schema version 7 is not the 2 this server reads      |

  Scenario Outline: the CLI parses its flags and refuses unknown ones
    When I parse the CLI arguments "<argv>"
    Then the parsed options are <outcome>

    Examples:
      | argv                                        | outcome                                        |
      | --db results.sqlite                         | db results.sqlite, port 8787, static none      |
      | --db x.sqlite --static dist --port 9000     | db x.sqlite, port 9000, static dist            |
      | --static dist                               | an error containing "--db <results.sqlite>"    |
      | --db x.sqlite --bogus 1                     | an error containing "unknown flag --bogus"     |

  Scenario Outline: the decision log refuses a bad mode, page or size
    When I GET "<path>"
    Then the status is 400
    And the error says "<text>"

    Examples:
      | path                                                              | text                                     |
      | /api/runs/20260928T010000-fixture/decisions?mode=bogus            | mode must be one of vetoes, entries, all |
      | /api/runs/20260928T010000-fixture/decisions?size=0                | size must be an integer between 1 and    |
      | /api/runs/20260928T010000-fixture/decisions?page=x                | page must be an integer between 1 and    |
      | /api/runs/20260928T010000-fixture/decisions/abc                   | decision id must be a positive integer   |
