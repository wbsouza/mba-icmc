Feature: Separate-span threshold calibration (Story 19, T8)
  Each epoch's q10 thresholds come from the reserved threshold span, never from the
  combiner-fit rows and never time-weighted (RWT-10, method-design.md "Weighting"):

      theta_low  = quantile(scores, 0.10)     linear (numpy's default, type 7)
      theta_high = quantile(scores, 0.90)     unweighted

  The input is the epoch model's p_hat score for every row the span admits: a scored
  row carries key, available_at (bar close), label_time and score; rows join the span
  by the same half-open selector as every other stage (`start <= available_at < end`
  and `label_time < end`, RWT-01), even though the label itself is not used. The
  registered minimum is 100 rows (RWT-06); the minimum is a parameter so the mechanics
  can be shown on a handful of rows, and its default is the registered value.

  The result is rejected (never repaired) when a score is non-finite, when fewer rows
  than the minimum are admitted, when the thresholds are not strictly increasing
  (ties), or when a threshold is not strictly inside (0, 1), because F7's terminal rule
  needs a non-empty HOLD band and F7Config refuses anything else. F7's rule stays
  strict: p_hat exactly equal to a threshold is HOLD.

  Background:
    Given the threshold span [2016-01-30T00:00:00Z, 2016-02-29T00:00:00Z)

  Rule: Thresholds are the unweighted linear 0.10 and 0.90 quantiles of the span's scores (RWT-10)

    Scenario: Eleven evenly indexed scores put the quantiles exactly on the second and tenth values
      Given the scored rows in the span
        | key | available_at         | label_time           | score |
        | s01 | 2016-02-01T09:00:00Z | 2016-02-01T10:00:00Z | 0.05  |
        | s02 | 2016-02-02T09:00:00Z | 2016-02-02T10:00:00Z | 0.10  |
        | s03 | 2016-02-03T09:00:00Z | 2016-02-03T10:00:00Z | 0.20  |
        | s04 | 2016-02-04T09:00:00Z | 2016-02-04T10:00:00Z | 0.30  |
        | s05 | 2016-02-05T09:00:00Z | 2016-02-05T10:00:00Z | 0.40  |
        | s06 | 2016-02-08T09:00:00Z | 2016-02-08T10:00:00Z | 0.50  |
        | s07 | 2016-02-09T09:00:00Z | 2016-02-09T10:00:00Z | 0.60  |
        | s08 | 2016-02-10T09:00:00Z | 2016-02-10T10:00:00Z | 0.70  |
        | s09 | 2016-02-11T09:00:00Z | 2016-02-11T10:00:00Z | 0.80  |
        | s10 | 2016-02-12T09:00:00Z | 2016-02-12T10:00:00Z | 0.90  |
        | s11 | 2016-02-15T09:00:00Z | 2016-02-15T10:00:00Z | 0.95  |
      When the thresholds are calibrated with a minimum of 5 rows
      Then theta_low is 0.1
      And theta_high is 0.9
      And the calibration used 11 rows

    Scenario Outline: Linear interpolation between order statistics, by hand (<case>)
      Given the scored rows in the span with scores <scores>
      When the thresholds are calibrated with a minimum of 5 rows
      Then theta_low is <theta_low>
      And theta_high is <theta_high>

      Examples:
        | case                                                     | scores                        | theta_low | theta_high |
        | six scores: position 0.5 between 0.0 and 0.2, 4.5 between 0.8 and 1.0 | 0.0, 0.2, 0.4, 0.6, 0.8, 1.0 | 0.1       | 0.9        |
        | five scores: position 0.4 between 0.2 and 0.4, 3.6 between 0.8 and 1.0 | 0.2, 0.4, 0.6, 0.8, 1.0      | 0.28      | 0.92       |

    Scenario: The quantiles are unweighted and order-free: shuffling the rows changes nothing
      Given the scored rows in the span with scores 0.95, 0.10, 0.80, 0.05, 0.60, 0.30, 0.90, 0.20, 0.50, 0.70, 0.40
      When the thresholds are calibrated with a minimum of 5 rows
      Then theta_low is 0.1
      And theta_high is 0.9

  Rule: F7's terminal rule treats a score exactly at a threshold as HOLD (strict inequalities)

    Scenario Outline: Calibrated thresholds 0.1/0.9 applied through F7 with the regime gate off (<case>)
      Given the scored rows in the span with scores 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95
      And the thresholds are calibrated with a minimum of 5 rows
      When a p_hat of <p_hat> is decided by F7 with the calibrated thresholds and the regime gate off
      Then F7 recommends "<recommendation>"

      Examples:
        | case                              | p_hat  | recommendation |
        | exactly theta_high holds          | 0.9    | HOLD           |
        | exactly theta_low holds           | 0.1    | HOLD           |
        | just above theta_high buys        | 0.9001 | BUY            |
        | just below theta_low sells        | 0.0999 | SELL           |
        | inside the band holds             | 0.5    | HOLD           |

  Rule: Invalid or insufficient calibration inputs are rejected, never repaired (RWT-02, RWT-06, RWT-10)

    Scenario: Tied quantiles (all scores identical) are non-increasing thresholds and are rejected
      Given 200 scored rows in the span all scoring 0.5
      When calibrating the thresholds fails
      Then the threshold failure names "non-increasing"
      And the threshold failure names "0.5"

    Scenario: A threshold on the boundary of (0, 1) is rejected because F7 needs a strict band
      Given the scored rows in the span with scores 0.0, 0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95
      When calibrating the thresholds with a minimum of 5 rows fails
      Then the threshold failure names "theta_low"
      And the threshold failure names "(0, 1)"

    Scenario Outline: A non-finite score is rejected naming the row (<case>)
      Given the scored rows in the span
        | key | available_at         | label_time           | score   |
        | ok1 | 2016-02-01T09:00:00Z | 2016-02-01T10:00:00Z | 0.2     |
        | ok2 | 2016-02-02T09:00:00Z | 2016-02-02T10:00:00Z | 0.4     |
        | bad | 2016-02-03T09:00:00Z | 2016-02-03T10:00:00Z | <score> |
        | ok3 | 2016-02-04T09:00:00Z | 2016-02-04T10:00:00Z | 0.6     |
        | ok4 | 2016-02-05T09:00:00Z | 2016-02-05T10:00:00Z | 0.8     |
      When calibrating the thresholds with a minimum of 5 rows fails
      Then the threshold failure names "finite"
      And the threshold failure names "bad"

      Examples:
        | case              | score |
        | NaN               | nan   |
        | positive infinity | inf   |
        | negative infinity | -inf  |

    Scenario Outline: Fewer admitted rows than the minimum is rejected with measured and required counts (<case>)
      Given <rows> scored rows in the span with evenly spread scores between 0.05 and 0.95
      When calibrating the thresholds <call> fails
      Then the threshold failure names "threshold"
      And the threshold failure names "rows: measured <rows>, required <required>"

      Examples:
        | case                                     | rows | call                       | required |
        | one short of the registered default      | 99   | with the registered minimum | 100      |
        | one short of an explicit minimum         | 4    | with a minimum of 5 rows    | 5        |
        | no rows at all                           | 0    | with a minimum of 5 rows    | 5        |

    Scenario: Exactly the minimum number of rows is accepted
      Given 100 scored rows in the span with evenly spread scores between 0.05 and 0.95
      When the thresholds are calibrated with the registered minimum
      Then the calibration used 100 rows
      And theta_low is below theta_high

  Rule: Only rows the span admits are scored: later, earlier and immature rows are excluded (RWT-01)

    Scenario: Rows outside the span or with a label maturing at or after its end do not move the quantiles
      Given the scored rows in the span with scores 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95
      And the extra scored rows
        | key            | available_at         | label_time           | score |
        | before         | 2016-01-29T23:00:00Z | 2016-01-30T00:30:00Z | 0.01  |
        | at-end         | 2016-02-29T00:00:00Z | 2016-02-29T01:00:00Z | 0.99  |
        | at-end-mature  | 2016-02-29T00:00:00Z | 2016-01-30T12:00:00Z | 0.99  |
        | after          | 2016-03-05T09:00:00Z | 2016-03-05T10:00:00Z | 0.99  |
        | immature       | 2016-02-28T23:00:00Z | 2016-02-29T00:00:00Z | 0.01  |
        | first          | 2016-01-30T00:00:00Z | 2016-01-30T01:00:00Z | 0.50  |
      When the thresholds are calibrated with a minimum of 5 rows
      Then the calibration used 12 rows
      And the calibrated row keys do not include "before, at-end, at-end-mature, after, immature"
      And the calibrated row keys include "first"
      And theta_low is 0.11
      And theta_high is 0.89

    Scenario: The calibration result records the span it used
      Given the scored rows in the span with scores 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95
      When the thresholds are calibrated with a minimum of 5 rows
      Then the calibration's span is [2016-01-30T00:00:00Z, 2016-02-29T00:00:00Z)
