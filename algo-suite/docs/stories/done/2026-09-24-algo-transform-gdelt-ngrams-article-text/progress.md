# Progress — TD-28 (algo-transform: GDELT NGrams article text)

- [x] Add `gdeltnews` dependency to `algo-transform/pyproject.toml`
- [x] `decoders/gdelt_ngrams.py` — reconstruct article rows from one raw NGrams
      minute payload. Verified against the real `gdeltnews` library (not
      assumed): synthetic multi-fragment payloads actually reconstruct via
      n-gram overlap; the reconstructed `Date` column truncates to hour
      granularity (`2020010214`, not the full minute/second input); only a
      non-gzip payload raises — a malformed JSON line or a line missing a
      required field is silently skipped by the library itself, not an error.
- [x] Orchestrator wiring — `--source gdelt_ngrams`, completeness-gated write
      to `parquet/news/gdelt/...` (`readers/gdelt_ngrams.py` +
      `orchestrator.transform_gdelt_ngrams_month`, `cli.py`).
- [x] `tests/features/gdelt_ngrams_decode.feature` + steps green (5 scenarios;
      pruned scenario 03's 2 of 3 "corrupt payload" examples to a new scenario
      04 "silently skipped, not an error" — matches verified real behavior,
      not the draft's assumption that all three raise `DecodeError`).
- [x] `tests/features/gdelt_ngrams_transform.feature` + steps green (5 scenarios).
- [x] `cli.feature` extended for `--source gdelt_ngrams` flag contract (already
      landed by specifier; ran green against the new CLI wiring unchanged).
- [x] `algo-transform/SPEC.md` §2/§5 updated to reflect the landed dataset;
      added §9b acceptance criteria.
- [x] `00-PLAN.md` §1 and `technical-debt.md` TD-28 updated (→ resolved).
- [x] `make check` green (ruff, mypy, pytest: 80/80). No `make audit`/
      `pip-audit` tooling exists in this repo (pre-existing gap, same as
      Spec 04a); `gdeltnews` is the one new dependency added.
