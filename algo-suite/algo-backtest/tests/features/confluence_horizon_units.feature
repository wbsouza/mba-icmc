Feature: Horizon unit re-derivation — normalized returns versus true price pips (story 21, T8)
  Proves `experiments/confluence-chain/rederive_horizon.py`, the read-only re-derivation
  tool for the frozen session-2 H1 decision archive
  (`docs/stories/in-progress/21-confluence-chain/evidence/signal-horizon-check.md`,
  spec CC-25, CC-26). The archive's forward-return statistic is a normalized return,
  `(close[t+k]/close[t]-1)/1e-4`, not an EUR/USD price change in pips. The tool joins the
  archive's decision timestamps against timestamp-matched source close prices by exact
  UTC minute and reports both units side by side: the archived normalized-return pips and
  the true price pips, `(close[t+k]-close[t])/0.0001`, so a reader can no longer conflate
  them. It never edits, truncates, reorders or reruns the archive (CC-26); it does not
  redo the PR #87 outlier analysis. It writes only to a new, caller-specified output path,
  and the archive's own bytes are sha256-checked before and after the run and must be
  byte-for-byte identical.

  Background:
    Given the frozen signal-horizon archive at "docs/stories/in-progress/21-confluence-chain/evidence/signal-horizon-check.md"

  Rule: The same matched closes give two different pip numbers, one per unit (CC-25)

    Scenario: a decision bar and its future close produce distinct normalized-return and price-pip values
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      And a timestamp-matched source close at "2016-03-01T14:00:00Z" of 1.09010
      When the horizon is re-derived to a new output path
      Then the re-derived row's normalized_return_pips is 33.1339
      And the re-derived row's price_pips is 36.0
      And the re-derived row records both "normalized_return_pips" and "price_pips" as distinct named columns

    Scenario Outline: the two units diverge more as the archived close moves away from parity (<case>)
      Given a decision at "2016-03-01T10:00:00Z" with archived close <close_t>
      And a timestamp-matched source close at "2016-03-01T14:00:00Z" of <close_tk>
      When the horizon is re-derived to a new output path
      Then the re-derived row's normalized_return_pips is <norm>
      And the re-derived row's price_pips is <price>

      Examples:
        | case                                     | close_t | close_tk | norm    | price |
        | a close near 1.0000 keeps the units close | 1.0050  | 1.0090   | 39.801  | 40.0  |
        | a close near 1.2000 separates them clearly | 1.2000  | 1.2060   | 50.0    | 60.0  |

  Rule: A malformed join key is refused, not silently guessed (CC-25)

    Scenario Outline: <case> is refused as a bad join key
      Given a decision at "<decision_time>" with archived close 1.08650
      When the horizon is re-derived to a new output path and fails
      Then the horizon-unit failure names "<fragment>"

      Examples:
        | case                                               | decision_time         | fragment                                       |
        | a decision timestamp off the H1 minute grid         | 2016-03-01T10:00:30Z  | is not on the H1 minute grid                   |
        | a naive decision timestamp                          | 2016-03-01T10:00:00   | must be timezone-aware UTC                     |

    Scenario: two archive rows sharing the same decision timestamp with different closes is an ambiguous join key
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      And a second decision at "2016-03-01T10:00:00Z" with archived close 1.08700
      When the horizon is re-derived to a new output path and fails
      Then the horizon-unit failure names "duplicate decision timestamp 2016-03-01T10:00:00+00:00 with different archived closes"

  Rule: A missing future horizon row or a missing matched price is recorded explicitly, not dropped or guessed (CC-25)

    Scenario: a decision near the end of the archived window has no close four bars later
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      And no source close is available at "2016-03-01T14:00:00Z" because the source series ends first
      When the horizon is re-derived to a new output path
      Then the re-derived row's normalized_return_pips is null
      And the re-derived row's price_pips is null
      And the re-derived row's unit_status is "missing_future_horizon"

    Scenario: a decision whose exact matched minute has no source price at all
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      And the source price series has a gap at "2016-03-01T14:00:00Z"
      When the horizon is re-derived to a new output path
      Then the re-derived row's normalized_return_pips is null
      And the re-derived row's price_pips is null
      And the re-derived row's unit_status is "missing_price"

    Scenario: a decision whose own archived close has no matched source price is refused, not defaulted to the archive value
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      And the source price series has a gap at "2016-03-01T10:00:00Z"
      When the horizon is re-derived to a new output path
      Then the re-derived row's normalized_return_pips is null
      And the re-derived row's price_pips is null
      And the re-derived row's unit_status is "missing_price"

  Rule: The archive's bytes are checked before and after, and never change (CC-26)

    Scenario: the archive's sha256 hash is identical before and after a successful re-derivation
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      And a timestamp-matched source close at "2016-03-01T14:00:00Z" of 1.09010
      When the horizon is re-derived to a new output path
      Then the archive's sha256 hash after the run equals its sha256 hash before the run

    Scenario: the archive's sha256 hash is still checked and unchanged even when the run fails
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      And no source close is available at "2016-03-01T14:00:00Z" because the source series ends first
      When the horizon is re-derived to a new output path
      Then the archive's sha256 hash after the run equals its sha256 hash before the run

  Rule: The report is written only to a new, caller-specified output path (CC-26)

    Scenario: re-derivation without an explicit output path is refused
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      When the horizon is re-derived with no output path and fails
      Then the horizon-unit failure names "an explicit output path is required"

    Scenario: writing the report to the archive's own path is refused
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      When the horizon is re-derived to "docs/stories/in-progress/21-confluence-chain/evidence/signal-horizon-check.md" and fails
      Then the horizon-unit failure names "must not overwrite the frozen archive"

    Scenario: the report is written to the caller's chosen new path and nowhere else
      Given a decision at "2016-03-01T10:00:00Z" with archived close 1.08650
      And a timestamp-matched source close at "2016-03-01T14:00:00Z" of 1.09010
      When the horizon is re-derived to a new output path
      Then the report exists only at that caller-specified path
