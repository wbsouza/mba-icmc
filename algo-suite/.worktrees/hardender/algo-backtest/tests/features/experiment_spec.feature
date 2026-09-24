Feature: Load a backtest experiment spec
  An experiment spec is the reproducible Chapter-4 experiment contract: a named set of
  runs, each pinning a strategy, symbol, window and parameters (an explicit nested params
  block: fast/slow/size). The schema is closed — required keys must be present and unknown
  keys are rejected. Loading is purely structural validation — running is a separate
  concern (experiment_run.feature).

  Rule: A valid spec loads its named runs

    Scenario: a spec loads each run with its id, strategy, window and params
      Given an experiment spec with runs:
        | id            | strategy    | symbol | from       | to         | fast | slow | size |
        | eurusd-may    | baseline-ma | EURUSD | 2014-05-07 | 2014-05-09 | 3    | 8    | 0.5  |
        | eurusd-june   | baseline-ma | EURUSD | 2014-06-07 | 2014-06-09 | 5    | 20   | 0.25 |
      When I load the experiment
      Then the experiment has 2 runs
      And run "eurusd-may" runs baseline-ma on EURUSD over 2014-05-07 to 2014-05-09
      And run "eurusd-june" has params fast 5, slow 20 and size 0.25

  Rule: An invalid experiment spec is rejected up front (fail fast)

    Scenario: duplicate run ids are rejected
      Given an experiment spec with runs:
        | id   | strategy    | symbol | from       | to         |
        | dup  | baseline-ma | EURUSD | 2014-05-07 | 2014-05-09 |
        | dup  | baseline-ma | EURUSD | 2014-06-07 | 2014-06-09 |
      When I load the experiment expecting failure
      Then loading fails naming the duplicate run id

    Scenario: a run missing a required field is rejected
      Given an experiment spec with runs:
        | id      | strategy    | symbol | from       |
        | no-to   | baseline-ma | EURUSD | 2014-05-07 |
      When I load the experiment expecting failure
      Then loading fails saying the run is invalid

    Scenario: a spec with no runs is rejected
      Given an experiment spec with no runs
      When I load the experiment expecting failure
      Then loading fails saying the experiment has no runs

    Scenario: a spec missing the experiment name is rejected
      Given an experiment spec with runs but no experiment name
      When I load the experiment expecting failure
      Then loading fails saying the experiment name is required

    Scenario: an unknown field is rejected (the schema is closed)
      Given an experiment spec with a run carrying an unknown "leverage" field
      When I load the experiment expecting failure
      Then loading fails naming the unknown field
