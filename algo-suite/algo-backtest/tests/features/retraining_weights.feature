Feature: Exponential recency weights and feasibility checks (Story 19, T4)
  Policy E weights each training observation by how old it is at the stage cutoff:

      age_days = (cutoff - available_at) / 86400      elapsed UTC days, fractional
      w_raw    = 2 ** (-age_days / half_life_days)   (RWT-04)
      w_norm   = n * w_raw / sum(w_raw)              mean one per fitting stage (RWT-05)
      n_eff    = sum(w)^2 / sum(w^2)                 weight concentration, not power

  The proposed half-life is 60 elapsed calendar days. Normalization is applied
  independently inside each fitting stage so the total sample weight equals the
  row count and regularization is not silently changed. Uniform weights are all
  ones. Invalid inputs (non-positive or non-finite half-life, availability after the
  cutoff, naive or non-UTC timestamps, negative or non-finite weights, zero total
  weight) are rejected rather than silently repaired (RWT-02). Support minima are
  checked against measured counts and the failure states measured versus required
  (RWT-06).

  Rule: Raw weights halve every half-life of elapsed UTC days (RWT-04)

    Scenario: The spec's analytic fixture: ages 0, h and 2h at half-life 60 days
      Given the stage cutoff 2016-03-01T00:00:00Z and half-life 60 days
      And rows available at
        | key | available_at         |
        | a   | 2016-03-01T00:00:00Z |
        | b   | 2016-01-01T00:00:00Z |
        | c   | 2015-11-02T00:00:00Z |
      When the exponential weights are computed
      Then the ages in days are 0, 60, 120
      And the raw weights are 1.0, 0.5, 0.25

    Scenario Outline: Age is elapsed time in UTC days, fractional, across month and year ends (<case>)
      Given the stage cutoff <cutoff> and half-life <half_life> days
      And rows available at
        | key | available_at   |
        | r   | <available_at> |
      When the exponential weights are computed
      Then the ages in days are <age>
      And the raw weights are <weight>

      Examples:
        | case                                    | cutoff               | available_at         | half_life | age                | weight              |
        | available exactly at the cutoff         | 2016-03-01T00:00:00Z | 2016-03-01T00:00:00Z | 60        | 0                  | 1.0                 |
        | half a day old                          | 2016-03-01T00:00:00Z | 2016-02-29T12:00:00Z | 60        | 0.5                | 0.9942404238175473  |
        | thirty days old (half a half-life)      | 2016-03-01T00:00:00Z | 2016-01-31T00:00:00Z | 60        | 30                 | 0.7071067811865476  |
        | one hour past a half-life, over New Year| 2016-03-01T00:00:00Z | 2015-12-31T23:00:00Z | 60        | 60.041666666666664 | 0.49975938181133317 |
        | a 30-day half-life halves in 30 days    | 2016-03-01T00:00:00Z | 2016-01-31T00:00:00Z | 30        | 30                 | 0.5                 |
        | one half-life on the January-2017 side  | 2017-01-01T00:00:00Z | 2016-11-02T00:00:00Z | 60        | 60                 | 0.5                 |

  Rule: Mean-one normalization makes the weights sum to the row count, per stage (RWT-05)

    Scenario: The spec's analytic fixture normalizes to 12/7, 6/7 and 3/7
      Given the raw weights 1.0, 0.5, 0.25
      When the weights are normalized to mean one
      Then the normalized weights are 1.7142857142857142, 0.8571428571428571, 0.42857142857142855
      And the normalized weights sum to 3.0

    Scenario: Arbitrary positive weights keep their ratios and sum to the row count
      Given the raw weights 2.0, 3.0, 5.0
      When the weights are normalized to mean one
      Then the normalized weights are 0.6, 0.9, 1.5
      And the normalized weights sum to 3.0

    Scenario: Normalization is independent per stage: the same rows get different weights under different cutoffs
      Given rows available at
        | key | available_at         |
        | a   | 2015-12-31T00:00:00Z |
        | b   | 2015-11-01T00:00:00Z |
      When the exponential weights are computed for the family stage with cutoff 2015-12-31T00:00:00Z and half-life 60 days
      And the exponential weights are computed for the combiner stage with cutoff 2016-01-30T00:00:00Z and half-life 60 days
      Then the family-stage normalized weights are 1.3333333333333333, 0.6666666666666666
      And the combiner-stage normalized weights are 1.3333333333333333, 0.6666666666666666
      And the family-stage raw weights are 1.0, 0.5
      And the combiner-stage raw weights are 0.7071067811865476, 0.3535533905932738

  Rule: Effective N describes weight concentration (RWT-06 input)

    Scenario: The spec's analytic fixture has effective N 7/3
      Given the raw weights 1.0, 0.5, 0.25
      When the effective N is computed
      Then the effective N is 2.3333333333333335

    Scenario: Effective N is invariant to mean-one normalization
      Given the raw weights 2.0, 3.0, 5.0
      When the effective N is computed
      Then the effective N is 2.6315789473684212
      When the weights are normalized to mean one and the effective N is computed again
      Then the effective N is 2.6315789473684212

  Rule: Uniform weights are all ones and behave as an unweighted fit

    Scenario Outline: Uniform weights for <n> rows are all 1.0 with effective N <n>
      When uniform weights are requested for <n> rows
      Then there are <n> weights, all equal to 1.0
      And normalizing them to mean one leaves them unchanged
      And their effective N is <n_eff>

      Examples:
        | n    | n_eff  |
        | 1    | 1.0    |
        | 3    | 3.0    |
        | 1000 | 1000.0 |

    Scenario: Uniform weights for zero rows are refused
      When requesting uniform weights for 0 rows fails
      Then the weight failure names "at least one"

  Rule: Invalid configurations are rejected, never silently repaired (RWT-02)

    Scenario Outline: An invalid half-life is rejected (<case>)
      Given the stage cutoff 2016-03-01T00:00:00Z and half-life <half_life> days
      And rows available at
        | key | available_at         |
        | a   | 2016-02-01T00:00:00Z |
      When computing the exponential weights fails
      Then the weight failure names "half_life_days"
      And the weight failure names "<fragment>"

      Examples:
        | case            | half_life | fragment |
        | zero            | 0         | positive |
        | negative        | -60       | positive |
        | positive infinity | inf     | finite   |
        | not a number    | nan       | finite   |

    Scenario: A row available after the cutoff (negative age) is rejected naming the row
      Given the stage cutoff 2016-03-01T00:00:00Z and half-life 60 days
      And rows available at
        | key    | available_at         |
        | ok     | 2016-02-01T00:00:00Z |
        | future | 2016-03-01T00:00:01Z |
      When computing the exponential weights fails
      Then the weight failure names "future"
      And the weight failure names "after the cutoff"

    Scenario Outline: Naive or non-UTC timestamps are rejected (<case>)
      Given the stage cutoff <cutoff> and half-life 60 days
      And rows available at
        | key | available_at   |
        | a   | <available_at> |
      When computing the exponential weights fails
      Then the weight failure names "UTC"

      Examples:
        | case                     | cutoff                    | available_at              |
        | naive availability       | 2016-03-01T00:00:00Z      | 2016-02-01T00:00:00       |
        | non-UTC availability     | 2016-03-01T00:00:00Z      | 2016-02-01T00:00:00+01:00 |
        | naive cutoff             | 2016-03-01T00:00:00       | 2016-02-01T00:00:00Z      |

    Scenario: No rows means no weights: an empty stage is refused
      Given the stage cutoff 2016-03-01T00:00:00Z and half-life 60 days
      And no rows
      When computing the exponential weights fails
      Then the weight failure names "at least one"

    Scenario Outline: Explicit weights that are negative, non-finite or of zero total mass are refused (<case>)
      Given the raw weights <weights>
      When <operation> fails
      Then the weight failure names "<fragment>"

      Examples:
        | case                              | weights           | operation                            | fragment    |
        | a negative weight                 | 1.0, -0.5, 0.25   | normalizing to mean one              | negative    |
        | a NaN weight                      | 1.0, nan, 0.25    | normalizing to mean one              | finite      |
        | an infinite weight                | 1.0, inf, 0.25    | normalizing to mean one              | finite      |
        | all-zero weights (zero mass)      | 0.0, 0.0, 0.0     | normalizing to mean one              | zero total  |
        | all-zero weights for effective N  | 0.0, 0.0          | computing the effective N            | zero total  |
        | a negative weight for effective N | 1.0, -1.0         | computing the effective N            | negative    |
        | no weights at all                 |                   | normalizing to mean one              | at least one|

  Rule: Extreme scales keep the analytic ratios (numerically stable relative exponents)

    Scenario: Very old rows keep the exact half-life ratio after normalization
      Given the stage cutoff 2016-03-01T00:00:00Z and half-life 60 days
      And rows with ages in days
        | key | age_days |
        | a   | 1200     |
        | b   | 1260     |
      When the exponential weights are computed
      Then the raw weights are 9.5367431640625e-07, 4.76837158203125e-07
      And the normalized weights are 1.3333333333333333, 0.6666666666666666
      And the effective N is 1.8

    Scenario: A row far beyond representable age underflows to zero weight without producing NaN or infinity
      Given the stage cutoff 2016-03-01T00:00:00Z and half-life 1 days
      And rows with ages in days
        | key  | age_days |
        | now  | 0        |
        | old  | 5000     |
      When the exponential weights are computed
      Then the raw weights are 1.0, 0.0
      And the normalized weights are 2.0, 0.0
      And the effective N is 1.0

    Scenario: When every raw weight underflows to zero the stage is rejected as unrepresentable rather than renormalized from nothing
      Given the stage cutoff 2016-03-01T00:00:00Z and half-life 1 days
      And rows with ages in days
        | key | age_days |
        | a   | 70000    |
        | b   | 70060    |
      When computing the exponential weights fails
      Then the weight failure names "zero total"
      And the weight failure names "half_life_days"

  Rule: Support minima are checked with measured versus required counts (RWT-06)

    Scenario Outline: Each registered minimum is enforced at its boundary for the <stage> stage (<case>)
      Given the registered support minima
        | stage     | min_rows | min_per_class | min_effective_n |
        | family    | 1000     | 50            | 200             |
        | combiner  | 100      | 20            | 50              |
        | threshold | 100      | none          | none            |
      And <rows> labeled rows with <up> UP and <down> DOWN
      And weights where the first <unit_rows> rows weigh 1.0 and the rest weigh 0.0
      When the <stage> stage support is checked
      Then the support check <outcome>

      Examples:
        | stage     | case                                  | rows | up  | down | unit_rows | outcome                                                          |
        | family    | exactly at every minimum              | 1000 | 950 | 50   | 200       | passes                                                           |
        | family    | one row short                         | 999  | 949 | 50   | 200       | fails naming "rows: measured 999, required 1000"                 |
        | family    | one DOWN row short                    | 1000 | 951 | 49   | 200       | fails naming "class 0: measured 49, required 50"                 |
        | family    | one UP row short                      | 1000 | 49  | 951  | 200       | fails naming "class 1: measured 49, required 50"                 |
        | family    | effective N one short                 | 1000 | 950 | 50   | 199       | fails naming "effective N: measured 199.0, required 200"         |
        | family    | a one-class span                      | 1000 | 1000| 0    | 1000      | fails naming "class 0: measured 0, required 50"                  |
        | combiner  | exactly at every minimum              | 100  | 80  | 20   | 50        | passes                                                           |
        | combiner  | one row short                         | 99   | 79  | 20   | 50        | fails naming "rows: measured 99, required 100"                   |
        | combiner  | one class short                       | 100  | 81  | 19   | 50        | fails naming "class 0: measured 19, required 20"                 |
        | combiner  | effective N one short                 | 100  | 80  | 20   | 49        | fails naming "effective N: measured 49.0, required 50"           |
        | threshold | exactly at the row minimum            | 100  | 100 | 0    | 100       | passes                                                           |
        | threshold | one row short                         | 99   | 99  | 0    | 99        | fails naming "rows: measured 99, required 100"                   |

    Scenario: A support failure reports the stage, every measured count and every required minimum together
      Given the registered support minima
        | stage  | min_rows | min_per_class | min_effective_n |
        | family | 1000     | 50            | 200             |
      And 10 labeled rows with 6 UP and 4 DOWN
      And weights where the first 10 rows weigh 1.0 and the rest weigh 0.0
      When the family stage support is checked
      Then the support check fails naming "family"
      And the support check fails naming "rows: measured 10, required 1000"
      And the support check fails naming "class 0: measured 4, required 50"
      And the support check fails naming "class 1: measured 6, required 50"
      And the support check fails naming "effective N: measured 10.0, required 200"

    Scenario: Weights and labels of different lengths cannot be checked
      Given the registered support minima
        | stage  | min_rows | min_per_class | min_effective_n |
        | family | 1000     | 50            | 200             |
      And 10 labeled rows with 6 UP and 4 DOWN
      And 9 explicit weights of 1.0
      When checking the family stage support fails
      Then the weight failure names "10"
      And the weight failure names "9"
