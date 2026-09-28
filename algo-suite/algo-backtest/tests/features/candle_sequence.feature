Feature: Doji-to-engulfing next-bar confirmation
  Story 22, task T5 (CND-05, CND-07, CND-08). A pure state machine over closed bars:
  IDLE -> CANDIDATE (a doji closed) -> CONFIRMED or EXPIRED at the NEXT closed bar.
  Confirmation belongs to the later bar and is timestamped at that bar's close_time.
  A bar may expire an old candidate and open a new one, but never confirms itself.
  Sequence evidence is separately typed from geometry hits and from context.

  Definitions (T1 ledger; sources: webinar 24:13-25:24 and 27:51-28:15 "left/right
  combo", the engulfing concerns the body "not necessarily the shadows"; book 37/43
  allows one equal edge; webinar 15:08 "doji at the bottom needs bullish confirmation
  the next day"):
    - doji: body <= 0.10 * range (catalog rule `doji`; the catalog decides).
    - qualifying bullish engulfing of the candidate: the confirming bar is bullish
      (close > open) and its body covers the doji body inclusively:
      open <= min(open_d, close_d) and close >= max(open_d, close_d).
    - qualifying bearish engulfing: bearish (close < open), open >= max(open_d,
      close_d) and close <= min(open_d, close_d).
    - The direction of a confirmed sequence is the confirming bar's colour;
      ids: doji_engulfing_bullish (+1) and doji_engulfing_bearish (-1).
    - Expected next bar: candidate close_time + timeframe under the "continuous"
      calendar policy. Under a policy with a scheduled closure [from, to), when the
      continuous expectation falls inside the closure the expected next close is the
      earliest timeframe-aligned close_time strictly after `to`. A next bar that
      closes later than expected expires the candidate with reason
      "missing_expected_bar" and can never confirm it, even if its body engulfs the
      doji body. The policy is a T5 input; the manifest owner (T7) records it.
    - Sequence evidence per bar: state (IDLE | CANDIDATE | CONFIRMED | EXPIRED),
      candidate_close_time, confirmed_direction (+1 | -1 | None),
      confirmation_time (close_time of the confirming bar or None), reason
      ("confirmed", "not_engulfing", "missing_expected_bar", or None). The reason
      explains how the PREVIOUS candidate ended on this bar; a bar that ends one
      candidate and is itself a doji reports state CANDIDATE with that reason.
    - Prices are integers; bars are 60-minute UTC bars closing on the hour; the
      first bar closes at 2024-01-01T01:00:00+00:00 unless stated.
    - D denotes the doji (1000, 1050, 950, 1000); B denotes the bullish engulfing
      (990, 1060, 985, 1030); S denotes the bearish engulfing (1010, 1015, 940, 970);
      N denotes a non-engulfing bullish bar (1005, 1030, 1000, 1025); F denotes a
      plain context bar (1000, 1030, 990, 1020) that is neither a doji nor engulfing.

  Rule: Confirmation is dated at the confirming bar's close

    Scenario: A doji followed by a bullish engulfing confirms bullish at the second close
      Given the closed bars F, D, B
      When the sequence evaluator processes every bar
      Then the sequence states per bar are "IDLE, CANDIDATE, CONFIRMED"
      And the confirmed direction at bar 3 is 1 with id "doji_engulfing_bullish"
      And the confirmation_time at bar 3 is "2024-01-01T03:00:00+00:00"
      And the candidate_close_time at bar 3 is "2024-01-01T02:00:00+00:00"

    Scenario: A doji followed by a bearish engulfing confirms bearish at the second close
      Given the closed bars F, D, S
      When the sequence evaluator processes every bar
      Then the sequence states per bar are "IDLE, CANDIDATE, CONFIRMED"
      And the confirmed direction at bar 3 is -1 with id "doji_engulfing_bearish"
      And the confirmation_time at bar 3 is "2024-01-01T03:00:00+00:00"

    Scenario: The doji bar itself never carries a confirmation
      Given the closed bars D
      When the sequence evaluator processes every bar
      Then the sequence states per bar are "CANDIDATE"
      And the confirmed direction at bar 1 is None
      And the confirmation_time at bar 1 is None

  Rule: A non-qualifying next bar expires the candidate

    Scenario: A non-engulfing bullish bar expires the candidate without confirmation
      Given the closed bars F, D, N
      When the sequence evaluator processes every bar
      Then the sequence states per bar are "IDLE, CANDIDATE, EXPIRED"
      And the reason at bar 3 is "not_engulfing"
      And the confirmed direction at bar 3 is None

    Scenario: An engulfing two bars after the doji confirms nothing
      Given the closed bars F, D, N, B
      When the sequence evaluator processes every bar
      Then the sequence states per bar are "IDLE, CANDIDATE, EXPIRED, IDLE"
      And the confirmed direction at bar 4 is None

    Scenario: A second doji expires the first candidate and becomes the new candidate
      Given the closed bars F, D, D, B
      When the sequence evaluator processes every bar
      Then the sequence states per bar are "IDLE, CANDIDATE, CANDIDATE, CONFIRMED"
      And the reason at bar 3 is "not_engulfing"
      And the candidate_close_time at bar 3 is "2024-01-01T03:00:00+00:00"
      And the confirmation_time at bar 4 is "2024-01-01T04:00:00+00:00"
      And the candidate_close_time at bar 4 is "2024-01-01T03:00:00+00:00"

    Scenario Outline: Engulfing edges are inclusive, colour is mandatory (<case>)
      Given the closed bars F, D, then (<open>, <high>, <low>, <close>)
      When the sequence evaluator processes every bar
      Then the sequence state at bar 3 is "<state>"
      And the confirmed direction at bar 3 is <direction>

      Examples:
        | case                                  | open | high | low | close | state     | direction |
        | open equal to doji body, bullish      | 1000 | 1040 | 995 | 1030  | CONFIRMED | 1         |
        | open one above the doji body          | 1001 | 1040 | 995 | 1030  | EXPIRED   | None      |
        | close equal to doji body, bearish     | 1010 | 1015 | 990 | 1000  | CONFIRMED | -1        |
        | bearish close one above the doji body | 1010 | 1015 | 990 | 1001  | EXPIRED   | None      |
        | shadows cover but body does not       | 1005 | 1100 | 900 | 1030  | EXPIRED   | None      |
        | another doji is a replacement         | 1000 | 1050 | 950 | 1000  | CANDIDATE | None      |

  Rule: Missing expected bars expire the candidate under the calendar policy

    Scenario: A skipped hour expires the candidate even when the late bar engulfs
      Given the closed bars F, D closing hourly from "2024-01-01T01:00:00+00:00"
      And a bullish engulfing bar B closing at "2024-01-01T04:00:00+00:00"
      When the sequence evaluator processes every bar under the "continuous" calendar policy
      Then the sequence states per bar are "IDLE, CANDIDATE, EXPIRED"
      And the reason at bar 3 is "missing_expected_bar"
      And the confirmed direction at bar 3 is None

    Scenario: A skipped hour before a doji still opens a new candidate
      Given the closed bars F, D closing hourly from "2024-01-01T01:00:00+00:00"
      And a doji bar D closing at "2024-01-01T04:00:00+00:00"
      And a bullish engulfing bar B closing at "2024-01-01T05:00:00+00:00"
      When the sequence evaluator processes every bar under the "continuous" calendar policy
      Then the sequence states per bar are "IDLE, CANDIDATE, CANDIDATE, CONFIRMED"
      And the reason at bar 3 is "missing_expected_bar"
      And the confirmation_time at bar 4 is "2024-01-01T05:00:00+00:00"

    Scenario: A scheduled closure is not a missing bar
      Given a calendar policy with a scheduled closure from "2024-01-05T22:00:00+00:00" to "2024-01-07T22:00:00+00:00"
      And the closed bars F closing at "2024-01-05T21:00:00+00:00" and D closing at "2024-01-05T22:00:00+00:00"
      And a bullish engulfing bar B closing at "2024-01-07T23:00:00+00:00"
      When the sequence evaluator processes every bar under that calendar policy
      Then the sequence states per bar are "IDLE, CANDIDATE, CONFIRMED"
      And the confirmation_time at bar 3 is "2024-01-07T23:00:00+00:00"

    Scenario: A bar after the scheduled closure that is later than the first expected close expires the candidate
      Given a calendar policy with a scheduled closure from "2024-01-05T22:00:00+00:00" to "2024-01-07T22:00:00+00:00"
      And the closed bars F closing at "2024-01-05T21:00:00+00:00" and D closing at "2024-01-05T22:00:00+00:00"
      And a bullish engulfing bar B closing at "2024-01-08T00:00:00+00:00"
      When the sequence evaluator processes every bar under that calendar policy
      Then the sequence states per bar are "IDLE, CANDIDATE, EXPIRED"
      And the reason at bar 3 is "missing_expected_bar"

    Scenario: A next expected close exactly at the closure end is not treated as inside the closure
      Given a calendar policy with a scheduled closure from "2024-01-05T22:00:00+00:00" to "2024-01-07T22:00:00+00:00"
      And the closed bars F closing at "2024-01-07T20:00:00+00:00" and D closing at "2024-01-07T21:00:00+00:00"
      And a bullish engulfing bar B closing at "2024-01-07T22:00:00+00:00"
      When the sequence evaluator processes every bar under that calendar policy
      Then the sequence states per bar are "IDLE, CANDIDATE, CONFIRMED"
      And the confirmation_time at bar 3 is "2024-01-07T22:00:00+00:00"

  Rule: A scheduled closure's bounds are validated eagerly

    Scenario: A closure with equal start and end is rejected
      When a scheduled closure from "2024-01-05T22:00:00+00:00" to "2024-01-05T22:00:00+00:00" is constructed
      Then constructing the scheduled closure raises mentioning "strictly after"

  Rule: The evaluator is causal and fails fast

    Scenario: Suffix invariance: later bars never change earlier sequence evidence
      Given the closed bars F, D, B, F, D
      When the sequence evaluator processes the bars once with the suffix N and once with the suffix S
      Then the sequence evidence over the first 5 bars is identical under both suffixes
      And the sequence state at bar 6 is "EXPIRED" under the suffix N and "CONFIRMED" under the suffix S

    Scenario: An invalid bar is rejected without consuming the candidate
      Given the closed bars F, D
      When a bar with OHLC [9, 8, 10, 9] is offered to the sequence evaluator
      Then the sequence evaluator rejects it mentioning "ordering" and a remedy
      And the sequence state is still "CANDIDATE" with candidate_close_time "2024-01-01T02:00:00+00:00"
      And the next valid bar B confirms bullish at "2024-01-01T03:00:00+00:00"

    Scenario: A duplicate close_time is rejected without consuming the candidate
      Given the closed bars F, D
      When a bullish engulfing bar B closing at "2024-01-01T02:00:00+00:00" is offered to the sequence evaluator
      Then the sequence evaluator rejects it mentioning "duplicate" and a remedy
      And the sequence state is still "CANDIDATE" with candidate_close_time "2024-01-01T02:00:00+00:00"

    Scenario: Sequence evidence is separate from geometry and context
      Given the closed bars F, D, B
      When the sequence evaluator processes every bar
      Then the sequence evidence at bar 3 exposes only state, candidate_close_time, confirmed_direction, confirmation_time and reason
      And the sequence evidence carries no pattern hits and no context values
