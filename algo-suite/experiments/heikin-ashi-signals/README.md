# Heikin-Ashi signal ablation — exploratory H4 pilot

This is an **exploratory, previously inspected 2015 window**, not a confirmatory
test, reproduction of the author's earlier Heikin-Ashi trading manager, or
walk-forward thesis result. The initial matrix contains exactly four EURUSD
Heikin-Ashi H4 **template proxies**:

| Strategy | Pattern detector | Volume gate |
| --- | --- | --- |
| heikin-ashi-h4-disabled-volume-off | disabled | absent |
| heikin-ashi-h4-disabled-volume-on | disabled | present |
| heikin-ashi-h4-talib-volume-off | TA-Lib | absent |
| heikin-ashi-h4-talib-volume-on | TA-Lib | present |

The default four YAMLs extend the bundled baseline and explicitly repeat each active
filter's parameters. F4/news is absent from this initial family. There is no pattern skill dependency: the detector
uses the repository's TA-Lib adapter. The volume gate uses quote tick counts,
not exchange-traded volume; its baseline is the previous 20 closed H4 bars and
its minimum relative activity is 1.0. Volume is an independent veto, not an F7
feature. F7 keeps the trend/indicator/pattern families in every cell, including
the neutral pattern family when detection is disabled.

An optional `--mode hybrid` selects exactly four matched counterparts:
`heikin-ashi-h4-hybrid-{disabled,talib}-volume-{off,on}`. These explicitly extend
the bundled hybrid configuration and differ from the paired baseline ONLY by
F4/news context and the added F7 news family. All price/label periods, costs,
risk/exit rules, thresholds, date windows, and pattern/volume treatments match.
Hybrid uses `train_hybrid_meta_learner.py`; baseline uses
`train_baseline_meta_learner.py`. Both receive explicit `--strategy`,
`--strategies-dir`, and `--out`. Each mode trains four separate models.
There is no combined mode or automatic H1/H4 × baseline/hybrid 16-run sweep.

Hybrid's `news_context.event_intensity_veto_threshold=-0.5` and
`sentiment_direction_threshold=0.15` come from the bundled
`algo-backtest/src/algo_backtest/strategies/hybrid/config.yaml`, not from the
reference template. Consequently baseline versus hybrid measures adding both the
F4 gate/opinion and news late fusion; it is not a pure F7-family-only ablation.

## Reference template settings

The Heikin-Ashi H4 template is the H4 configuration of the author's earlier
Heikin-Ashi trading manager (unpublished). Only its risk and exit settings are
carried over, as the YAML values below; `plan.yaml` and the variant YAMLs hold
every value, and the runner copies, hashes or reads nothing else from that
system. These are historical configuration values, not evidence that the
original strategy has been reproduced.

| YAML key | Value | Note |
| --- | --- | --- |
| `capital_mgmt.risk_per_trade` | 0.03 | template risk per trade |
| `risk_guard.portfolio_at_risk_cap` | 0.18 | existing account-risk gate, not a reproduction of the template's allocation logic |
| `price_features.bar_minutes` | 240 | exact complete UTC buckets |
| `capital_mgmt.stop_loss_shrink` | 0.50 | applied to the swing proxy stop |
| `capital_mgmt.targets[0]` | `at_level_ratio: 4.0, close_fraction: 0.5` | target at 4R closes half of the original position |
| `capital_mgmt.targets[1]` | `at_level_ratio: 6.0, close_fraction: 0.5` | target at 6R closes the remaining half of the original position |
| `capital_mgmt.trail_stops[0]` | `at_level_ratio: 2.0, to_level_ratio: 0.1` | one trail step arms at 2R and moves to +0.1R; repository spread-aware formulas apply |

Unsupported template semantics, never silently mapped onto this matrix:

- The template's proprietary trend-line buffer and its buy/sell entry and
  stop-loss indicator buffers are not implemented; baseline EMA directions,
  F1/F2/F3/F7 entries and the rolling swing stop are explicit research
  substitutions, not equivalents.
- The template's exit-point buffers are not implemented; `close_on_veto=false`
  does not implement them, and baseline opposite-signal and planned-order exits
  remain.
- The template's trail/target risk-offset flag is not explicitly set in the H4
  template; no claim is made about an inherited default, and the current
  trade-plan schema has no such setting.
- No MetaTrader/account/statement deployment integration; OANDA simulated
  adapter and local reports only.
- The Heikin-Ashi H1 template (60-minute selector with a 20 % stop cut; trail
  1R -> -0.66R without risk offset, then 1.5R -> 0R with risk offset; final
  target 3R) is documented but NOT included or launched by this setup; its risk
  offset cannot be faithfully represented by the current schema, and no H1 YAMLs
  are generated.
- The setup template (240-minute deployment, 50 % stop cut; middle target 1R
  closing 50 %, trail 0.5R -> 0R, final target 1.5R) and its directional bias
  buffers are a different management family, deliberately excluded from these
  four runs.
- No active explicit symbol deployment is inherited; EURUSD is a research choice.

The 1R/2R template (1R/50 %, trail 1R -> 0R, final 2R), a 2R/50 % variant with
risk offset (trail 2R -> 0.1R with risk offset, final 4R), and an against-trend
variant also exist in the earlier system. They are outside this matrix; no
unsupported options are silently mapped onto the Heikin-Ashi H4 template.

## Explicit research assumptions

Training is 2015-02-02 through 2015-06-30; July 1–31 calibrates the combiner;
evaluation is September 1–30, 2015. August is a gap in reported evaluation.
The existing trainer reads through September and internally labels its unused
held-out partition August–September; neither month is fitted. Only September
is passed to LEAN. All four arms use the same dates and sources.

`label_horizon_minutes: 240` means one **delivered complete** H4 bar ahead.
The current trainer counts delivered bars, so elapsed time can exceed four hours
across a market break; it does not synthesize missing buckets. This is an explicit research assumption:
the baseline's 15-minute horizon cannot be used on 240-minute bars because 15
is not divisible by 240. Completed-bar aggregation omits partial buckets and
never fills market gaps. Main must establish training/live parity before launch.

The following values are baseline/research choices, **not reference template parameters**:

| Area | Explicit settings |
| --- | --- |
| F1/perception | EMA; periods 3, 8, 60 count H4 bars. ema_higher_tf=60 is a period, not an H1 aggregation setting |
| F2/price indicators | RSI 14/midline 50; MACD 12/26/9/histogram threshold 0; ATR 14 |
| F3 | TA-Lib or disabled; bullish engulfing/hammer/morning star versus bearish engulfing/shooting star/evening star |
| F4 (hybrid only) | GDELT event-intensity veto at or below -0.5; sentiment direction magnitude 0.15, when sentiment exists; bundled hybrid research choices |
| F5 | Daily drawdown -5%, weekly -15%, max concurrent trades 2, max leverage 30; retained baseline caps |
| F6/stop | swing source, 60 H4 bars; minimum 5 pips and broker-minimum factor 1.2; min reward:risk 2.0 |
| F6/economics | $10 per pip/lot, 100000 units/lot, leverage 30; fixed stop 20 pips and ATR multiplier 2.0 are declared but inactive for swing |
| F7 | theta_high=0.55, theta_low=0.45, regime_gate=false explicitly retains the baseline pilot choice; no template analogue |
| Execution | Spread 1 pip, commission 0, broker stop level 0, min_hold_bars=0, close_on_veto=false |
| Account | EURUSD, USD cash 10000, simulated OANDA; the reference template does not establish these economics |
| Resource limits | plan.yaml resources: workers=1 (prepare-time option 2), lean_max_concurrent=6, lean_container_cpus=4, lean_container_mem_gib=8, training_numeric_threads=4, training_device=cpu; training timeout 7200s, LEAN timeout 1800s, host grace 60s |

The current runner trains four separate models. Sharing the same-pattern model
between volume-off/on arms is permissible because volume does not enter F7;
that optimization is intentionally not implicit. Different pattern detectors
must have separately trained models. No old bundled model is overwritten.

## Prepare first; main launches only after parity

Main reports H1/H4 native parity passed; the existing M1 RSI rounding fix is
pending separately. This setup remains H4-only and launches nothing automatically.
Preparation should follow final code changes because archived code hashes must
match at execution. No current jobs or host concurrency limits are modified.

The resource budget is explicit in `plan.yaml` and copied into each run's
`provenance.json` and `parameters.md`, along with the exact child environment.
The inspected host has 24 logical CPUs and 121 GiB RAM (about 57 GiB available
at the resource review), with two existing LEAN jobs at about 2 CPUs each.
Six future LEAN slots at 4 CPUs/8g each imply up to 24 CPUs and 48 GiB of
container limits across processes using that slot range; existing jobs retain
their own limits. Candidate workers are a separate bound: this runner launches
only one or two cells. It neither restarts existing jobs nor edits prepared plans.
All budgets remain provisional; main coordinates launch against current host load.

GPU capability was checked with a one-tree, 64-row synthetic diagnostic using
installed LightGBM 4.7.0. Its OpenCL GPU backend successfully selected the RTX 3090
(24 GiB). No project dataset or persisted experiment model was used. Production
training remains on the existing CPU backend: availability is not numerical/model
parity approval. The runner refuses a non-CPU `training_device`; changing backend
requires a separately reviewed parity check. CPU thread settings include
`OMP_THREAD_LIMIT=4` as well as OpenMP/BLAS thread counts because LightGBM's wrapper
can request its own thread count. No model hyperparameters or training algorithm change.

Run with this checkout's existing environment; no dependency synchronization or
input downloads are performed. From `algo-suite/`:

```sh
.venv/bin/python experiments/heikin-ashi-signals/runner.py prepare \
  --mode baseline \
  --input-root /home/wellington/workspace/mba-agents/mba-main/algo-suite/data \
  --output-root /tmp/heikin-ashi-h4-REPLACE-WITH-UNIQUE-ID
```

For the optional comparable hybrid family, use the same command with
`--mode hybrid` and a different fresh output directory. Omitting `--mode`
selects baseline; each prepared manifest contains only the selected four runs.
Execution reads that archived selection and cannot add another family.
For bounded parallel execution, add `--workers 2` to **prepare**, using a new
output directory. `execute` then uses the archived worker count; its optional
`--workers 2` is only a consistency check and rejects a different prepared count.
Omitting this flag preserves the plan's sequential default. Finish parent
documentation/provenance edits before preparing: the code fingerprint stays frozen.

Preparation only archives and validates. It requires all February–September
minute Parquet partitions and every September weekday's LEAN quote zip. These
presence checks do not certify intraday completeness or train/live parity.
Hybrid additionally requires GDELT feature partitions for February–October:
September's final closed bar has its decision at October 1, 00:00 UTC. Those
partitions and any September/October `lm_symbol` sentiment partitions are hashed.
Absent sentiment is recorded explicitly; the existing hybrid trainer always
uses missing sentiment, so any present live sentiment requires main to verify
that train/serve assumption before using the hybrid results. The worker applies
the production news-coverage check before launching LEAN. It does not build news
or substitute missing inputs. Baseline requires no news input files.
It refuses existing or overlapping output roots. It hashes the input files and
the current code/configuration, including untracked source changes. Do not
prepare against a checkout still being edited; code drift invalidates the plan.

After main finishes parity checks, it may explicitly execute:

```sh
.venv/bin/python experiments/heikin-ashi-signals/runner.py execute \
  --output-root /tmp/heikin-ashi-h4-REPLACE-WITH-UNIQUE-ID
```

Each child is awaited individually; its exact return code is recorded. Execution
uses batches of at most the archived worker count. A failing batch drains its
already-started cells, records every outcome, and does not submit later cells;
with one worker the first failure stops immediately. Timeouts record 124, spawn failures 127. This
runner never starts background batches or uses bare `wait`. A claimed output
root cannot be executed again; failures require a fresh directory, preserving
the failed run. An abrupt host termination can leave status `*_running`; that
is incomplete, never success. Host/container timeouts are bounded, but forced
host termination may require inspecting Docker for an unfinished container.
Specifically, `subprocess.run(timeout=...)` kills and waits for its direct Python
child. That does not synchronously prove the Docker container has stopped:
normal testcontainers teardown or its Ryuk reaper handles container cleanup,
and Ryuk cleanup can be delayed or unavailable after abrupt termination. A host
timeout is recorded as 124, never success; inspect Docker before scheduling
replacement work if cleanup has not completed. These budgets do not bound the
time spent hashing input files or waiting for container cleanup.

Only the parent executor checks immutable inputs before each batch and after
all its cells have joined. It writes atomic `batch-NN-before-input-check.json`
and `batch-NN-after-input-check.json` reports. It also writes atomic
`final-input-check.json` on normal success, child failure, or a handled execution
error. Reports compare code and market/news inputs against
the manifest's SHA-256 values, record expected/observed hashes and errors, and
detect input/code file-set changes. Sealed per-cell model hashes are checked too;
each backtest child independently checks its model before LEAN starts.

These runtime checks do not re-hash `prepared-hashes.json`'s mutable status/model
records. Any mismatch makes the experiment exit 1, even when the child succeeded
or returned another failure code (individual child outcomes remain archived).
No later batch is submitted. Files are checked at those boundaries: matching
hashes prove byte identity at observation time, not the absence of a transient
write subsequently reverted. Abruptly killing the parent can prevent a final
report; a missing final check means immutability was not verified to completion.

Before **any training child**, every run directory already contains resolved
`strategy-config.{yaml,json}`, `strategy-provenance.json`, `provenance.json`,
`parameters.md`, `commands.json`, `hashes.json`, and `status.json`. The initial
model hash is explicitly null/not_trained; after training its SHA-256 is written
before the LEAN child starts. Status is updated atomically on child exit.
Standard LEAN results, metrics, trade ledger, statement, equity and report live
in each run's `results/`; settings and logs are alongside that directory.
Each run also contains `template-settings.md` (a copy of this document) and its
original variant plus bundled baseline/hybrid YAMLs in `source-configs/`.
Per-leaf provenance names the source for every resolved filter setting; the
template-settings document explains reference values, research choices and
unsupported semantics. News availability and hashes are recorded per run in `provenance.json`.

## Input/output isolation and current integration boundary

`algo-backtest run` currently has neither `--run-id` nor `--results-dir`; it
generates fresh timestamped paths under `ALGO_DATA_ROOT/runs/<strategy>/`.
Setting a new data root would also hide source data. `/data` does not exist in
the inspected host environment. Do not create symlink overlays or copy/mutate
the user's input tree to work around this.

Instead the child uses the existing Python API
`run_strategy(data_root=explicit_input_root, results_dir=fresh_run/results, ...)`.
Training receives the explicit input root through `ALGO_DATA_ROOT` and an
explicit `--out` inside the new run directory. LEAN mounts source directories
read-only; host training reads them without writing. Host filesystem permissions
are not changed, so this is not an OS-level read-only sandbox for host code.
Inherited `ALGO_*` and `LEAN_*` overrides are removed for children; all relevant
simulation parameters are provided by the archived plan/strategy. No ambient
backtest config is loaded by the direct API.

Canonical inputs are `parquet/forex/EURUSD/m1/...`; main's concurrent integration
now mounts the security-type directory under `activity/parquet/forex` for volume
runs. This setup uses that production API and does not create an alias or modify
engine files. Main still verifies training/LEAN parity before launch. Package/version
and code hashes capture the implementation actually used when preparation runs.

Scoped checks (these do not train or launch LEAN):

```sh
.venv/bin/pytest algo-backtest/tests/steps/test_heikin_ashi_experiments.py -q
.venv/bin/ruff check experiments/heikin-ashi-signals/runner.py algo-backtest/tests/steps/test_heikin_ashi_experiments.py
.venv/bin/mypy experiments/heikin-ashi-signals/runner.py
```
