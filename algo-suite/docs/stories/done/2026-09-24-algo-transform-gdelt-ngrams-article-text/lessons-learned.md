# Lessons learned — algo-transform: GDELT NGrams article-text reconstruction (TD-28)

This story closes the text-sentiment gap Spec 02 deferred: `algo-transform`
now reconstructs article text from `algo-download`'s raw
`raw/gdelt_ngrams/...` payloads (the earlier, separate
[`2026-09-23-gdelt-ngrams-adapter`](../2026-09-23-gdelt-ngrams-adapter/lessons-learned.md)
story) and writes it to `parquet/news/gdelt/...`, the input `algo-score`'s
FinBERT/LM sentiment scorer is already contracted to read.

**Verify a third-party library's real behavior before writing the contract
around it, not the other way around.** The draft spec assumed a malformed
NGrams JSON line or one missing a required field would raise a `DecodeError`,
same as a non-gzip payload. Running the real `gdeltnews` package showed it
silently skips those lines instead (only a non-gzip payload fails) — the
coder caught this empirically and corrected both the decoder and the Gherkin
scenario (pruning scenario 03 to a new scenario 04) rather than building a
decoder that matched an assumption the library doesn't actually hold.

**A downstream contract that's already fixed constrains the upstream
producer, not the reverse.** `algo_score.scorers.models.NewsArticle`
(`id`/`text`/`publish_ts`) was already published before this story started;
the new `GdeltNewsArticle` model in `algo-transform` was written to match it
field-for-field rather than the other way around. QA's end-to-end driver
(`tests/qa/spec_td28_gdelt_ngrams_article_text_qa.py`) asserts this contract
directly against the written Parquet's column names, not just against the
in-process dataclass, so a future drift between the two models would fail
loudly at the CLI boundary QA actually exercises.

**A merge conflict in shared tooling can hide unrelated debt.** Merging
hardener's `f8e24b28a2` (a `tools/mutation_harness.py` memory-cap fix for the
earlier OOM/tmux-crash incident) surfaced 2 new `mypy --strict` errors in
that file, on top of 35 pre-existing ones unrelated to this story
(confirmed by checking mypy against the file's pre-fix revision). QA fixed
the 2 regressions the conflict resolution was responsible for and logged the
35 pre-existing ones as new debt (`technical-debt.md` TD-38) rather than
either ignoring the regression or scope-creeping into annotating an entire
unrelated dev-tool script during a verification pass.

**A QA procedure doc with no driver script yet is still work QA owns.** The
specifier's `spec-td28-gdelt-ngrams-article-text.qa.md` had no corresponding
executable script when this task reached QA (unlike the sibling Spec 02 QA
doc, which already had one) — converting it into
`spec_td28_gdelt_ngrams_article_text_qa.py` was this pass's own deliverable,
not a gap to report and defer.
