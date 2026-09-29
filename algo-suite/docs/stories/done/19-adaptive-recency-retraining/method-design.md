# Story 19 frozen protocol (T1): adaptive recency-weighted retraining

Status: registered September 28, 2026 by the Lane A coder (Claude) before any new
fit. Everything below is fixed for the study; a change needs a dated amendment
here and in the canonical plan before code or runs that depend on it. Planning
sources: [spec.md](../../../../../.specs/features/recency-weighted-retraining/spec.md),
[design.md](../../../../../.specs/features/recency-weighted-retraining/design.md),
[tasks.md](../../../../../.specs/features/recency-weighted-retraining/tasks.md),
the [review](review.md) and its [disposition](review-disposition.md).

Nothing in this document is an empirical result. Every date in the study has
already been inspected (session 2, Story 20), so every finding of this study is
exploratory (RWT-21).

## Review-disposition approval

The user accepted all ten dispositions as proposed on September 28, 2026. T1
records them as approved; the disposition table is the approved text.

| Item | Approved resolution |
| --- | --- |
| 1 precomputed bundles first | Prepared replay is a parity path; the consume/train/load cycle stays in scope; T10/T12 feasibility gate, no invented LEAN pause API. |
| 2 F equals session 2 | Every policy keeps the separate calibration spans below; session 2 is an external historical reference, not F. |
| 3 H4 second base | Deferred; the primary matrix is five H1 runs. |
| 4 prediction quality | E/U log-loss, Brier and directional accuracy on common mature rows are registered secondary endpoints (RWT-29). |
| 5 concrete data inputs | Named below (M1 partitions, feature construction, watermark); GDELT is not a prerequisite. |
| 6 effective N comparison | E's n_eff is reported beside R's row counts per stage and epoch; neither is "independent observations". |
| 7 compute budget | Measured resource cap frozen below; one shared semaphore across the three stories. |
| 8 determinism | Equal semantic model and decision payloads on pinned inputs; wall time and run IDs are volatile fields outside the digest (RWT-30). |
| 9 epoch UI | Deferred; tabular reports and decision records first (T13/T16). |
| 10 epoch thresholds | Actual thresholds, row counts and changes persisted and reported per epoch (T8/T16). |

## Pinned readings

The specifier pinned these readings of spec-precision gaps; the feature files
and the implementation follow them.

1. Raw weight is `2^(-age_days/half_life_days)` computed absolutely. A partial
   underflow gives exact `0.0` weights for the oldest rows; a stage whose raw
   weights all underflow is rejected as zero total weight, never renormalized
   from nothing.
2. Ingestion "as of" queries are inclusive: a label is mature at cutoff `t`
   when `label_time <= t`. Span selection for fitting is strictly half-open:
   a row joins a span when `start <= available_at < end` and
   `label_time < end` (RWT-01).
3. A source partition declares its bar count; a delivered batch that falls
   short is rejected naming the declared and the delivered counts.
4. `select_rows` on a span with no available history returns an empty
   selection; feasibility is `check_support`'s job (RWT-06).
5. F and Q reuse the initial epoch's family and combiner spans for every later
   D. Q's threshold span moves with D; F's threshold span does not.
6. Per-class minima are raw row counts; n_eff carries the weights.
7. There is no price-feature cache on disk or in code. Price features and
   labels are rebuilt from the M1 partitions at fit time by
   `algo_backtest.training.build_training_rows`; the only `_features` cache
   under the data root is the GDELT event-feature cache, unused by this
   price-only lane. T2 therefore identifies sources by M1 partition path,
   sha256 and bar count, and rows by key.

## Policies (design.md matrix, unchanged)

One strategy configuration, one continuous account per policy across the whole
year, identical filters, costs, sizing and exits. Only the F7 model and its two
thresholds differ.

| ID | Family and combiner fitting | Thresholds |
| --- | --- | --- |
| F | Fit the initial expanding uniform model once, then freeze | Freeze the initial q10 thresholds |
| Q | Same exact initial model as F | Refresh q10 monthly |
| R | Refit monthly on a uniform trailing 180-day family span | Refresh q10 monthly |
| U | Refit monthly on the uniform expanding family span | Refresh q10 monthly |
| E | Same row support as U, exponential weights with a 60-day half-life | Refresh q10 monthly, unweighted |

E versus U isolates recency weighting on identical row support. R versus U
measures history truncation. Q versus F isolates threshold refresh. F and U
share the first bundle. Fit budget: at most 36 distinct fits (one shared
initial F/Q/U fit, 11 later U fits, 12 R fits, 12 E fits); duplicate artifacts
are reused, never refitted.

## Temporal contract

Let D be a UTC month start and C = D minus one day (the preparation embargo).

| Stage | Span (half-open, UTC) |
| --- | --- |
| Family fit | `[start, C - 60d)`; R: `start = C - 60d - 180d`; U and E: `start = 2015-03-02T00:00:00Z` |
| Combiner | `[C - 60d, C - 30d)` |
| Threshold | `[C - 30d, C)` |
| Deployment | `[D, next month's D)` |

Study span: deployment epochs from `2016-03-01T00:00:00Z` to
`2017-03-01T00:00:00Z` exclusive, twelve epochs, March 2016 through February
2017. The epochs cover the span without gaps or overlaps (RWT-03).

Worked first epoch: D = `2016-03-01`, C = `2016-02-29`; family fit ends
`2015-12-31`; R starts `2015-07-04`; U and E start `2015-03-02`; combiner
`[2015-12-31, 2016-01-30)`; threshold `[2016-01-30, 2016-02-29)`.

Rows are assigned by feature availability (bar close), never by the stored
bucket-start timestamp, and only when `label_time < span end`. A `None`
`label_time` is not maturity in this path and is rejected (RWT-24). Eligibility
is independent of trades, vetoes and realized profit (RWT-09). Earlier bars
serve indicator warm-up only; excluded rows are never fitted.

## Weighting

- Half-life `h = 60` elapsed calendar days, the same in the family and the
  combiner stage. Not an optimized value.
- `age_days = (cutoff - available_at) / 86400`, fractional, cutoff = the
  stage's span end.
- Raw weight `w = 2^(-age_days / 60)` (RWT-04).
- Mean-one normalization independently per fitting stage:
  `w' = n * w / sum(w)`, so each stage's weights sum to its row count and the
  regularization scale is unchanged (RWT-05).
- `n_eff = sum(w)^2 / sum(w^2)`: a weight-concentration summary, not a count
  of independent observations and not statistical power.
- Threshold quantiles are unweighted (RWT-10).
- Rejected, never repaired: non-positive or non-finite half-life, availability
  after the cutoff, naive or non-UTC timestamps, negative or non-finite
  weights, zero total weight.

Analytic fixture: ages 0, h, 2h give raw weights 1, 0.5, 0.25; mean-one
12/7, 6/7, 3/7; n_eff 7/3.

## Support minima (RWT-06)

| Stage | Rows | Per class | n_eff |
| --- | --- | --- | --- |
| Family fit | >= 1000 | >= 50 | >= 200 |
| Combiner | >= 100 | >= 20 | >= 50 |
| Threshold | >= 100 | none | none |

A violation rejects the whole epoch candidate with measured and required counts
for every violated minimum. No last-good-model fallback (RWT-15, RWT-27).

## Seed and runtime

- Seed 42 for every LightGBM booster and the logistic combiner
  (`random_state=42`, the existing `_DEFAULT_RANDOM_STATE`).
- LightGBM grid unchanged: `n_estimators=50`, `max_depth=3`,
  `min_child_samples=1`.
- Host runtime at registration: Python 3.11.16, lightgbm 4.7.0,
  scikit-learn 1.9.1, numpy 2.4.6, pyarrow 24.0.0, duckdb 1.5.3.

## Baseline strategy (session 2, Story 20)

The session-2 H1 q10 price-only cell is `h1-q10-base`, which runs the
`h1-baseline` model. All paths below are under the canonical data root
`/home/wellington/workspace/mba-agents/mba-main/algo-suite/data` (readable on
this host; sha256 taken on September 28, 2026).

| Artifact | Path (under `training/2026-09-28-session-2/`) | sha256 |
| --- | --- | --- |
| Cell config | `strategies/h1-q10-base/config.yaml` | `f56dab933dd338fb980378e903e5569caef2e63f1bbf2a1e910c51d89d892d6a` |
| Parent | `strategies/h1-base/config.yaml` | `a236f3f8f3ced21c7cce0d7546471a6d39893c56bba3e51215ba9975169e482c` |
| Template | `strategies/heikin-ashi-h4-talib-volume-off/config.yaml` | `8f359364a7745b5b5f3200f267867d2e23b9994a9480dffe616bc91085845975` |
| Model | `models/h1-baseline.json` | `c290399c701c6287f705c4a9f8e7c04fd02bcd98ca62ddb1b8795a4fca8d66cf` |
| Calibration | `calibration.json` | `4e718dd9a72e5885b637094f15152399ef3bf38690891808cf47b2e5bdce437b` |
| Train map | `train-map.json` | `55e3ee28985e05b2790f52d7a01707cac6c4c68b8a33d739bcc83ad589968037` |

The template file is byte-identical to the repository copy at
`algo-suite/experiments/heikin-ashi-signals/strategies/heikin-ashi-h4-talib-volume-off/config.yaml`
(same sha256). Resolution chain: `h1-q10-base` extends `h1-base`
(`bar_minutes: 60`, `label_horizon_minutes: 60`) extends the H4 template
(`families: [trend, indicator, pattern]`, `regime_gate: false`, 3 % risk,
targets 4R/6R, trail 2R to +0.1R, portfolio at risk 18 %) extends the bundled
`baseline`. Session-2 thresholds `theta_high 0.5401`, `theta_low 0.5165` are
the 0.9/0.1 quantiles of the combiner's January-2016 validation p̂ (440 rows).
The session-2 model was fitted with `--from 2015-03-02 --train-end 2015-12-31
--validation-end 2016-01-31 --test-end 2016-02-29` at code revision
`b72b3f1a` (simulation at `cb418b93`).

Frozen for this study: every policy uses the `h1-q10-base` resolved filter,
cost, risk and exit settings; only `meta_learner.theta_high`,
`meta_learner.theta_low` and the loaded model change per epoch. The
session-2 model and thresholds are an external historical reference, not
policy F (disposition item 2): F's initial bundle is fitted under this
protocol's separated spans.

## Data inventory

| Source | Location | Reachable from the worktree? |
| --- | --- | --- |
| Canonical data root | `/home/wellington/workspace/mba-agents/mba-main/algo-suite/data` (local NVMe) | Not via the default: the Story 19 worktree `/tmp/mba-impl-19/algo-suite` has no `data/` entry, so `ALGO_DATA_ROOT` must point at the root above. The coordinator supplies the local NVMe root at run time. |
| EUR/USD M1 partitions | `parquet/forex/EURUSD/m1/year=YYYY/month=MM/data.parquet` plus `data.parquet.sha256`; years 2015 through 2026, every month of 2015, 2016 and 2017 present | Yes with `ALGO_DATA_ROOT`; read-only for this lane |
| Coverage matrix | `parquet/_meta/coverage.parquet` | Yes with `ALGO_DATA_ROOT` |
| Session-2 training root | `training/2026-09-28-broad-window-h4/data` (`parquet/forex` and `lean-data` are symlinks to the canonical root; event features built there) | Yes with `ALGO_DATA_ROOT`; not needed for price-only |
| Price-feature cache | None exists (pinned reading 7) | n/a |
| GDELT event-feature cache | `parquet/events/_features/gdelt/year=2015..2017` | Present; unused in this lane |
| LEAN data | `lean-data/` (materialized minute store) | Yes with `ALGO_DATA_ROOT` |

Partition checksums for the study's input months (content of each
`data.parquet.sha256`, first column):

| Month | sha256 | Month | sha256 |
| --- | --- | --- | --- |
| 2015-03 | `40db7cab8b8b5219aebeef783fc7d83cd7b72d1429c97ee4a32d23bdbf6a5a84` | 2016-03 | `93a6b4505218cc620424d7f005ff8bd5ada4512b0335121343dc29f381903049` |
| 2015-04 | `c55d4028c942f2b0b641e47fc38c2c7c18e2b9e8964b7e1767db41e7a3896751` | 2016-04 | `6f3b4d0a0681c9df2a2dd2aa6659f132ef9f304dda123e4f84b1f41768eb6e84` |
| 2015-05 | `2a7e887c8a0ba7edd3bd6988eb6e5aa6f9e726f33d60263ecedc5945c36a55aa` | 2016-05 | `42c64e9a1e20658863fc6f78215089704304934c04f94f5806ee7385fb984d49` |
| 2015-06 | `3e78fd15c6559ed141d5c8c8044f9286bde03d210316f3987d863ef9690d45db` | 2016-06 | `dac05ef092be5e635e2abe02b946ace9cc3a356a0e8f7c6fa32a8bca1bf55b24` |
| 2015-07 | `00b2c7128b9b57363c1ce5a59ac5bbf68c27ac4a3aeebae1b1d766abeca16c71` | 2016-07 | `6fac3664e0e3b144ae241fe6215e1996925d05b833627057d50a8fd86adadfab` |
| 2015-08 | `1b422cbfe665fc909b458dc194bd25f5babe8e0e5326a932f1df39c796100cdd` | 2016-08 | `314ba272185dc6d2b91b5ca026b4a43869dd7c1956bb87bc6da6e85d58651925` |
| 2015-09 | `42244bd400f9a8ab40cd7fb7dae5427b9a4d7344f62c46384ae1fc88c315a210` | 2016-09 | `cf9c632dc75172100fa920970a9c25e283eaf544cd46db416239600fd19e7e1c` |
| 2015-10 | `bae6412e840bd660c579923c708ce32a3e8f76fe8d565669407875971abf752d` | 2016-10 | `6ec0eb16419696ba03eaea1b23c6895bc6d8ba0413d0e0d120e177a38330dfbf` |
| 2015-11 | `087aed09a3ab5842b463eb7d14c44334bc541103030eca61fd062b2b78d127e5` | 2016-11 | `db14d4ef136f8a5108e4cbb3f8beedc92cb964f3b2244a4d0d8c95b35874ee71` |
| 2015-12 | `9adc943b7205aae3962b798d611045d8b4b80dfa65c72c3bb96473bb6f3a1e51` | 2016-12 | `a6c1e01440bfb9c43739ca3c52ea116ac2079ac9c274bad28ab2723946b29c7b` |
| 2016-01 | `51a3ec29cbf8af31cbe5af76a55d8a138bbbc4b0c803f07ef3b3f37dccc9e1df` | 2017-01 | `98159a5f3c7f0f75c89ec383f0823d89a4485ce6335df8accbf4687814c71c89` |
| 2016-02 | `365ea70cd72f1d313b3fea25ee6fdd60d42cd5ab48c4407c05386f3e2020a17b` | 2017-02 | `c01b8da620614727155521dafe64f692724e11131c98ae6c6fcb08434543505f` |

A changed checksum invalidates the registration for that month; T18 verifies
these before any run. The availability watermark is the last validated and
persisted bar close, never the on-disk completion of a month (RWT-23).

## Analysis plan

Primary endpoint: mean paired UTC-daily net return difference E minus U over
the common study days, stationary block bootstrap, primary block length 4 days,
sensitivity block length 2 days, 9999 resamples, seed 42, two-sided
alpha 0.05. Reuse `algo_analyze.significance.paired_block_test`.

Feasibility against the current analyzer contract
(`algo-analyze/src/algo_analyze/significance.py`): `validate_block_settings`
requires `n_resamples >= 100` and `alpha > 1/(n_resamples + 1)` (9999 gives
1/10000 < 0.05, satisfied); `_paired_difference` refuses `n < 30` or
`n / block_length < 10`. The trading year 2016-03-01 through 2017-02-28 has
261 weekdays, so the largest possible paired day count is 261 and the
requirement `n >= 10L = 40` for L = 4 (20 for L = 2) is satisfied whenever at
least 40 common equity days exist. The actual `n` is the count of common
UTC days with equity for both arms and is recorded by T16/T18; if it falls
below 40 the primary inference is reported as unavailable, not relaxed.

Secondary, descriptive: R minus U and Q minus F on the same paired daily
grid. Prediction quality: E versus U log-loss, Brier score and directional
accuracy on identical mature evaluation-row keys, with sample counts, reported
separately from trading returns (RWT-29); classification quality never
establishes trading profit. All five policies report net return, drawdown,
trade count, win rate, average win/loss, expectancy, turnover/costs, veto
reasons and monthly/model-age diagnostics with counts, plus per-epoch actual
thresholds, row counts and E's stage n_eff beside R's row counts.

Monthly epochs, overlapping trades and repeated seeds are not independent
market replications.

## Attempt budget and limits

- One attempt per policy (five continuous year-long runs), plus at most one
  logged retry per policy for an infrastructure failure (container, disk,
  timeout). A retry is a logged attempt, never new evidence. Every attempt,
  including failures, stays in the ledger with its resolved parameters
  (RWT-19).
- Host timeout for one cycle (consume, mature, fit, validate, publish):
  30 minutes. A timeout is a failed cycle; replay stops without fallback.
- No half-life sweep, hidden extra seed, early efficacy stopping or strategy
  expansion without an amendment.
- TD-71 affected runs are reported as failed candidates, never patched.

Resource cap, measured by the coordinator on the host (September 28, 2026):

| Resource | Measured by coordinator |
| --- | --- |
| CPU | 24 cores |
| RAM | 121 GB |
| GPU | one RTX 3090, not used by this study |
| LEAN image | `quantconnect/lean:17748` |
| Global cap across Stories 19, 21 and 22 | 3 concurrent LEAN containers |
| Threads per host fit | 8 CPU threads |
| Host timeout per cycle | 30 minutes |

## Native host coordination (feasibility gate)

Not yet verified. No working LEAN pause or host-training API is claimed. T10
and T12 must demonstrate the bounded local request/response mechanism before
replay depends on it; if native coordination cannot meet the timing and state
contract, work stops for a design amendment (prepared-bundle replay stays a
parity path, disposition item 1). Phase 1 (T1 through T5) does not depend on
that outcome.

## Prior evidence outside this registration

Two exploratory pre-checks and one trial preceded this registration and are
evidence, not part of the frozen matrix:

- Commit `ca76847` (T0 pre-check): monthly refit on the session-2 rows,
  frozen versus rolling 3 and 6 months versus expanding; scripts
  `rolling_precheck.py` and `daily_precheck.py` under
  `training/2026-09-28-session-2/`.
- Commit `0d66abf` (D60 trial): 60-day window refitted monthly, H1 and H4,
  job `training/2026-09-28-d60-trial`; the 60-day models sat at or above
  coin-flip log-loss and did not beat the frozen model at either clock.

Those commits also requested a daily-cadence, 60-day "D60" arm and a
calibration-month gate. The parallel-plan commit `ef0111d` rewrote this
story's `review.md` without those amendment sections, and the canonical
`.specs` plan, the review disposition accepted by the user and the Lane A
brief all fix the five-policy monthly matrix above. This registration therefore
freezes the five policies only. A D60 short-window control, a daily cadence or
a calibration-month gate needs a separate dated amendment to spec, design,
tasks and this protocol before any run; nothing here treats them as approved
or as rejected.

## Docs gate evidence (T1)

Recorded in [progress.md](progress.md) with commands, cwd, exit codes and
counts: `git diff --check`, the strict spec validator and the strict tasks
validator from `/home/wellington/.claude/skills/tlc-spec-driven/scripts/`.
