Feature: Training entry points reject incompatible strategy feature families before data IO
  The baseline trainer produces trend, indicator and pattern models without news.
  The hybrid trainer additionally produces a news model and requires the news filter.

  Scenario Outline: An incompatible external strategy is rejected before market reads
    Given the <trainer> training CLI selects an external <shape> strategy
    When the selected training CLI is invoked
    Then training rejects the selection mentioning "<reason>" with remediation
    And neither price nor event data was read and no model was written
    Examples:
      | trainer  | shape                    | reason                |
      | baseline | hybrid                   | families              |
      | hybrid   | baseline                 | families              |
      | baseline | baseline-subset          | families              |
      | hybrid   | hybrid-subset            | families              |
      | baseline | baseline-news-gate       | f4_news_context       |
      | hybrid   | hybrid-without-news-gate | f4_news_context       |
      | baseline | no-f7                    | f7_meta_learner        |
      | hybrid   | no-f7                    | f7_meta_learner        |

  Scenario Outline: Compatible external selections reach market data loading
    Given the <trainer> training CLI selects an external <shape> strategy
    When the selected training CLI is invoked
    Then the selection reaches the price data boundary
    Examples:
      | trainer  | shape             |
      | baseline | baseline          |
      | baseline | baseline-reversed |
      | hybrid   | hybrid            |
      | hybrid   | hybrid-reversed   |

  Scenario: All current Heikin-Ashi H4 candidates remain compatible with their matching trainer
    When each current Heikin-Ashi H4 candidate is passed to its matching training CLI
    Then all eight candidates reach the price data boundary
