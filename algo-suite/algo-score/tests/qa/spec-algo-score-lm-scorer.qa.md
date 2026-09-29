# QA procedure — algo-score: Loughran-McDonald lexicon scorer

End-to-end verification through the `algo-score` CLI only (the tool's user
interface — no direct calls into `algo_score.*` Python modules). Convert each
numbered step below into an executable script per `swarmforge/roles/QA.prompt`;
keep the script in lockstep with this file when either changes.

Executable script: `run_lm_scorer_qa.py`.

Scope note: this QA procedure covers `scorers/base.py`, `scorers/lexicon.py`,
`bucket.py`, and per-currency attribution — always invoked as `--scorer lm`.
`scorers/finbert.py` and `events/` (GPR/GDELT event features) are separate
lanes, out of scope here. Articles come from a synthetic fixture (`id`,
`text`, `publish_ts`) — the real GDELT article-text source is a parallel,
not-yet-landed task.

Setup common to every section: `ALGO_DATA_ROOT` points at an empty, writable
temp directory holding the synthetic article-text fixture; discard it
afterward.

## 1. Happy path — polarity, confidence, minute bucketing

1. Place 3 mocked articles with known Loughran-McDonald-scorable text (e.g.
   one clearly positive, one clearly negative, one neutral), each with a
   `publish_ts` inside the same UTC minute a price bar exists for.
2. Run: `algo-score --scorer lm --source gdelt --month 2020-01`.
3. Expect: exit code 0.
4. Expect: `parquet/sentiment/lm/...` exists; each article's row has
   `polarity` in `[-1, 1]` and `confidence` in `[0, 1]`.
5. Expect: the minute bucket aggregates `n_articles` and net polarity across
   the 3 articles.
6. Expect: `model_version` is recorded and non-empty.

## 2. Empty batch abstains

1. Mock a minute with zero articles alongside a minute that has articles.
2. Run the same command.
3. Expect: exit code 0; the empty minute's row has `n_articles = 0` and is not
   reported as an error.

## 3. Deterministic scoring

1. Run the command from §1 twice against the same fixture and `model_version`.
2. Expect: byte-identical `polarity`/`confidence` values both times.

## 4. Cache hit avoids re-inference

1. Run the command from §1 once (cold cache).
2. Re-run it immediately, with the mocked scorer instrumented to fail the
   test if invoked again for an already-scored `(article_id, model,
   model_version)`.
3. Expect: exit code 0 both times; the second run's report states 0 new
   scores computed (all cache hits).

## 5. Model-version bump invalidates cache

1. Run the command from §1 at a fixed `model_version` (e.g. `v1`).
2. Re-run with a different `model_version` (e.g. `v2`, via `--config` or the
   tool's version-selection mechanism).
3. Expect: exit code 0; the v2 output partition holds freshly computed scores
   (not reused from v1), and no partition mixes `v1`/`v2` rows.

## 6. Non-English text abstains

1. Add one article whose text is not English to the fixture from §1.
2. Run the command.
3. Expect: exit code 0; that article's row is ABSTAIN (no polarity value, or
   a documented abstain marker) rather than a fabricated score.

## 7. Multi-currency ambiguous headline

1. Add an article whose text mentions two currencies with opposite tone
   (e.g. positive-EUR, negative-USD in the same headline).
2. Run the command, then run attribution.
3. Expect: the article contributes to both currencies with reduced
   confidence — not forced onto a single side.

## 8. Per-currency attribution routing

1. Mock three articles: one about "the ECB raising rates", one about "an
   FOMC decision", one about "BOJ intervention".
2. Run attribution over the scored output.
3. Expect: the ECB article attributes to `EUR`, the FOMC article to `USD`,
   the BOJ article to `JPY`.

## 9. USD-macro news feeds both pairs

1. Using the FOMC article from §8, form pair features for EURUSD and USDJPY.
2. Expect: both pairs' derived sentiment consumes the USD stream from that
   article.

## 10. Article with no attributable currency is dropped, not an error

1. Add an article concerning none of EUR/USD/JPY (e.g. a Brazil-only story).
2. Run attribution.
3. Expect: exit code 0; that article is excluded from
   `parquet/sentiment/lm/...`'s per-currency output and counted in the run
   report, not raised as an error.

## 11. A scored minute with no matching price bar is excluded, not an error

1. Mock an article whose `publish_ts` falls in a minute for which no price
   bar exists in the data root (e.g. outside market hours).
2. Run the command.
3. Expect: exit code 0; that minute's feature row is absent from the
   price-aligned output, and this is not reported as a failure.

## 12. LM output namespaced for future FinBERT comparison

1. Run the command from §1.
2. Expect: the output partition path/column identifies `scorer=lm`
   (`parquet/sentiment/lm/...`), distinct from any future `finbert` partition.
