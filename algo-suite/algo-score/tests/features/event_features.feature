Feature: Event features
  events/gpr.py and events/gdelt.py each turn one source's daily event-derived
  series into a minute-bucketed feature, written to
  parquet/events/_features/... (algo-score/SPEC.md §6.2), by forward-filling
  the most recent prior daily value onto the price-aligned minute grid — no
  interpolation, no fabricated value before the first observation, and no
  look-ahead: a day's aggregate only becomes visible at 00:00 UTC the next day. These are
  event-derived regime signals (GPR index level; a GDELT GoldsteinScale/
  AvgTone aggregate) and are never labeled "sentiment" — the output columns
  are `gpr` and `event_intensity` per SPEC.md §6.2, keeping them unambiguously
  distinct from actual FinBERT/LM sentiment (scorers/, a separate lane, out of
  scope here).

  Background:
    Given canonical event Parquet exists for gdelt and gpr

  # event-features-01
  Scenario Outline: A daily series is forward-filled onto the minute grid
    Given a daily <source> series
    When I build event features
    Then each minute carries the most recent prior daily <column> value

    Examples:
      | source | column          |
      | gpr    | gpr             |
      | gdelt  | event_intensity |

  # event-features-01b
  Scenario Outline: A day's aggregate is not visible until the next UTC day
    Given a daily <source> series
    When I build event features
    Then the last minute of 2020-01-06 still carries the 2020-01-05 <column> value
    And the first minute of 2020-01-07 carries the 2020-01-06 <column> value

    Examples:
      | source | column          |
      | gpr    | gpr             |
      | gdelt  | event_intensity |

  # event-features-02
  Scenario Outline: A gap in the daily series carries forward, never interpolates
    Given a daily <source> series with a missing day
    When I build event features
    Then minutes in the missing day carry the last known prior <column> value
    And no value is interpolated between the surrounding days

    Examples:
      | source | column          |
      | gpr    | gpr             |
      | gdelt  | event_intensity |

  # event-features-03
  Scenario Outline: Minutes before any data exists have no feature value
    Given a daily <source> series whose first observation is on day 2
    When I build event features
    Then minutes before day 2 have no <column> value
    And that absence is not fabricated as zero

    Examples:
      | source | column          |
      | gpr    | gpr             |
      | gdelt  | event_intensity |

  # event-features-04
  Scenario: GDELT event_intensity is the unweighted mean of goldstein_scale per day
    Given GDELT events on 2020-01-05 with goldstein_scale -4.0, 2.0, and 6.0
    When I build event features
    Then every minute of 2020-01-06 carries event_intensity 1.3333333333333333
    And avg_tone is not folded into event_intensity

  # event-features-05
  Scenario: GDELT QA fixture path is accepted
    Given flat GDELT events on 2020-01-05 with goldstein_scale -4.0, 2.0, and 6.0
    When I build event features
    Then every minute of 2020-01-06 carries event_intensity 1.3333333333333333

  # event-features-06
  Scenario: Unknown event feature kind fails fast
    When I build event features for unknown kind "nope"
    Then the run exits non-zero
    And the output names the known event feature kinds

  # event-features-07
  Scenario Outline: Source-specific event helpers build feature partitions
    Given a daily <source> series
    When I build event features through the <source> helper
    Then each minute carries the most recent prior daily <column> value

    Examples:
      | source | column          |
      | gpr    | gpr             |
      | gdelt  | event_intensity |
