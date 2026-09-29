# QA procedure — algo-score: event features (GPR + GDELT)

End-to-end verification through the `algo-score` CLI only (the tool's user
interface — no direct calls into `algo_score.*` Python modules). Convert each
numbered step below into an executable script per `swarmforge/roles/QA.prompt`;
keep the script in lockstep with this file when either changes.

Executable script: `run_event_features_qa.py`.

Scope note: this QA procedure covers only the event-feature side
(`events/gpr.py`, `events/gdelt.py`, and the `algo-score events --kind
<gdelt|gpr>` CLI dispatch that reads/writes them) per the task boundary — it
does **not** cover `--scorer finbert|lm` (sentiment) or `models-fetch`, which
are separate parallel lanes.

Setup common to every section: `ALGO_DATA_ROOT` points at an empty, writable
temp directory holding a mocked canonical event Parquet fixture (`GdeltEvent`/
`GprEvent` rows per [`algo-transform/src/algo_transform/events.py`](../../../../../algo-transform/src/algo_transform/events.py)); discard it
afterward.

## 1. GPR event feature, happy path

1. Place a mocked `parquet/events/gpr/data.parquet` with `GprEvent` rows for
   three consecutive days (e.g. 2020-01-05, 2020-01-06, 2020-01-07), each a
   distinct known `gpr` value.
2. Run: `algo-score events --kind gpr --from 2020-01-05 --to 2020-01-07`.
3. Expect: exit code 0.
4. Expect: `parquet/events/_features/gpr/...` (or the path SPEC.md §6.2
   resolves to) exists and holds one row per minute in the window.
5. Expect: every minute of 2020-01-05 carries that day's `gpr` value; every
   minute of 2020-01-06 carries 2020-01-06's value; same for 2020-01-07 (no
   interpolation between days).
6. Expect: the column is named `gpr`, never `sentiment` or `polarity`.

## 2. GPR event feature, a missing day carries forward

1. Repeat step 1 but omit the 2020-01-06 row entirely.
2. Run the same command.
3. Expect: exit code 0; every minute of 2020-01-06 carries 2020-01-05's `gpr`
   value (the last known prior value), not an interpolated midpoint and not
   zero/null.

## 3. GPR event feature, no fabricated value before the first observation

1. Mock only 2020-01-06 and 2020-01-07 (no earlier `GprEvent` rows at all).
2. Run: `algo-score events --kind gpr --from 2020-01-05 --to 2020-01-07`.
3. Expect: exit code 0; every minute of 2020-01-05 has no `gpr` value (null/
   absent, not fabricated as `0.0`); minutes from 2020-01-06 onward carry the
   real values.

## 4. GDELT event feature, happy path (golden-value aggregation)

1. Place a mocked `parquet/events/gdelt/data.parquet` with three `GdeltEvent`
   rows sharing `event_date` 2020-01-05, with `goldstein_scale` -4.0, 2.0, and
   6.0 respectively (and any `avg_tone` values — they must not affect the
   result), plus a second day 2020-01-06 with its own rows.
2. Run: `algo-score events --kind gdelt --from 2020-01-05 --to 2020-01-06`.
3. Expect: exit code 0.
4. Expect: every minute of 2020-01-05 carries `event_intensity` equal to
   `1.3333333333333333` (the unweighted mean of -4.0, 2.0, 6.0 — per
   [`algo-score/SPEC.md`](../../../../../algo-score/SPEC.md) §6.2 and its 2026-09-22 decision: mean of
   `goldstein_scale` only, `avg_tone` not folded in).
5. Expect: the column is named `event_intensity`, never `sentiment`.

## 5. GDELT event feature, gap and no-fabrication (mirrors §2/§3 for gdelt)

1. Repeat the gap and before-first-observation checks from §2/§3, substituting
   `--kind gdelt` and asserting on `event_intensity` instead of `gpr`.
2. Expect: identical forward-fill/no-fabrication behavior.

## 6. CLI flag applicability

1. Run: `algo-score events --kind nope --from 2020-01-01 --to 2020-01-02`.
2. Expect: non-zero exit; output names the known kinds (`gdelt`, `gpr`).
