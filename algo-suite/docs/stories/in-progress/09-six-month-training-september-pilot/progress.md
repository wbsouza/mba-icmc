# Six-month training and September pilot

## Amendment — 2026-09-27: filter parameters in config.yaml, regime gate off, $10,000 account

Decisions taken with the user after the zero-trade diagnosis below:

1. **Every filter's parameters are configuration, not code.** `strategies/<name>/config.yaml`
   now carries one section per configurable filter — `news_context` (F4), `risk_guard`
   (F5), `capital_mgmt` (F6: `risk_per_trade` plus the sizing economics the chain feeds
   F6) and `meta_learner.theta_high/theta_low/regime_gate` (F7). Each filter module owns
   `parse_*_config`; the loader fails fast on a listed filter without its section, a
   section without its filter, a missing key or an out-of-range value. `hybrid` inherits
   F5/F6/F7's sections from `baseline` via `extends:` and adds only `news_context`. The
   `conf/backtest.yaml` loaders and the `chain/wiring.py` constants are removed (TD-43
   closed). Later the same day, at the user's request that *every* item be a parameter
   (defaults for the ones that almost never change): `price_features` (EMA/RSI/MACD
   periods, shared by training and serving, recorded in the model's provenance and
   checked on `--model`), `indicator` (F2 midline/threshold), `pattern` (F3 vocabulary)
   and `meta_learner.label_horizon_minutes`. Defaulted sections are written back into
   the resolved config so `strategy-config.json` shows the effective values. Finally,
   strategies are resolved from their YAML rather than a code registry (`--strategy` takes
   any bundled or `--strategies-dir` name; F4 in `filters` selects the news-aware
   algorithm), `extends:` chains of any depth compose like compose override files, and
   every parameter records its source (`<name>/config.yaml` or `default`): printed at run
   bootstrap, `algo-backtest explain-strategy`, and `strategy-provenance.json` per run. Modelled on the reference engine's per-component parameter maps with parent
   inheritance (the Spring version's deployment and strategy configuration).
2. **F7 regime gate off** (`regime_gate: false` in both bundled configs). The gated rule
   cannot fire with these models (diagnosis below); the gate stays available as a switch.
3. **Thresholds calibrated on the July-2015 validation span**, per the methodology
   (Chapter 3: "calibrated on the validation span and held fixed"), never on September.
   Procedure: rebuild the pilot's training rows (`algo_backtest.training.build_training_rows`
   over 2015-02-02..2015-08-31, EMA perception), `walk_forward_split` at 06-30 / 07-31 /
   08-31, predict p̂ on the validation and held-out spans with the frozen
   `baseline-f7.json` / `hybrid-f7.json`, and count signals and 15-minute directional
   hits for a grid of thresholds with the gate on and off. Full grid:
   [`evidence/threshold-calibration.json`](evidence/threshold-calibration.json).

   | Model / span | θ_high / θ_low | gate | signals (share of bars) | directional hit |
   |---|---|---|---|---|
   | baseline / Jul validation | 0.55 / 0.45 | on | 48 (0.15%) | 0.542 |
   | baseline / Jul validation | 0.55 / 0.45 | off | 5,140 (15.7%) | 0.568 |
   | baseline / Jul validation | 0.56 / 0.44 | off | 2,352 (7.2%) | 0.570 |
   | baseline / Jul validation | 0.53 / 0.47 | off | 17,662 (53.8%) | 0.547 |
   | baseline / Aug held-out | 0.55 / 0.45 | off | 5,113 (16.9%) | 0.529 |
   | hybrid / Jul validation | 0.55 / 0.45 | off | 5,223 (15.9%) | 0.569 |
   | hybrid / Aug held-out | 0.55 / 0.45 | off | 5,274 (17.4%) | 0.524 |

   Chosen: **0.55 / 0.45, gate off** — the widest band that still yields a usable signal
   count on validation; tighter bands lose most signals for no hit-rate gain. The
   validation hit rate is in-sample for the combiner (July fitted it); August is the
   first out-of-sample reading and is only marginally above 0.5. A 15-minute directional
   hit is not profitability: spread, stop and sizing decide that in the simulation.
   This calibration inspected the validation and held-out spans only; September remains
   untouched by parameter choice, but the gate decision itself was taken after seeing
   September's zero-trade outcome, so September is development data for the gate
   (see "Remaining work").
4. **Account starts from $10,000**: new run parameter `--param cash=<deposit>` on the
   chain strategies (`set_cash` in `engine/chain_algorithm.py`), logged as
   `<TAG>_STARTING_CASH`. The engine controls still hard-code $100,000 (TD-65).

Verification: 977 BDD scenarios green (`make test`), mypy strict clean on the tools,
perception/inference architecture gates pass; Ruff/mypy remain red only in the
BigQuery export scripts (TD-64, pre-existing on `main`). Thesis Chapter 3's terminal
rule now carries the gate switch $g$ and builds.

September replay job (frozen 2026-09-26 models, amended chain): local
`data/training/2026-09-27-f7-ungated-september/` — `run.sh`, `status.txt`,
`exit-status.txt`, `model-hashes.txt`, `git-revision.txt`, `baseline-september.log`,
`hybrid-september.log`; LEAN artifacts land in the pilot's shared data root under
`data/runs/<strategy>/<stamp>/`. Results (job exited 0 at 03:16 PDT, 2026-09-27; git revision at launch
`709b9bd` + the uncommitted amendment, models unchanged — SHA-256
`1a6fd37e…4e831e` baseline, `a6dda4c2…06af9b7` hybrid; `qa_check.py` PASS on both):

| Run | Run ID | Closed trades | Decisions BUY / SELL / HOLD / F1-vetoed | Start → end equity | Net | Max DD | Win rate |
|---|---|---|---|---|---|---|---|
| baseline | `baseline/20260927T094856-5d34ecde9301` | 1,032 | 1,976 / 3,222 / 18,169 / 8,145 | $10,000 → $9,995.38 | −0.05% | 1.5% | 60% |
| hybrid | `hybrid/20260927T100447-5e124bec56dc` | 1,069 | 1,780 / 3,671 / 17,916 / 8,145 | $10,000 → $10,051.41 | +0.51% | 1.5% | 62% |

The machinery now trades: every BUY/SELL decision joins a LEAN trade (11,429 and
11,708 decision rows carry a `trade_id`), the account starts from the requested
$10,000, and every parameter is in the run's `strategy-config.json`. F4 ABSTAINed on
all 23,367 hybrid bars (no sentiment source, no event-intensity veto in September), so
the hybrid's difference from baseline comes only from the news family's input to F7.
Average win ≈ 0.01% and average loss ≈ 0.02% per trade with ~1,000 trades in a month:
these are minute-scale, near-zero-fee flips, not an economic result — TD-51's execution
economics (fixed 20-pip stop, no spread model in the fill, size 0.5) still apply, and no
paired inference has been run. Yesterday's zero-trade runs (`…T044836`, `…T053156`)
remain on disk for the audit trail.

Defect found by the QA procedure: the run's `strategy-config.json` (written inside the
LEAN container by `write_text_atomic`) came out root-owned with mode 0600, unreadable
on the host. Fixed in `algo_core.atomicio` (the published file now gets the ordinary
umask mode; scenario in `atomic_write.feature`); the two September run folders were
made readable with an unprivileged `chmod` container.

## Zero-trade diagnosis — 2026-09-27

Data was not missing. At training time (2026-09-26 21:43 PDT) the canonical
GDELT months 2015-02 through 2015-08 were complete (`.done` written 19:55–21:18
PDT, every calendar day present, 2.9M–8.9M events per month) and both models
hash all seven months. The September replay evaluated 31,512 minute bars and
every filter ran; `decisions.parquet` records a p̂ for 23,367 bars.

Cause: the F7 terminal rule and the fitted model disagree in sign. F7 emits BUY
only if p̂ > θ_high = 0.55 **and** F1's regime is bull, SELL only if
p̂ < θ_low = 0.45 **and** regime is bear. In September the fitted combiner
produced p̂ < 0.50 on every bull bar (11,540 bars, 99th percentile 0.493) and
p̂ > 0.49 on every bear bar (11,827 bars, 1st percentile 0.491). Neither
condition can hold simultaneously, so all 23,367 bars are HOLD. The remaining
8,145 bars were vetoed by F1 (primary vs. higher-timeframe direction conflict).
The label is the 15-minute forward up-move; the model has learned mean reversion
relative to the EMA trend at that horizon, which the regime-gated rule forbids.

| Run | Bars reaching F7 | bull with p̂<0.45 | bear with p̂>0.55 | BUY/SELL |
|---|---|---|---|---|
| baseline `20260927T044836-4cd12c922200` | 23,367 | 3,222 | 1,976 | 0 |
| hybrid `20260927T053156-4f2ebf081eaf` | 23,367 | 3,671 | 1,780 | 0 |

Retraining on the same six months reproduces this; the block is the rule/model
interaction, not the data. Any change to θ, the regime gate, the label horizon,
or the model made after inspecting these September outcomes turns September
into development data and requires a later untouched window for confirmation.

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
