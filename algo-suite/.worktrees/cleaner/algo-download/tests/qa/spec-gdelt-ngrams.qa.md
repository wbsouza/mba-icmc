# QA procedure — GDELT article-text adapter (Web News NGrams 3.0)

End-to-end verification through the `algo-download` CLI only (the tool's user
interface — no direct calls into `algo_download.*` Python modules). Convert
each numbered step below into an executable script per
`swarmforge/roles/QA.prompt`; keep the script in lockstep with this file when
either changes.

Executable script: `run_gdelt_ngrams_qa.py`.

Setup common to every section: `ALGO_DATA_ROOT` points at an empty, writable
temp directory for the run; discard it afterward. Where "the mocked GDELT
NGrams datafeed" is referenced, use the same fixture-payload convention as the
Dukascopy/GDELT-events QA runs (offline, deterministic — no live network).

## 1. Dry run plans without I/O

1. Run: `algo-download run --source gdelt_ngrams --month 2020-01 --dry-run`.
2. Expect: exit code 0.
3. Expect: the output lists 44640 minute units (31 days × 24 × 60) and makes
   no HTTP request.
4. Expect: no file is written under the data root.

## 2. Happy path writes raw payloads at the canonical path

1. With the mocked datafeed returning gzip bytes for every minute of
   2020-01-02: run `algo-download run --source gdelt_ngrams --month 2020-01`.
2. Expect: exit code 0; output reports `written`.
3. Expect: a raw payload exists at
   `raw/gdelt_ngrams/2020/01/02/20200102143400.webngrams.json.gz`.
4. Expect: no file is written outside `raw/`.

## 3. Resume is a filesystem no-op

1. Re-run the same command from §2 with no changes to the mocked datafeed.
2. Expect: exit code 0; output reports every unit `skipped`; no HTTP request
   is made (assert on the mock's call count, exposed by the QA fixture same
   as the Dukascopy/GDELT resume checks).

## 4. Provider no-data is MISSING and durable, not FAILED

1. Configure the mocked datafeed to return an empty body for minute
   2020-01-02 14:34, gzip bytes for every other minute in 2020-01.
2. Run: `algo-download run --source gdelt_ngrams --month 2020-01`.
3. Expect: exit code 0.
4. Expect: `raw/gdelt_ngrams/2020/01/02/20200102143400.webngrams.json.gz`
   exists as a 0-byte file (the durable MISSING marker).
5. Re-run the same command. Expect: exit 0; that minute now reports `skipped`
   (the empty marker satisfies resume).

## 5. A failed fetch writes nothing and flips the exit code

1. Configure the mocked datafeed to error (beyond the adapter's retry limit)
   for minute 2020-01-02 14:34, gzip bytes for every other minute in 2020-01.
2. Run: `algo-download run --source gdelt_ngrams --month 2020-01`.
3. Expect: non-zero exit.
4. Expect: no file exists at
   `raw/gdelt_ngrams/2020/01/02/20200102143400.webngrams.json.gz`.
5. Expect: every other minute in the month is still written (one bad minute
   does not abort the run).

## 6. CLI flag applicability (global source, no symbol)

1. Run: `algo-download run --source gdelt_ngrams --symbol EURUSD --month 2020-01`.
2. Expect: non-zero exit; output contains `--symbol`.
3. Run: `algo-download run --source gdelt_ngrams --month 2020-01 --dry-run`
   (no `--symbol`).
4. Expect: exit code 0 (confirms the CLI accepts the source without
   `--symbol` and proceeds to plan the month).
5. Run: `algo-download run --source gdelt_ngrams` (no month, no range).
6. Expect: non-zero exit (a date span is required for this source, same as
   `gdelt`).

## 7. Unsupported source (regression guard)

1. Run: `algo-download run --source nope --month 2020-01`.
2. Expect: non-zero exit; output names the known sources including
   `dukascopy`, `gdelt`, `gpr`, and `gdelt_ngrams`.

## 8. Real-feed smoke (manual, opt-in — not part of the automated QA run)

Documented for completeness; QA does **not** execute this against the live
network as part of the standard suite (see `SPEC.md` §7a.3 on publish lag —
only fixed, already-settled timestamps are safe to probe):

1. `uv run pytest -m network -k gdelt_ngrams` reproduces the real-feed
   assertions: a fixed 2020-01-01 00:01 minute is `WRITTEN` with a
   gzip-JSON-lines payload; a fixed 2019-12-31 23:59 minute (before dataset
   coverage) is `MISSING`.
