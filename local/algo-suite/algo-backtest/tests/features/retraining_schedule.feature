Feature: Exact-UTC epoch planning (Story 19, T3)
  The registered study replays one continuous account per policy across monthly
  epochs. Every epoch's deployment interval is the half-open UTC month [D, next D)
  (RWT-03), and every fitting/calibration stage is a half-open UTC span derived from
  D by the design's temporal contract (design.md "Exact proposed temporal contract"):

      C            = D - 1 day                         (one-day preparation embargo)
      family fit   = [start, C - 60d)   start = C - 60d - 180d for R,
                                        start = 2015-03-02T00:00:00Z for U and E
      combiner     = [C - 60d, C - 30d)
      threshold    = [C - 30d, C)
      deployment   = [D, next month's D)

  F and Q keep the family/combiner spans of the initial epoch (they share U's first
  bundle); Q refreshes its threshold span monthly, F keeps the initial one.

  Row membership in a span is decided by feature availability (the bar close), never
  by the stored bucket-start timestamp, and a row is admitted only if its label_time
  is strictly before the span's end (RWT-01). Eligibility is independent of whether
  the strategy vetoed the bar, traded it, or lost on it (RWT-09). The legacy
  date-based `walk_forward_split` keeps its own (date-inclusive) semantics untouched.

  Rule: The monthly schedule covers the registered span with half-open intervals, no gaps, no overlaps (RWT-03)

    Scenario: The registered trading year yields twelve contiguous monthly epochs
      When the monthly epochs from 2016-03-01T00:00:00Z to 2017-03-01T00:00:00Z are planned
      Then there are 12 epochs
      And the first epoch deploys over [2016-03-01T00:00:00Z, 2016-04-01T00:00:00Z)
      And the last epoch deploys over [2017-02-01T00:00:00Z, 2017-03-01T00:00:00Z)
      And every epoch starts exactly where the previous one ends
      And the union of the epochs is exactly [2016-03-01T00:00:00Z, 2017-03-01T00:00:00Z)

    Scenario Outline: Month, year and leap boundaries are honoured (<case>)
      When the monthly epochs from <start> to <end> are planned
      Then there are <count> epochs
      And the epoch starting <probe_start> ends at <probe_end> and lasts <days> days

      Examples:
        | case                              | start                | end                  | count | probe_start          | probe_end            | days |
        | year boundary December to January | 2016-11-01T00:00:00Z | 2017-02-01T00:00:00Z | 3     | 2016-12-01T00:00:00Z | 2017-01-01T00:00:00Z | 31   |
        | leap February 2016 has 29 days    | 2016-01-01T00:00:00Z | 2016-04-01T00:00:00Z | 3     | 2016-02-01T00:00:00Z | 2016-03-01T00:00:00Z | 29   |
        | common February 2017 has 28 days  | 2017-01-01T00:00:00Z | 2017-03-01T00:00:00Z | 2     | 2017-02-01T00:00:00Z | 2017-03-01T00:00:00Z | 28   |
        | a single-month span               | 2016-06-01T00:00:00Z | 2016-07-01T00:00:00Z | 1     | 2016-06-01T00:00:00Z | 2016-07-01T00:00:00Z | 30   |

    Scenario Outline: An invalid registered span is rejected before any epoch is produced (<case>)
      When planning the monthly epochs from <start> to <end> fails
      Then the schedule failure names "<fragment>"

      Examples:
        | case                                 | start                     | end                       | fragment       |
        | start is not a UTC month start       | 2016-03-02T00:00:00Z      | 2017-03-01T00:00:00Z      | month start    |
        | start is not at midnight             | 2016-03-01T09:00:00Z      | 2017-03-01T00:00:00Z      | month start    |
        | end is not a UTC month start         | 2016-03-01T00:00:00Z      | 2017-02-28T00:00:00Z      | month start    |
        | end equals start (empty span)        | 2016-03-01T00:00:00Z      | 2016-03-01T00:00:00Z      | after          |
        | end before start                     | 2017-03-01T00:00:00Z      | 2016-03-01T00:00:00Z      | after          |
        | naive start (no timezone)            | 2016-03-01T00:00:00       | 2017-03-01T00:00:00Z      | UTC            |
        | start in a non-UTC offset            | 2016-03-01T00:00:00+01:00 | 2017-03-01T00:00:00Z      | UTC            |

  Rule: Stage spans follow the temporal contract exactly, per policy

    Scenario Outline: The first epoch's stage spans for every policy (D = 2016-03-01, C = 2016-02-29)
      Given the registered monthly schedule from 2016-03-01T00:00:00Z to 2017-03-01T00:00:00Z
      When the stage spans of the epoch starting 2016-03-01T00:00:00Z are computed for policy <policy>
      Then the family span is [<family_start>, 2015-12-31T00:00:00Z)
      And the combiner span is [2015-12-31T00:00:00Z, 2016-01-30T00:00:00Z)
      And the threshold span is [2016-01-30T00:00:00Z, 2016-02-29T00:00:00Z)
      And the deployment span is [2016-03-01T00:00:00Z, 2016-04-01T00:00:00Z)

      Examples:
        | policy | family_start         |
        | F      | 2015-03-02T00:00:00Z |
        | Q      | 2015-03-02T00:00:00Z |
        | R      | 2015-07-04T00:00:00Z |
        | U      | 2015-03-02T00:00:00Z |
        | E      | 2015-03-02T00:00:00Z |

    Scenario Outline: Later epochs for the refitting policies R, U and E shift every stage with D (<case>)
      Given the registered monthly schedule from 2016-03-01T00:00:00Z to 2017-03-01T00:00:00Z
      When the stage spans of the epoch starting <D> are computed for policy <policy>
      Then the family span is [<family_start>, <family_end>)
      And the combiner span is [<family_end>, <combiner_end>)
      And the threshold span is [<combiner_end>, <C>)
      And the deployment span is [<D>, <next_D>)

      Examples:
        | case                                     | policy | D                    | C                    | family_start         | family_end           | combiner_end         | next_D               |
        | April 2016, C-60d crosses leap February  | R      | 2016-04-01T00:00:00Z | 2016-03-31T00:00:00Z | 2015-08-04T00:00:00Z | 2016-01-31T00:00:00Z | 2016-03-01T00:00:00Z | 2016-05-01T00:00:00Z |
        | April 2016, expanding start is fixed     | U      | 2016-04-01T00:00:00Z | 2016-03-31T00:00:00Z | 2015-03-02T00:00:00Z | 2016-01-31T00:00:00Z | 2016-03-01T00:00:00Z | 2016-05-01T00:00:00Z |
        | April 2016, E shares U's row support     | E      | 2016-04-01T00:00:00Z | 2016-03-31T00:00:00Z | 2015-03-02T00:00:00Z | 2016-01-31T00:00:00Z | 2016-03-01T00:00:00Z | 2016-05-01T00:00:00Z |
        | January 2017, year boundary              | R      | 2017-01-01T00:00:00Z | 2016-12-31T00:00:00Z | 2016-05-05T00:00:00Z | 2016-11-01T00:00:00Z | 2016-12-01T00:00:00Z | 2017-02-01T00:00:00Z |
        | January 2017, year boundary              | U      | 2017-01-01T00:00:00Z | 2016-12-31T00:00:00Z | 2015-03-02T00:00:00Z | 2016-11-01T00:00:00Z | 2016-12-01T00:00:00Z | 2017-02-01T00:00:00Z |
        | February 2017, the last epoch            | E      | 2017-02-01T00:00:00Z | 2017-01-31T00:00:00Z | 2015-03-02T00:00:00Z | 2016-12-02T00:00:00Z | 2017-01-01T00:00:00Z | 2017-03-01T00:00:00Z |

    Scenario: Policy F keeps the initial model and the initial thresholds in a later epoch
      Given the registered monthly schedule from 2016-03-01T00:00:00Z to 2017-03-01T00:00:00Z
      When the stage spans of the epoch starting 2016-04-01T00:00:00Z are computed for policy F
      Then the family span is [2015-03-02T00:00:00Z, 2015-12-31T00:00:00Z)
      And the combiner span is [2015-12-31T00:00:00Z, 2016-01-30T00:00:00Z)
      And the threshold span is [2016-01-30T00:00:00Z, 2016-02-29T00:00:00Z)
      And the deployment span is [2016-04-01T00:00:00Z, 2016-05-01T00:00:00Z)

    Scenario: Policy Q keeps the initial model but refreshes the threshold span monthly
      Given the registered monthly schedule from 2016-03-01T00:00:00Z to 2017-03-01T00:00:00Z
      When the stage spans of the epoch starting 2016-04-01T00:00:00Z are computed for policy Q
      Then the family span is [2015-03-02T00:00:00Z, 2015-12-31T00:00:00Z)
      And the combiner span is [2015-12-31T00:00:00Z, 2016-01-30T00:00:00Z)
      And the threshold span is [2016-03-01T00:00:00Z, 2016-03-31T00:00:00Z)
      And the deployment span is [2016-04-01T00:00:00Z, 2016-05-01T00:00:00Z)

    Scenario: Every stage span ends no later than the next stage begins, and all end before deployment
      Given the registered monthly schedule from 2016-03-01T00:00:00Z to 2017-03-01T00:00:00Z
      When the stage spans of every epoch are computed for policy E
      Then in every epoch the family span ends where the combiner span begins
      And in every epoch the combiner span ends where the threshold span begins
      And in every epoch the threshold span ends one day before deployment begins

    Scenario Outline: Stage spans are refused for an unregistered epoch or policy (<case>)
      Given the registered monthly schedule from 2016-03-01T00:00:00Z to 2017-03-01T00:00:00Z
      When computing the stage spans of the epoch starting <D> for policy <policy> fails
      Then the schedule failure names "<fragment>"

      Examples:
        | case                                  | D                    | policy | fragment   |
        | unknown policy                        | 2016-04-01T00:00:00Z | X      | policy     |
        | epoch outside the registered schedule | 2017-03-01T00:00:00Z | U      | registered |
        | epoch before the registered start     | 2016-02-01T00:00:00Z | U      | registered |
        | D not a month start                   | 2016-04-15T00:00:00Z | U      | registered |

  Rule: Rows join a span by availability in [start, end) with label_time strictly before end (RWT-01)

    Scenario: Availability boundaries are half-open and label maturity is strict at the span end
      Given the candidate rows
        | key    | bucket_start         | available_at         | label_time           | label |
        | before | 2016-01-29T23:00:00Z | 2016-01-30T00:00:00Z | 2016-01-30T01:00:00Z | 1     |
        | first  | 2016-01-30T00:00:00Z | 2016-01-30T01:00:00Z | 2016-01-30T02:00:00Z | 0     |
        | middle | 2016-02-10T08:00:00Z | 2016-02-10T09:00:00Z | 2016-02-10T10:00:00Z | 1     |
        | ripe   | 2016-02-28T21:00:00Z | 2016-02-28T22:00:00Z | 2016-02-28T23:59:00Z | 1     |
        | exact  | 2016-02-28T22:00:00Z | 2016-02-28T23:00:00Z | 2016-02-29T00:00:00Z | 0     |
        | at-end | 2016-02-28T23:00:00Z | 2016-02-29T00:00:00Z | 2016-02-29T01:00:00Z | 1     |
      When the rows are selected for the span [2016-01-30T00:00:00Z, 2016-02-29T00:00:00Z)
      Then the selected keys are "before, first, middle, ripe"

    Scenario: A row is placed by its close (availability), not by its bucket-start timestamp
      Given the candidate rows
        | key      | bucket_start         | available_at         | label_time           | label |
        | straddle | 2016-02-28T23:00:00Z | 2016-02-29T00:00:00Z | 2016-02-29T01:00:00Z | 1     |
        | inside   | 2016-02-28T22:00:00Z | 2016-02-28T23:00:00Z | 2016-02-28T23:30:00Z | 0     |
      When the rows are selected for the span [2016-01-30T00:00:00Z, 2016-02-29T00:00:00Z)
      Then the selected keys are "inside"
      When the rows are selected for the span [2016-02-29T00:00:00Z, 2016-03-01T00:00:00Z)
      Then the selected keys are "straddle"

    Scenario: A row whose label matures after the span end is excluded even though its features were available
      Given the candidate rows
        | key      | bucket_start         | available_at         | label_time           | label |
        | leaks    | 2016-02-28T10:00:00Z | 2016-02-28T11:00:00Z | 2016-02-29T11:00:00Z | 1     |
        | matured  | 2016-02-28T10:00:00Z | 2016-02-28T11:00:00Z | 2016-02-28T12:00:00Z | 1     |
      When the rows are selected for the span [2016-01-30T00:00:00Z, 2016-02-29T00:00:00Z)
      Then the selected keys are "matured"

    Scenario: A row with unknown label maturity is refused by the adaptive selector (RWT-24)
      Given the candidate rows
        | key     | bucket_start         | available_at         | label_time | label |
        | unknown | 2016-02-10T08:00:00Z | 2016-02-10T09:00:00Z | None       | 1     |
      When selecting the rows for the span [2016-01-30T00:00:00Z, 2016-02-29T00:00:00Z) fails
      Then the schedule failure names "label_time"
      And the schedule failure names "unknown"

    Scenario: Vetoed, untraded and losing observations stay eligible (RWT-09)
      Given the candidate rows with trade context
        | key     | available_at         | label_time           | label | vetoed | traded | trade_pnl |
        | vetoed  | 2016-02-01T09:00:00Z | 2016-02-01T10:00:00Z | 1     | yes    | no     | none      |
        | loser   | 2016-02-02T09:00:00Z | 2016-02-02T10:00:00Z | 0     | no     | yes    | -35.0     |
        | winner  | 2016-02-03T09:00:00Z | 2016-02-03T10:00:00Z | 1     | no     | yes    | 80.0      |
        | flat    | 2016-02-04T09:00:00Z | 2016-02-04T10:00:00Z | 0     | no     | no     | none      |
      When the rows are selected for the span [2016-01-30T00:00:00Z, 2016-02-29T00:00:00Z)
      Then the selected keys are "vetoed, loser, winner, flat"

    Scenario: A span with no available history selects nothing and leaves feasibility to the support check
      Given the candidate rows
        | key   | bucket_start         | available_at         | label_time           | label |
        | later | 2016-02-10T08:00:00Z | 2016-02-10T09:00:00Z | 2016-02-10T10:00:00Z | 1     |
      When the rows are selected for the span [2015-03-02T00:00:00Z, 2015-12-31T00:00:00Z)
      Then the selected keys are ""

    Scenario Outline: An invalid selection span is rejected (<case>)
      Given the candidate rows
        | key | bucket_start         | available_at         | label_time           | label |
        | one | 2016-02-10T08:00:00Z | 2016-02-10T09:00:00Z | 2016-02-10T10:00:00Z | 1     |
      When selecting the rows for the span [<start>, <end>) fails
      Then the schedule failure names "<fragment>"

      Examples:
        | case                       | start                     | end                  | fragment |
        | end not after start        | 2016-02-29T00:00:00Z      | 2016-01-30T00:00:00Z | after    |
        | empty span                 | 2016-02-29T00:00:00Z      | 2016-02-29T00:00:00Z | after    |
        | naive bound                | 2016-01-30T00:00:00       | 2016-02-29T00:00:00Z | UTC      |
        | non-UTC bound              | 2016-01-30T00:00:00+01:00 | 2016-02-29T00:00:00Z | UTC      |

  Rule: The legacy date-based walk-forward split is untouched (regression guard)

    Scenario: The legacy split still admits a label knowable exactly at the day-end boundary, which the exact-UTC selector excludes
      Given the candidate rows
        | key   | bucket_start         | available_at         | label_time           | label |
        | edge  | 2016-01-31T22:00:00Z | 2016-01-31T23:00:00Z | 2016-02-01T00:00:00Z | 1     |
        | later | 2016-02-10T08:00:00Z | 2016-02-10T09:00:00Z | 2016-02-10T10:00:00Z | 0     |
        | test  | 2016-02-20T08:00:00Z | 2016-02-20T09:00:00Z | 2016-02-20T10:00:00Z | 1     |
      When the rows are walk-forward split (legacy) at train_end 2016-01-31, validation_end 2016-02-15, test_end 2016-02-28
      Then the legacy train span holds the keys "edge"
      When the rows are selected for the span [2016-01-01T00:00:00Z, 2016-02-01T00:00:00Z)
      Then the selected keys are ""
