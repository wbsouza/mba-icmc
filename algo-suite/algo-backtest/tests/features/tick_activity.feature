Feature: Canonical minute tick activity without invented evidence
  Canonical prices supply quote tick counts, not traded volume.
  Only an explicitly marked fill-forward bar contributes an invented zero.

  Scenario: Exact minute lookup reads canonical prices without changing their bytes
    Given canonical tick counts for EURUSD in January and February
    When January minutes are read out of order
    Then each minute has its own canonical count
    And the canonical source files are unchanged

  Scenario: Only the requested month is opened and one month remains cached
    Given canonical tick counts for EURUSD in January and February
    When January is read with an unreadable February partition
    Then January is available from the month cache after its file is removed
    When February is restored and read
    Then returning to the removed January partition fails with remediation

  Scenario: A real missing minute never borrows previous or future activity
    Given canonical tick counts for EURUSD in January and February
    When an absent real January minute is requested
    Then tick lookup fails mentioning "no tick_count" and "download/transform"

  Scenario: Missing price partitions fail with actionable remediation
    Given an empty canonical price root
    When a real January minute is requested
    Then tick lookup fails mentioning "canonical" and "download/transform"

  Scenario: Fill-forward is explicitly zero without requiring a partition
    Given an empty canonical price root
    When a January fill-forward minute is requested
    Then the tick count is 0

  Scenario: Fill-forward never inherits a stored nonzero count
    Given canonical tick counts for EURUSD in January and February
    When a stored January minute is requested as fill-forward
    Then the tick count is 0

  Scenario Outline: A malformed lookup time cannot be rounded or normalized
    Given an empty canonical price root
    When a lookup uses timestamp <timestamp> and fill-forward <fill_forward>
    Then tick lookup fails mentioning "UTC minute start" and "supply"
    Examples:
      | timestamp                        | fill_forward |
      | null                             | false        |
      | text                             | false        |
      | 2020-01-01T00:00:00              | false        |
      | 2020-01-01T00:00:00+01:00        | false        |
      | 2020-01-01T00:00:01+00:00        | false        |
      | 2020-01-01T00:00:00.000001+00:00 | false        |
      | 2020-01-01T00:00:01+00:00        | true         |

  Scenario Outline: Fill-forward must be an explicit boolean
    Given an empty canonical price root
    When a lookup uses a fill-forward flag of <flag>
    Then tick lookup fails mentioning "fill_forward" and "boolean"
    Examples:
      | flag    |
      | null    |
      | 0       |
      | 1       |
      | "false" |

  Scenario Outline: Invalid canonical partitions fail without coercion
    Given a January canonical partition containing <defect>
    When a real January minute is requested
    Then tick lookup fails mentioning "<reason>" and "download/transform"
    And the canonical source files are unchanged
    Examples:
      | defect             | reason          |
      | duplicate minutes  | duplicate       |
      | negative count     | tick_count      |
      | fractional count   | tick_count      |
      | integral float count | tick_count    |
      | boolean count      | tick_count      |
      | string count       | tick_count      |
      | null count         | tick_count      |
      | naive time         | UTC minute start |
      | non-UTC time       | UTC minute start |
      | second time        | UTC minute start |
      | microsecond time   | UTC minute start |
      | nanosecond time    | UTC minute start |
      | null time          | UTC minute start |
      | string time        | UTC minute start |
      | wrong month        | partition month |
      | absent tick column | tick_count      |
      | absent time column | timestamp       |
      | corrupt parquet    | canonical       |
      | empty rows         | no tick_count   |

  Scenario: A failed month load does not publish partially validated counts
    Given a January canonical partition containing duplicate minutes
    When a real January minute is requested
    And the invalid partition is repaired and the same reader retries
    Then the tick count is 12

  Scenario: Valid nanosecond timestamps preserve exact UTC minute lookup
    Given a January canonical partition containing valid nanosecond time
    When the stored real January minute is requested
    Then the tick count is 12
    And the canonical source files are unchanged

  Scenario: Failure to load another month preserves the last valid cache
    Given canonical tick counts for EURUSD in January and February
    When January is read with an unreadable February partition
    And loading the corrupt February partition fails
    Then January is available from the month cache after its file is removed

  Scenario Outline: Relative activity uses only the previous closed counts
    Given a relative activity lookback of <lookback>
    When the closed tick counts are <counts>
    Then the activity sequence is <expected>
    Examples:
      | lookback | counts            | expected                    |
      | 3        | [10,20,30,60,10]  | [null,null,null,3,0.2727272727272727] |
      | 2        | [0,0,10,10,0]    | [null,null,null,2,0]         |
      | 2        | [0,10,10]        | [null,null,2]               |
      | 1        | [4,8,0,6]        | [null,2,0,null]             |

  Scenario Outline: Invalid lookbacks fail before any activity is observed
    When relative activity is configured with lookback <lookback>
    Then activity validation fails mentioning "lookback" and "fix"
    Examples:
      | lookback |
      | 0        |
      | -1       |
      | true     |
      | 1.5      |
      | null     |
      | "3"      |

  Scenario Outline: Invalid counts do not advance the rolling history
    Given a relative activity lookback of 2
    When count <count> is rejected between valid counts
    Then activity validation fails mentioning "tick_count" and "repair"
    And the following valid count still uses only the valid history
    Examples:
      | count |
      | -1    |
      | 1.5   |
      | true  |
      | null  |
      | "2"   |

  Scenario: Volume gating changes exactly when the previous-count baseline is ready
    Given a relative activity lookback of 2
    When the closed tick counts are [10,10,10,0]
    Then the volume veto sequence at threshold 1 is [true,true,false,true]

  Scenario Outline: Volume gating is inclusive and never directional
    When the volume gate sees <activity> at threshold <threshold>
    Then the volume gate abstains with veto <veto> and quote-count metadata
    Examples:
      | activity | threshold | veto  |
      | missing  | 1         | true  |
      | null     | 1         | true  |
      | 0        | 1         | true  |
      | 0.999    | 1         | true  |
      | 1        | 1         | false |
      | 1.001    | 1         | false |
      | 1.5      | 2         | true  |
      | 2        | 2         | false |

  Scenario Outline: Invalid activity cannot silently permit a trade
    When the volume gate rejects activity <activity>
    Then activity validation fails mentioning "relative_tick_activity" and "repair"
    Examples:
      | activity |
      | true     |
      | "1"      |
      | -1       |
      | NaN      |
      | Infinity |

  Scenario Outline: Volume configuration fails with remediation
    When volume configuration <config> is parsed
    Then activity validation fails mentioning "<reason>" and "fix"
    Examples:
      | config                              | reason                |
      | {"lookback":0}                      | lookback              |
      | {"lookback":true}                   | lookback              |
      | {"min_relative_activity":true}      | min_relative_activity |
      | {"min_relative_activity":"1"}       | min_relative_activity |
      | {"min_relative_activity":0}         | min_relative_activity |
      | {"min_relative_activity":-1}        | min_relative_activity |
      | {"min_relative_activity":NaN}       | min_relative_activity |
      | {"min_relative_activity":Infinity}  | min_relative_activity |
      | {"unknown":1}                       | unknown               |

  Scenario: An explicit valid volume configuration preserves both settings
    When valid volume configuration is parsed
    Then its lookback is 3 and its threshold is 2

  Scenario Outline: Activity provenance binds exactly the inclusive canonical month window
    Given canonical tick counts for EURUSD in January and February
    When activity provenance covers <start> through <end>
    Then the activity manifest hashes exact bytes for <months>
    And the canonical source files are unchanged
    Examples:
      | start      | end        | months           |
      | 2020-01-01 | 2020-01-01 | january          |
      | 2020-01-31 | 2020-01-31 | january          |
      | 2020-01-31 | 2020-02-01 | january,february |
      | 2020-02-01 | 2020-02-29 | february         |

  Scenario: Provenance resolves the year boundary in calendar order
    Given canonical tick counts spanning December and January
    When activity provenance covers 2019-12-31 through 2020-01-01
    Then the activity manifest hashes exact bytes for december,january
    And the canonical source files are unchanged

  Scenario: Provenance changes when only a quote tick count changes
    Given canonical tick counts for EURUSD in January and February
    When activity provenance covers 2020-01-01 through 2020-02-29
    And only the first January tick count is changed
    And activity provenance is collected again for the same window
    Then only the January digest changes and matches the new exact bytes

  Scenario: Activity provenance is independent of the data root mount point
    Given canonical tick counts for EURUSD in January and February
    When activity provenance covers 2020-01-01 through 2020-02-29
    And identical canonical files are copied to a different root
    Then the relocated activity manifest is identical

  Scenario: Provenance does not require months outside the requested window
    Given canonical tick counts for EURUSD in January and February
    And the February canonical file is absent
    When activity provenance covers 2020-01-15 through 2020-01-31
    Then the activity manifest hashes exact bytes for january

  Scenario: A missing covered month cannot produce a partial provenance manifest
    Given canonical tick counts for EURUSD in January and February
    And the February canonical file is absent
    When activity provenance is requested across the missing month
    Then tick lookup fails mentioning "month=02" and "download/transform"

  Scenario: A reversed provenance window is rejected
    Given canonical tick counts for EURUSD in January and February
    When activity provenance is requested with reversed dates
    Then tick lookup fails mentioning "window start" and "after"
