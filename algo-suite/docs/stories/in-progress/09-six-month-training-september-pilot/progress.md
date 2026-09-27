# Six-month training and September pilot

## Follow-up — 2026-09-27

The supervisor completed at 22:45 PDT on September 26 with exit code 0.
Baseline `20260927T044836-4cd12c922200` and hybrid
`20260927T053156-4f2ebf081eaf` both completed with zero trades. Story 11's
[saved-run evidence](../../done/11-statistical-inference-corrections/evidence/pilot-sources.json)
verifies 30 recorded daily portfolio returns per run and unchanged source hashes.
Flat equity makes DSR and paired uncertainty unavailable. This pilot story stays
in progress: diagnose inactivity and complete its audit before extending or
interpreting the experiment. The earlier snapshot below is retained as history.

## Decision — 2026-09-26

The user requested training now on the first six available months, an initial
September 2015 simulation today, and continuation over the remaining period
tomorrow. Use EUR/USD baseline and hybrid with the existing EMA configuration.
DSHA retraining is not included in this execution.

| Purpose | Inclusive dates |
|---|---|
| Family-model fitting | 2015-02-02 through 2015-06-30 |
| Combiner calibration | 2015-07-01 through 2015-07-31 |
| Held-out rows required by existing trainer | 2015-08-01 through 2015-08-31 |
| Initial LEAN simulation | 2015-09-01 through 2015-09-30 |

The first GDELT day cannot provide a prior-day publication-lagged feature, hence
February 2 is the start. Split-boundary labels are purged by the existing trainer.
August and September must not influence fitting or calibration. Freeze the model
artifacts for tomorrow's evaluation; do not tune against this pilot and then call
September untouched test data.

## Execution

Snapshot: September 26, 2026, 22:03 PDT. Both baseline and hybrid training
completed: 153,531 fitting, 32,813 calibration, and 30,297 held-out rows each.
The baseline September replay completed with `success=True`, zero closed trades,
and run ID `baseline/20260927T044836-4cd12c922200`. Its zero-valued metrics do not
establish performance; inspect coverage, model decisions, and vetoes first.
Hybrid replay is waiting for September's GDELT `.done` marker.

First attempt started at 21:43 PDT (PID `642640`), saved the baseline model,
and stopped because the broker adapter was missing. Resumed supervisor PID
`643301` sets `ALGO_BROKER__ADAPTER=oanda`, preserves that model, and runs feature
preparation and hybrid training before simulations. The original failure log
and exit status remain as `attempt-1-*`. Fifteen training-data/perception BDD
checks passed. No paired performance or significance result is claimed.

[The evidence snapshot](evidence.json) records both model hashes, fitting provenance,
and the baseline run manifest without committing bulk artifacts.

Local job directory, relative to `algo-suite/`:
`data/training/2026-09-26-six-month-pilot/`.

- `run.sh`: exact execution commands; shell syntax checked.
- `pid`, `status.txt`, `pipeline.log`: supervisor and current stage.
- `exit-status.txt`: written on pipeline exit; zero means all stages succeeded.
- `baseline-training.log`, `hybrid-training.log`: fitting logs.
- `baseline-f7.json`, `hybrid-f7.json`: separately saved models with input hashes,
  split dates, row counts, strategy configuration, revision, and package versions.
- `baseline-september.log`, `hybrid-september.log`: simulation logs and result IDs.
- `data/runs/`: this pilot's LEAN artifacts.

The job runs detached and stops on the first failed command. Stage order: baseline
training, monthly event-feature builds, hybrid training, baseline September
simulation, September completion check, September event features, hybrid simulation.
Backtests have a four-hour timeout each. The September completion wait is bounded
at six hours after baseline simulation; it fails if the marker does not arrive.

The actual active downloader uses this checkout's **local** `algo-suite/data/`,
not the older NAS copy described in previous status snapshots. February–August
GDELT `.done` markers and EUR/USD price partitions were verified. September had
reached September 19 by the status snapshot, so its presence alone is not completion.
The job requires September's `.done` before using it for hybrid evaluation.

An isolated job data root links completed canonical event months, price Parquet,
and existing LEAN data. It owns its derived features and run outputs. This avoids
reading October while the downloader rewrites that month's partial Parquet.
October 1 event features are generated from completed September data to cover the
last September bar's decision timestamp. Bundled models are not overwritten.

## Follow-up

- Inspect exit status and both simulation logs; resolve failures before reporting
  any comparison. Check actual run dates, model hashes, trades, and decision audit.
- Generate descriptive paired metrics after successful simulations. Story 11
  must correct inferential statistics before significance claims are made.
- Tomorrow, extend evaluation over newly completed months with these frozen models.
- Retain existing method limitations: event-derived news, missing text sentiment
  and pattern detection, and the trainers' smoke-test label/model assumptions.
  A successful pilot is not a full walk-forward study or completed Chapter 4.
