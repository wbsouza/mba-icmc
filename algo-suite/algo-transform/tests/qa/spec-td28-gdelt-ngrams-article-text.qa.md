# QA procedure — TD-28: GDELT NGrams article-text transform

End-to-end verification through the `algo-transform` CLI only (the tool's user
interface — no direct calls into `algo_transform.*` Python modules). Convert
each numbered step below into an executable script per
`swarmforge/roles/QA.prompt`; keep the script in lockstep with this file when
either changes.

Setup common to every section: `ALGO_DATA_ROOT` points at an empty, writable
temp directory for the run; discard it afterward. Where "the mocked GDELT
NGrams datafeed" is referenced, use the same fixture-payload convention as
the GDELT Events QA/acceptance runs (offline, deterministic — no live
network, no live `gdeltnews` reconstruction against real GDELT servers).

## 1. GDELT NGrams decode + transform, happy path

1. Place a mocked raw NGrams minute payload on disk for every UTC minute of
   2020-01-02 14:00-14:59 (`raw/gdelt_ngrams/2020/01/02/202001021400..59.webngrams.json.gz`),
   with minute `14:34`'s payload containing 3 URLs' worth of ngram data (each
   with a known url and enough n-gram fields for the `gdeltnews` package to
   reconstruct text); every other minute of the month is a mocked 0-byte
   MISSING marker.
2. Run: `algo-transform run --source gdelt_ngrams --month 2020-01`.
3. Expect: exit code 0; console output reports `WRITTEN`.
4. Expect: `parquet/news/gdelt/year=2020/month=01/data.parquet` exists under
   the data root and is non-empty.
5. Open the partition (any Parquet reader) and confirm: 3 rows exist, each
   with a non-empty `url`, a `published_at` timestamp, and non-empty
   reconstructed `text`; no row's `url` is null/empty.
6. Re-run the same command. Expect: exit code 0; output reports `SKIPPED`;
   the partition file's mtime is unchanged.
7. Re-run with `--rebuild`. Expect: exit code 0; output reports `WRITTEN`
   again; the partition is rewritten.

## 2. GDELT NGrams incomplete/corrupt month

1. Repeat step 1 above but omit one minute's raw file entirely (no data, no
   MISSING marker).
2. Run: `algo-transform run --source gdelt_ngrams --month 2020-01`.
3. Expect: non-zero exit; output contains "incomplete" (case-insensitive); no
   `parquet/news/gdelt/year=2020/month=01/` directory is created.
4. Restore the missing minute as a corrupt payload (not valid gzip) instead
   of missing.
5. Run the same command again.
6. Expect: non-zero exit; output contains "corrupt" (case-insensitive); no
   partition directory is created; the output names the corrupt minute's raw
   path.

## 3. GDELT NGrams all-MISSING month (durable-missing is complete, not absent)

1. Place a mocked 0-byte MISSING marker for every minute of 2020-02 (the
   provider published nothing that month) — no real data anywhere.
2. Run: `algo-transform run --source gdelt_ngrams --month 2020-02`.
3. Expect: exit code 0; output reports `WRITTEN` (not `INCOMPLETE`).
4. Expect: `parquet/news/gdelt/year=2020/month=02/data.parquet` exists and
   has zero rows (a valid, empty partition — not an error, not a missing
   file).

## 4. GDELT NGrams CLI flag applicability

1. Run: `algo-transform run --source gdelt_ngrams --symbol EURUSD --month
   2020-01`.
2. Expect: non-zero exit; output contains `--symbol` (GDELT NGrams has no
   per-instrument dimension, same as GDELT Events).
3. Run: `algo-transform run --source gdelt_ngrams --month 2020-01` (no
   `--symbol`) against an empty data root.
4. Expect: non-zero exit; output contains "incomplete" — confirms the CLI
   accepted the source without `--symbol` and proceeded to the normal
   completeness check, rather than rejecting the invocation.

## 5. algo-score consumer contract (regression guard)

1. After step 1 of section 1 above, open
   `parquet/news/gdelt/year=2020/month=01/data.parquet` and confirm its
   column names/types match `algo-score/SPEC.md` §2's declared
   `parquet/news/{source}/...` input shape exactly (article text column,
   publish-timestamp column, url column) — this is the contract `algo-score`
   reads from; a mismatch here silently breaks Spec 03's real-sentiment
   path.

## 6. Unsupported source (regression guard)

1. Run: `algo-transform run --source nope --symbol EURUSD --month 2020-01`.
2. Expect: non-zero exit; output names the known sources including
   "dukascopy".
   (Confirms `gdelt_ngrams` joining the known-sources list didn't break this
   existing check.)
