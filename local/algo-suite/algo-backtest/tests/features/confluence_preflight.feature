Feature: Confluence preflight — input population and point-in-time availability (story 21, T9)
  Proves `experiments/confluence-chain/preflight.py`, the report that binds actual input
  coverage, population counts and news availability to each of the fourteen cells before
  any is launched (spec CC-08, CC-09, CC-13, CC-24, CC-32; decisions D2, D8). Its ledger
  reconciles five distinct counts for every (pair, clock, month): calendar-expanded rows
  (every UTC bar-length slot the calendar contains, e.g. January 2016 on H1 is 744 hourly
  slots), documented market closures, expected valid closed decision bars, warmup bars
  (declared collection has not yet reached L+1 closes or a full 30-day intensity window)
  and missing expected days/minutes (a slot the ledger expects open and ready but the
  source does not have). Calendar-expanded rows are never assumed tradable on their own;
  only "expected valid decision bars minus warmup minus missing" is ready for a cell.
  File existence and `.done` markers establish nothing about these counts — the ledger
  reads the actual row content. M-only and both drift-control arms vote only from price
  history and never gate on news availability; A, B and T-only require a provenance
  sidecar proving each intensity observation's `available_at` precedes its decision, and
  its absence is an explicit unavailable outcome (CC-32), never a silently dropped cell
  or a manufactured estimate.

  Rule: The ledger separates calendar-expanded rows from documented closures and expected valid bars (CC-24)

    Scenario: January 2016 on the H1 clock reconciles 744 calendar hours into closures and valid bars
      Given a preflight ledger for pair "EURUSD" clock 60 minutes over "2016-01-01".."2016-01-31"
      When the population ledger is computed
      Then the ledger's calendar_expanded_count is 744
      And the ledger's market_closure_count is 240
      And the ledger's expected_valid_count is 504
      And the ledger's calendar_expanded_count equals market_closure_count plus expected_valid_count

    Scenario: a three-day window spanning the weekend reconciles the same way on H1 and H4
      Given a preflight ledger for pair "EURUSD" clock 60 minutes over "2016-01-01".."2016-01-03"
      And a preflight ledger for pair "EURUSD" clock 240 minutes over "2016-01-01".."2016-01-03"
      When the population ledger is computed for both clocks
      Then the H1 ledger's calendar_expanded_count is 72
      And the H1 ledger's market_closure_count is 48
      And the H1 ledger's expected_valid_count is 24
      And the H4 ledger's calendar_expanded_count is 18
      And the H4 ledger's market_closure_count is 13
      And the H4 ledger's expected_valid_count is 5
      And the H4 ledger's expected_valid_count times 4 does not exceed the H1 ledger's expected_valid_count

    Scenario: a Monday-through-Thursday window with no weekend inside it has zero documented closures on both clocks
      Given a preflight ledger for pair "EURUSD" clock 60 minutes over "2016-01-04".."2016-01-07"
      And a preflight ledger for pair "EURUSD" clock 240 minutes over "2016-01-04".."2016-01-07"
      When the population ledger is computed for both clocks
      Then the H1 ledger's calendar_expanded_count is 96
      And the H1 ledger's market_closure_count is 0
      And the H4 ledger's calendar_expanded_count is 24
      And the H4 ledger's market_closure_count is 0
      And the H1 ledger's expected_valid_count is 96
      And the H4 ledger's expected_valid_count is 24

  Rule: Warmup and missing expected days/minutes are distinct from documented closures (CC-08, CC-24)

    Scenario: the start of the registered H1 collection is warmup, not a missing-data failure
      Given a preflight ledger for pair "EURUSD" clock 60 minutes over "2016-03-01".."2016-03-31"
      And the declared H1 collection begins 479 completed bars before the momentum window is ready
      When the population ledger is computed
      Then the ledger's warmup_count is 479
      And the ledger status is not a failure
      And the ledger's warmup_count is disjoint from its missing_count

    Scenario: the start of the registered H4 collection is warmup at L=120, not a missing-data failure
      Given a preflight ledger for pair "EURUSD" clock 240 minutes over "2016-03-01".."2016-03-31"
      And the declared H4 collection begins 119 completed bars before the momentum window is ready
      When the population ledger is computed
      Then the ledger's warmup_count is 119
      And the ledger status is not a failure

    Scenario: an expected valid bar with no source data at all is missing, not a closure and not warmup
      Given a preflight ledger for pair "EURUSD" clock 60 minutes over "2016-03-01".."2016-03-31"
      And the source has no H1 bar at "2016-03-15T09:00:00Z", an otherwise-open trading hour
      When the population ledger is computed and fails
      Then the preflight failure names "missing expected H1 bar at 2016-03-15T09:00:00+00:00"
      And the preflight failure names "1 missing expected bar(s) in 2016-03"

    Scenario: several consecutive missing expected minutes are named as one contiguous interval
      Given a preflight ledger for pair "EURUSD" clock 60 minutes over "2016-03-01".."2016-03-31"
      And the source has no H1 bars from "2016-03-15T09:00:00Z" through "2016-03-15T12:00:00Z"
      When the population ledger is computed and fails
      Then the preflight failure names "missing expected H1 bars 2016-03-15T09:00:00+00:00..2016-03-15T12:00:00+00:00 (4 bars)"

  Rule: File presence and .done markers alone never establish completeness (CC-24)

    Scenario: a plausibly sized source file with a .done marker but an internal missing minute still fails
      Given a preflight ledger for pair "EURUSD" clock 60 minutes over "2016-03-01".."2016-03-31"
      And the source partition file exists, has a plausible size, and carries a .done marker
      And the source has no H1 bar at "2016-03-15T09:00:00Z", an otherwise-open trading hour
      When the population ledger is computed and fails
      Then the preflight failure names "missing expected H1 bar at 2016-03-15T09:00:00+00:00"

    Scenario: an absent required source partition fails with a remediation naming the exact path
      Given a preflight ledger for pair "EURUSD" clock 60 minutes over "2016-03-01".."2016-03-31"
      And the source partition for "2016-03" does not exist
      When the population ledger is computed and fails
      Then the preflight failure names "missing source partition"
      And the preflight failure names the exact missing partition path
      And the preflight failure names how to materialize it

  Rule: M-only and both drift controls never gate on news availability (CC-24, D9)

    Scenario Outline: the <arm> arm's ledger requires no news availability proof (<case>)
      Given a preflight ledger for the "<arm>" arm on clock 60 minutes over "2016-03-01".."2016-03-31"
      And no availability provenance sidecar exists for that window
      When the population ledger is computed
      Then the ledger status is not a failure
      And the ledger's news_availability_required is false

      Examples:
        | case                          | arm          |
        | momentum-only needs no news   | M-only       |
        | always-short needs no news    | always-short |
        | always-long needs no news     | always-long  |

  Rule: A, B and T-only require a provenance sidecar; its absence is an explicit unavailable outcome, not a silent drop (CC-13, CC-32)

    Scenario Outline: the <arm> arm requires an availability provenance sidecar (<case>)
      Given a preflight ledger for the "<arm>" arm on clock 60 minutes over "2016-03-01".."2016-03-31"
      When the population ledger is computed
      Then the ledger's news_availability_required is true

      Examples:
        | case                    | arm     |
        | arm A requires news     | A       |
        | arm B requires news     | B       |
        | T-only requires news    | T-only  |

    Scenario Outline: a missing availability sidecar for a news-dependent arm is an explicit unavailable outcome (<case>)
      Given a preflight ledger for the "<arm>" arm on clock 60 minutes over "2016-03-01".."2016-03-31"
      And no availability provenance sidecar exists for that window
      When the population ledger is computed
      Then the ledger's status for "<arm>" is "unavailable"
      And the ledger names the reason "no availability provenance sidecar for 2016-03"
      And the "<arm>" cell is still listed in the ledger, not dropped

      Examples:
        | case                    | arm     |
        | arm A is unavailable    | A       |
        | arm B is unavailable    | B       |
        | T-only is unavailable   | T-only  |

    Scenario: a present, valid sidecar proving point-in-time availability lets the arm pass this gate
      Given a preflight ledger for the "A" arm on clock 60 minutes over "2016-03-01".."2016-03-31"
      And an availability provenance sidecar for that window whose every observation's available_at precedes its decision timestamp
      When the population ledger is computed
      Then the ledger's status for "A" is not "unavailable"

    Scenario: a sidecar whose availability timestamp is not strictly before the decision is refused, not trusted
      Given a preflight ledger for the "A" arm on clock 60 minutes over "2016-03-01".."2016-03-31"
      And an availability provenance sidecar for that window with one observation whose available_at is after its decision timestamp
      When the population ledger is computed and fails
      Then the preflight failure names "available_at is not strictly before its decision timestamp"

    Scenario: a sidecar whose availability timestamp exactly equals the decision timestamp is refused, not treated as strictly prior
      Given a preflight ledger for the "A" arm on clock 60 minutes over "2016-03-01".."2016-03-31"
      And an availability provenance sidecar for that window with one observation whose available_at equals its decision timestamp
      When the population ledger is computed and fails
      Then the preflight failure names "available_at is not strictly before its decision timestamp"

  Rule: The five ledger counts always reconcile for every reported cell (CC-24)

    Scenario: calendar-expanded, closures, valid, warmup and missing sum consistently for one full month
      Given a preflight ledger for pair "EURUSD" clock 60 minutes over "2016-03-01".."2016-03-31"
      And the declared H1 collection begins 479 completed bars before the momentum window is ready
      When the population ledger is computed
      Then the ledger's calendar_expanded_count equals market_closure_count plus expected_valid_count
      And the ledger's expected_valid_count equals warmup_count plus missing_count plus ready_count
