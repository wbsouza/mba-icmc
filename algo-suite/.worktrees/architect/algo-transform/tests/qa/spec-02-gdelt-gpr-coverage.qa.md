# QA procedure — Spec 02: GDELT/GPR transform + coverage matrix

End-to-end verification through the `algo-transform` CLI only (the tool's user
interface — no direct calls into `algo_transform.*` Python modules). Convert
each numbered step below into an executable script per
`swarmforge/roles/QA.prompt`; keep the script in lockstep with this file when
either changes.

Setup common to every section: `ALGO_DATA_ROOT` points at an empty, writable
temp directory for the run; discard it afterward. Where "the mocked GDELT/GPR
datafeed" is referenced, use the same fixture-payload convention as the
Dukascopy QA/acceptance runs (offline, deterministic — no live network).

## 1. GDELT decode + transform, happy path

1. Place a mocked raw GDELT Events zip on disk for every 15-minute slot of
   2020-01 (`raw/gdelt/2020/01/...`), each slot's zip containing one
   tab-delimited Events CSV row with a known `GLOBALEVENTID`, `EventCode`,
   `GoldsteinScale`, `AvgTone` and `SOURCEURL`.
2. Run: `algo-transform run --source gdelt --month 2020-01`.
3. Expect: exit code 0; console output reports `WRITTEN`.
4. Expect: `parquet/events/gdelt/year=2020/month=01/data.parquet` exists
   under the data root and is non-empty.
5. Open the partition (any Parquet reader) and confirm: no column holds
   article text; `SOURCEURL`, `EventCode`, `GoldsteinScale`, `AvgTone` are
   present and match the mocked values.
6. Re-run the same command. Expect: exit code 0; output reports `SKIPPED`;
   the partition file's mtime is unchanged.
7. Re-run with `--rebuild`. Expect: exit code 0; output reports `WRITTEN`
   again; the partition is rewritten.

## 2. GDELT incomplete/corrupt month

1. Repeat step 1 above but omit one slot's raw file entirely.
2. Run: `algo-transform run --source gdelt --month 2020-01`.
3. Expect: non-zero exit; output contains "incomplete" (case-insensitive);
   no `parquet/events/gdelt/year=2020/month=01/` directory is created.
4. Restore the missing slot as a corrupt payload (not a valid zip) instead
   of missing.
5. Run the same command again.
6. Expect: non-zero exit; output contains "corrupt" (case-insensitive); no
   partition directory is created; the output names the corrupt slot's path.

## 3. GDELT CLI flag applicability

1. Run: `algo-transform run --source gdelt --symbol EURUSD --month 2020-01`.
2. Expect: non-zero exit; output contains `--symbol` (GDELT has no
   per-instrument dimension).
3. Run: `algo-transform run --source gdelt --month 2020-01` (no `--symbol`)
   against an empty data root.
4. Expect: non-zero exit; output contains "incomplete" — confirms the CLI
   accepted the source without `--symbol` and proceeded to the normal
   completeness check, rather than rejecting the invocation.

## 4. GPR decode + transform, happy path

1. Place a mocked raw GPR file at `raw/gpr/data_gpr_export.xls` with at
   least three period rows spanning 2015-02 through 2015-04.
2. Run: `algo-transform run --source gpr`.
3. Expect: exit code 0; output reports `WRITTEN`.
4. Expect: `parquet/events/gpr/data.parquet` (whole-window, no
   `year=/month=` partitioning) exists and holds one row per period in the
   mocked file, with no forward-filled or interpolated periods.
5. Re-run the same command. Expect: exit 0; output reports `SKIPPED`.
6. Remove the raw file and re-run. Expect: non-zero exit; output states the
   input is missing; no partition is written.

## 5. GPR CLI flag applicability

1. Run: `algo-transform run --source gpr --symbol EURUSD`.
   Expect: non-zero exit; output contains `--symbol`.
2. Run: `algo-transform run --source gpr --month 2020-01`.
   Expect: non-zero exit; output contains `--month`.
3. Run: `algo-transform run --source gpr --from 2020-01 --to 2020-02`.
   Expect: non-zero exit; output contains `--from`.

## 6. Coverage matrix + training-window figure

1. Populate the data root with mocked GDELT event partitions (or their raw
   inputs) such that the monthly coverage ratio for 2015-02 through 2015-07
   matches: 0.9, 0.85, 0.5, 0.95, 0.9, 0.92 (a gap at 2015-04 below 80%).
2. Run: `algo-transform coverage`.
3. Expect: exit code 0; console output states the selected window as
   "2015-05 to 2015-07" (the longer of the two contiguous >=80% spans).
4. Expect: `parquet/_meta/coverage.parquet` exists and has one row per
   `(month, source)` with `units_expected`, `units_present`,
   `coverage_ratio`, `resolution`, `backtestable` columns populated.
5. Expect: a vector PDF coverage-matrix figure is written under the data
   root (path reported by the command's output).
6. Re-run `algo-transform coverage` and confirm the reported window and the
   figure are byte-for-byte reproducible (same command, same input ⇒ same
   output — no timestamp or random element in the artifact).

## 7. Unsupported source (regression guard)

1. Run: `algo-transform run --source nope --symbol EURUSD --month 2020-01`.
2. Expect: non-zero exit; output names the known sources including
   "dukascopy".
   (This replaces a prior check that used `gdelt` as the unsupported
   example — `gdelt` became a real, supported source under Spec 02, so that
   check would now fail for the wrong reason if not updated here too.)
