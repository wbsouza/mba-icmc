Feature: Training entry points reject incompatible strategy feature families before data IO
  The baseline trainer produces trend, indicator and pattern models without news.
  The hybrid trainer trains exactly the families the strategy declares — any non-empty
  subset of the known families that includes news (all four for `hybrid`, `[news]`
  alone for `news-only`) — and requires the news filter. Every candidate below is an
  external strategy named "candidate" extending a bundled base (`none` = its own
  one-filter chain without F7, F1 as its terminal_filter), with the families written
  into its config.yaml.

  Scenario Outline: An incompatible external strategy is rejected before market reads
    Given the <trainer> training CLI selects an external strategy extending <extends> with families <families>
    When the selected training CLI is invoked
    Then training rejects the selection mentioning "<reason>" with remediation
    And neither price nor event data was read and no model was written
    Examples:
      | trainer  | extends  | families                          | reason                                                                                                                  |
      | baseline | hybrid   | [trend, indicator, pattern, news] | baseline trainer requires families ['indicator', 'pattern', 'trend']                                                    |
      | hybrid   | baseline | [trend, indicator, pattern]       | hybrid trainer requires the news family, but strategy 'candidate' declares meta_learner.families ['trend', 'indicator', 'pattern'] |
      | baseline | baseline | [trend, indicator]                | baseline trainer requires families ['indicator', 'pattern', 'trend']                                                    |
      | hybrid   | hybrid   | [trend]                           | hybrid trainer requires the news family, but strategy 'candidate' declares meta_learner.families ['trend']              |
      | hybrid   | hybrid   | [news, volume]                    | strategy 'candidate': unknown meta_learner.families ['volume'] — known families: ['trend', 'indicator', 'pattern', 'news'] |
      | baseline | hybrid   | [trend, indicator, pattern]       | f4_news_context                                                                                                         |
      | hybrid   | baseline | [trend, indicator, pattern, news] | f4_news_context                                                                                                         |
      | baseline | none     | [trend]                           | f7_meta_learner                                                                                                         |
      | hybrid   | none     | [news]                            | f7_meta_learner                                                                                                         |

  Scenario Outline: Compatible external selections reach market data loading
    Given the <trainer> training CLI selects an external strategy extending <extends> with families <families>
    When the selected training CLI is invoked
    Then the selection reaches the price data boundary
    Examples:
      | trainer  | extends  | families                          |
      | baseline | baseline | [trend, indicator, pattern]       |
      | baseline | baseline | [pattern, indicator, trend]       |
      | hybrid   | hybrid   | [trend, indicator, pattern, news] |
      | hybrid   | hybrid   | [news, pattern, indicator, trend] |
      | hybrid   | hybrid   | [trend, indicator, news]          |
      | hybrid   | hybrid   | [news]                            |
      | hybrid   | hybrid   | [news, trend]                     |

  Scenario Outline: The hybrid trainer fits and records exactly the declared families, in order
    Given the hybrid training CLI selects an external strategy extending hybrid with families <families>
    And the market data and model persistence behind the training CLI are stubbed
    When the selected training CLI is invoked
    Then the meta-learner is trained on the families <families>
    And the persisted model provenance records the families <families>
    Examples:
      | families                          |
      | [news]                            |
      | [news, trend]                     |
      | [trend, indicator, pattern, news] |

  Scenario: All current Heikin-Ashi H4 candidates remain compatible with their matching trainer
    When each current Heikin-Ashi H4 candidate is passed to its matching training CLI
    Then all eight candidates reach the price data boundary
