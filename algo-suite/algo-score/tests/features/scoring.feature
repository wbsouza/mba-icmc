Feature: Score financial news sentiment (Loughran-McDonald lexicon scorer)
  scorers/lexicon.py scores article text with the Loughran-McDonald dictionary
  and bucket.py aggregates per-article scores onto the price-aligned minute
  grid. FinBERT (scorers/finbert.py) is a separate, later task — every
  scenario here exercises `--scorer lm` only. Articles are the synthetic
  fixture shape (id, text, publish_ts) described in the task brief; the real
  GDELT article-text source is a parallel, not-yet-landed task.

  Background:
    Given news articles with id, text, and UTC publish_ts

  # scoring-01
  Scenario: Happy path — articles get polarity and confidence
    When I run "algo-score --scorer lm --source gdelt --month 2020-01"
    Then each article has polarity in [-1,1] and confidence in [0,1]
    And minute buckets aggregate net polarity and article count
    And the output records the model_version

  # scoring-02
  Scenario: Empty batch abstains, does not crash
    Given a minute bucket with no articles
    When scoring runs
    Then that bucket has n_articles 0
    And it is treated as ABSTAIN downstream, not an error

  # scoring-03
  Scenario: Deterministic scoring
    Given a fixed seed and a fixed model_version
    When I score the same articles twice with "lm"
    Then the polarity and confidence are identical both times

  # scoring-04
  Scenario: Cache hit avoids re-inference
    Given an article already scored at the current model_version
    When I re-run scoring with "lm"
    Then the cached score is used
    And no new inference is performed for that article

  # scoring-05
  Scenario: Model-version bump invalidates cache
    Given articles scored at model_version v1
    When I score at model_version v2 with "lm"
    Then they are re-scored
    And no partition mixes v1 and v2 scores

  # scoring-06
  Scenario: Non-English text abstains
    Given an article whose text is not English
    When scoring runs
    Then it abstains rather than producing a spurious polarity

  # scoring-07
  Scenario: Multi-currency headline ambiguity is flagged
    Given a headline mentioning two currencies with opposite tone
    When scoring runs
    Then the article is marked ambiguous (low confidence), not forced to a side

  # scoring-08
  Scenario: LM output is stored separately, ready for future FinBERT comparison
    When I run "algo-score --scorer lm --source gdelt --month 2020-01"
    Then a transparent dictionary polarity is produced
    And it is stored under scorer=lm

  # scoring-09
  Scenario: An article's minute has no matching price bar
    Given an article scored with polarity and confidence
    And its minute bucket has no corresponding price bar
    When features are aligned to price minutes
    Then that bucket is excluded from the price-aligned output
    And it is not treated as an error

  # scoring-10
  Scenario Outline: CLI argument validation fails fast with a helpful message
    When I run "algo-score <args>"
    Then the CLI exits non-zero
    And the output contains "<contains>"

    Examples:
      | args                                                                        | contains            |
      | --scorer nope --source gdelt --month 2020-01                               | unknown scorer      |
      | --scorer lm --source gdelt --month 2020-01 --from 2020-01-01 --to 2020-01-05 | --month or          |
      | --scorer lm --source gdelt --month 2020/01                                 | expected YYYY-MM    |
      | --scorer lm --source gdelt --month 2020-13                                 | must be 01-12       |
      | --scorer lm --source gdelt                                                 | provide --month     |
      | --scorer lm --source gdelt --from 2020/01/05 --to 2020-01-07               | expected YYYY-MM-DD |
      | --scorer lm --source gdelt --from 2020-01-07 --to 2020-01-05               | is after            |
