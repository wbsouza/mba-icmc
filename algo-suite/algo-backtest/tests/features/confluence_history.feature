Feature: Intensity history — frozen, causal monthly quantile snapshots (story 21, T3)
  Proves the pure snapshot calculator in `chain/intensity_history.py` (spec CC-09, CC-10,
  CC-13, CC-14, CC-31; decisions D1, D2, D8). For a decision in UTC month M the relative
  trigger's thresholds are the 10 % and 90 % quantiles of one intensity observation per
  completed signal bar whose close time lies in `[M - 30 calendar days, M)` and whose
  availability time is strictly before M. The window is thirty calendar days before the
  fixed UTC month start, not the previous calendar month, and not the first trade of the
  month. The snapshot is frozen for the whole month: a mid-month start rebuilds the
  same one; rows that arrive or are revised later never change it (CC-10).

  Each observation is `IntensityObservation(bar_closed_at, available_at, intensity,
  source_id)`: two timezone-aware UTC times, a finite value and the identity of the
  source it came from. Observations must arrive in strictly increasing `bar_closed_at`
  order; sorting values for the quantile is not permission to repair event order.
  Quantiles use linear interpolation at index `(n - 1) * q` over the sorted sample
  (numpy `quantile(..., method="linear")` semantics), q = 0.10 and 0.90.

  `IntensitySnapshot` fields: `cutoff` (M), `window_start` (M - 30 d), `clock_minutes`,
  `q_low`, `q_high`, `sample_count`, `max_closed_at`, `max_available_at`, `source_hash`,
  `quantile_method` ("linear"), `schema_version` (1) and `status` ("READY" or "WARMUP").
  A WARMUP snapshot (the declared collection started after `window_start`) carries null
  quantiles and is the trigger's cue to HOLD (CC-14); a window the collection should
  cover but does not is a hard failure naming the interval (CC-13).

  The reference archive used below: 30 daily bars (clock 1440) closing at 00:00 UTC on
  2016-03-02 through 2016-03-31, available at their close, intensities in time order
  0.05 × {30, 5, 22, 1, 18, 29, 12, 3, 26, 8, 15, 20, 4, 25, 7, 2, 28, 11, 19, 6, 24,
  14, 9, 27, 17, 13, 23, 10, 21, 16} — every multiple of 0.05 from 0.05 to 1.50 once.
  Sorted, index 2.9 interpolates 0.15→0.20 giving q10 = 0.195; index 26.1 interpolates
  1.35→1.40 giving q90 = 1.355.

  Rule: The calibration window is thirty calendar days before the fixed UTC month start (D1)

    Scenario Outline: a decision at <decision> calibrates on [<window_start>, <cutoff>) (<case>)
      When the calibration window for decision time "<decision>" is derived
      Then the calibration cutoff is "<cutoff>"
      And the calibration window_start is "<window_start>"

      Examples:
        | case                                     | decision                  | cutoff                    | window_start              |
        | mid-month decision                       | 2016-04-17T10:00:00+00:00 | 2016-04-01T00:00:00+00:00 | 2016-03-02T00:00:00+00:00 |
        | the first minute of the month            | 2016-04-01T00:00:00+00:00 | 2016-04-01T00:00:00+00:00 | 2016-03-02T00:00:00+00:00 |
        | the last hour of the previous month      | 2016-03-31T23:00:00+00:00 | 2016-03-01T00:00:00+00:00 | 2016-01-31T00:00:00+00:00 |
        | a leap-year February behind the window   | 2016-03-01T00:00:00+00:00 | 2016-03-01T00:00:00+00:00 | 2016-01-31T00:00:00+00:00 |
        | a Sunday-evening first trade of the month| 2016-05-01T22:00:00+00:00 | 2016-05-01T00:00:00+00:00 | 2016-04-01T00:00:00+00:00 |
        | a year boundary                          | 2017-01-03T09:00:00+00:00 | 2017-01-01T00:00:00+00:00 | 2016-12-02T00:00:00+00:00 |

    Scenario: a naive decision time is refused
      When the calibration window for a naive decision time "2016-04-17T10:00:00" is derived and fails
      Then the history failure names "must be timezone-aware UTC"

  Rule: q10 and q90 are linear-interpolation quantiles of one observation per completed bar in the window (CC-09)

    Scenario: the reference daily archive gives q10 0.195 and q90 1.355 for April 2016
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed
      Then the snapshot status is "READY"
      And the snapshot q_low is 0.195
      And the snapshot q_high is 1.355
      And the snapshot sample_count is 30
      And the snapshot cutoff is "2016-04-01T00:00:00+00:00"
      And the snapshot window_start is "2016-03-02T00:00:00+00:00"
      And the snapshot clock_minutes is 1440
      And the snapshot max_closed_at is "2016-03-31T00:00:00+00:00"
      And the snapshot max_available_at is "2016-03-31T00:00:00+00:00"
      And the snapshot quantile_method is "linear"
      And the snapshot schema_version is 1

    Scenario: an hourly archive is sampled once per completed H1 bar, window edges inclusive-exclusive
      Given an intensity history on a 60-minute clock with collection declared from 2016-01-01T00:00:00Z
      And hourly observations closing every hour from 2016-03-01T22:00:00Z through 2016-04-01T02:00:00Z available at close, with intensities cycling through 0.3, 0.1, 0.2
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed
      Then the snapshot sample_count is 720
      And the snapshot q_low is 0.1
      And the snapshot q_high is 0.3
      And the snapshot max_closed_at is "2016-03-31T23:00:00+00:00"
      And the snapshot window_start is "2016-03-02T00:00:00+00:00"
      And the snapshot clock_minutes is 60

    Scenario: a bar closing exactly at the cutoff belongs to the next month, a bar closing exactly at window_start is in
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-01 available at close, with intensities in time order:
        """
        9.00
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        9.00
        """
      When the intensity snapshot for decision time "2016-04-15T12:00:00Z" is computed
      Then the snapshot sample_count is 30
      And the snapshot q_low is 0.195
      And the snapshot q_high is 1.355
      And the snapshot max_closed_at is "2016-03-31T00:00:00+00:00"

  Rule: Only observations available strictly before the cutoff enter the sample (D2)

    Scenario: an observation available exactly at the cutoff is excluded and the quantiles move
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      And the observation closing at "2016-03-31T00:00:00Z" became available at "2016-04-01T00:00:00Z"
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed
      Then the snapshot sample_count is 29
      And the snapshot q_low is 0.19
      And the snapshot q_high is 1.36
      And the snapshot max_closed_at is "2016-03-30T00:00:00+00:00"
      And the snapshot max_available_at is "2016-03-30T00:00:00+00:00"

    Scenario: an observation available one second before the cutoff is included
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      And the observation closing at "2016-03-31T00:00:00Z" became available at "2016-03-31T23:59:59Z"
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed
      Then the snapshot sample_count is 30
      And the snapshot q_high is 1.355
      And the snapshot max_available_at is "2016-03-31T23:59:59+00:00"

  Rule: The snapshot is frozen for the month: same result from any start day, unchanged by later or revised rows (CC-10)

    Scenario: a mid-month start computes the same snapshot as a month-start run
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        1.90 0.10 0.10 0.10 0.10 0.10 0.10 0.10 0.10 0.10
        0.10 0.10 0.10 0.10 0.10 0.10 0.10
        """
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed
      And the intensity snapshot for decision time "2016-04-17T10:00:00Z" is computed
      Then the two snapshots are equal
      And the snapshot q_low is 0.195
      And the snapshot q_high is 1.355
      And the snapshot cutoff is "2016-04-01T00:00:00+00:00"

    Scenario: rows that arrive after the snapshot froze do not change it, and a repeat lookup is identical
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed
      And a later observation closing at "2016-04-01T00:00:00Z" with intensity 9.0 available at "2016-04-01T00:00:00Z" is recorded
      And a later observation closing at "2016-04-02T00:00:00Z" with intensity 9.0 available at "2016-04-02T00:00:00Z" is recorded
      And the intensity snapshot for decision time "2016-04-20T00:00:00Z" is computed
      Then the two snapshots are equal
      And the snapshot sample_count is 30
      And the snapshot q_high is 1.355

    Scenario: a frozen bar cannot be rewritten in place: a re-recorded close is rejected and the snapshot stands
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed
      And an observation closing at "2016-03-31T00:00:00Z" with intensity 9.0 available at "2016-03-31T00:00:00Z" is recorded and fails
      Then the history failure names "bar_closed_at 2016-03-31T00:00:00+00:00 is not after the last recorded 2016-03-31T00:00:00+00:00"
      And the intensity snapshot for decision time "2016-04-01T00:00:00Z" still has q_high 1.355
      And the history holds 30 observations

    Scenario: the next month gets its own snapshot from its own window
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10 0.20 0.30
        0.10 0.20 0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10
        0.20 0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10 0.20
        """
      When the intensity snapshot for decision time "2016-04-30T23:00:00Z" is computed
      And the intensity snapshot for decision time "2016-05-01T00:00:00Z" is computed
      Then the first snapshot has cutoff "2016-04-01T00:00:00+00:00", q_low 0.195 and q_high 1.355
      And the second snapshot has cutoff "2016-05-01T00:00:00+00:00", q_low 0.1 and q_high 0.3
      And the second snapshot sample_count is 30

  Rule: Provenance is part of the snapshot and round-trips through plain values (CC-31)

    Scenario: the snapshot mapping carries every provenance field as a plain JSON-safe value
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed
      Then the snapshot mapping has exactly the keys "cutoff, window_start, clock_minutes, q_low, q_high, sample_count, max_closed_at, max_available_at, source_hash, quantile_method, schema_version, status"
      And the snapshot mapping survives a JSON round trip
      And the snapshot mapping loads back as an equal snapshot
      And the snapshot mapping records cutoff "2016-04-01T00:00:00+00:00" as an ISO-8601 string
      And the snapshot source_hash is a 64-character hexadecimal string

    Scenario: the source hash covers the sampled observations and nothing else
      Given two intensity histories on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And both are fed daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      And only the second is fed an observation closing at "2016-04-01T00:00:00Z" with intensity 9.0 available at "2016-04-01T00:00:00Z"
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed on both
      Then the two snapshots have the same source_hash
      And the two snapshots are equal

    Scenario: one differing sampled value changes the source hash
      Given two intensity histories on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And both are fed daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      And in the second the observation closing at "2016-03-16T00:00:00Z" has intensity 0.36 instead
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed on both
      Then the two snapshots have different source_hash values

  Rule: A valid but incomplete initial collection is WARMUP, not a failure (CC-14, D8)

    Scenario: a collection that started inside the window reports WARMUP with null quantiles
      Given an intensity history on a 1440-minute clock with collection declared from 2016-03-20T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-21 available at close, with intensities in time order:
        """
        0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10
        """
      When the intensity snapshot for decision time "2016-04-05T10:00:00Z" is computed
      Then the snapshot status is "WARMUP"
      And the snapshot q_low is null
      And the snapshot q_high is null
      And the snapshot sample_count is 11
      And the snapshot cutoff is "2016-04-01T00:00:00+00:00"
      And the snapshot window_start is "2016-03-02T00:00:00+00:00"

    Scenario: the first month whose whole window is covered by the collection is READY
      Given an intensity history on a 1440-minute clock with collection declared from 2016-03-20T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-21 available at close, with intensities in time order:
        """
        0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10
        0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10 0.20 0.30
        0.10 0.20 0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10
        0.20 0.30 0.10 0.20 0.30 0.10 0.20 0.30 0.10 0.20
        """
      When the intensity snapshot for decision time "2016-05-01T00:00:00Z" is computed
      Then the snapshot status is "READY"
      And the snapshot sample_count is 30
      And the snapshot q_low is 0.1
      And the snapshot q_high is 0.3
      And the snapshot window_start is "2016-04-01T00:00:00+00:00"

  Rule: Missing, malformed or unordered history is a hard failure naming the interval and the fix (CC-13)

    Scenario: a bar the collection should cover but does not fails naming the missing close
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      And the observation closing at "2016-03-18T00:00:00Z" is removed
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed and fails
      Then the history failure names "no observation for the bar closing at 2016-03-18T00:00:00+00:00"
      And the history failure names "window [2016-03-02T00:00:00+00:00, 2016-04-01T00:00:00+00:00)"
      And the history failure names "backfill the archive or register the closure"

    Scenario: a gap inside a documented market closure is not a missing bar
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And a documented market closure from "2016-03-17T00:00:00Z" to "2016-03-18T00:00:00Z"
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10 0.05 0.90 1.45 0.60 0.15 1.30 0.40
        0.75 1.00 0.20 1.25 0.35 0.10 1.40 0.55 0.95 0.30
        1.20 0.70 0.45 1.35 0.85 0.65 1.15 0.50 1.05 0.80
        """
      And the observation closing at "2016-03-18T00:00:00Z" is removed
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed
      Then the snapshot status is "READY"
      And the snapshot sample_count is 29
      And the snapshot q_low is 0.19
      And the snapshot q_high is 1.31

    Scenario: an empty archive with a collection declared before the window is a failure, not warmup
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And no observations
      When the intensity snapshot for decision time "2016-04-01T00:00:00Z" is computed and fails
      Then the history failure names "no observations in window [2016-03-02T00:00:00+00:00, 2016-04-01T00:00:00+00:00)"

    Scenario Outline: recording <case> is rejected naming the offending bar
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10
        """
      When an observation closing at "<closed_at>" with intensity <intensity> available at "<available_at>" is recorded and fails
      Then the history failure names "<fragment>"

      Examples:
        | case                        | closed_at            | intensity | available_at         | fragment                                                                  |
        | a NaN intensity             | 2016-03-05T00:00:00Z | nan       | 2016-03-05T00:00:00Z | intensity must be finite, got nan for the bar closing at 2016-03-05T00:00:00+00:00 |
        | an infinite intensity       | 2016-03-05T00:00:00Z | inf       | 2016-03-05T00:00:00Z | intensity must be finite, got inf for the bar closing at 2016-03-05T00:00:00+00:00 |
        | a duplicated bar close      | 2016-03-04T00:00:00Z | 0.5       | 2016-03-04T00:00:00Z | bar_closed_at 2016-03-04T00:00:00+00:00 is not after the last recorded 2016-03-04T00:00:00+00:00 |
        | an out-of-order bar close   | 2016-03-03T00:00:00Z | 0.5       | 2016-03-03T00:00:00Z | bar_closed_at 2016-03-03T00:00:00+00:00 is not after the last recorded 2016-03-04T00:00:00+00:00 |
        | a close off the clock grid  | 2016-03-05T06:00:00Z | 0.5       | 2016-03-05T06:00:00Z | bar_closed_at 2016-03-05T06:00:00+00:00 is not on the 1440-minute UTC grid |

    Scenario: an observation without an availability time lacks provenance and is refused
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      When an observation closing at "2016-03-02T00:00:00Z" with intensity 0.5 and no availability time is recorded and fails
      Then the history failure names "available_at is required"
      And the history failure names "2016-03-02T00:00:00+00:00"

    Scenario: an observation without a source identity is refused
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      When an observation closing at "2016-03-02T00:00:00Z" with intensity 0.5 and an empty source_id is recorded and fails
      Then the history failure names "source_id must be non-empty"

    Scenario: a rejected observation leaves the history unchanged
      Given an intensity history on a 1440-minute clock with collection declared from 2016-01-01T00:00:00Z
      And daily observations closing at 00:00 UTC from 2016-03-02 available at close, with intensities in time order:
        """
        1.50 0.25 1.10
        """
      When an observation closing at "2016-03-05T00:00:00Z" with intensity nan available at "2016-03-05T00:00:00Z" is recorded and fails
      Then the history holds 3 observations
      And the last recorded bar close is "2016-03-04T00:00:00+00:00"
