# Progress — Spec 04e (news-context filter F4)

- [x] Confirm Spec 03 sentiment/event Parquet present on NAS data root (blocker check, do first) —
      event half real+built (`algo-score events --kind gdelt`, 44640 rows); sentiment half
      genuinely infeasible to materialize for a full month within this task's scope (~500 GB /
      ~90 hours at the current `gdelt_ngrams` adapter's throughput) — see `docs/technical-debt.md`
      TD-48. F4 built accordingly: event Parquet mandatory/fail-fast, sentiment best-effort/ABSTAIN.
- [x] F4 news-context filter (`chain/filters/f4_news_context.py`)
- [x] Veto-on-active-high-risk-event scenario against real Spec 03 Parquet (real Jan-2020 GDELT
      event_intensity values, e.g. 2020-01-01 = -1.579, the month's real most-conflictual day)
- [x] ABSTAIN scenario (no active high-risk event)
- [x] `make check` green
- [x] Gauntlet (differential mutmut, `uncle-bob-agent-gauntlet`): 144/148 killed (97.3%) after
      adding boundary scenarios (veto/sentiment threshold `<=`/`<`, zero-polarity `>=`/`>`), a
      cross-symbol-isolation scenario, a null-polarity-excluded-from-index scenario, and
      `load_news_context_config()` coverage (closed 18 "no tests" outright). Remaining 4
      survivors are the pre-existing message-text-canary class (TD-34/TD-36/TD-40) — new row
      TD-49, deferred pending the project-wide exact-string-assertion decision.
- [x] `lessons-learned.md` written, story moved to `docs/stories/done/`
