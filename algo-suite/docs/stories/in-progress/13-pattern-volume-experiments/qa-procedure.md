# Story 13 verification and experiment handoff

## Location, ownership and safe takeover

Run commands from `/tmp/mba-pattern-volume/algo-suite` on branch
`feat/13-pattern-volume-experiments`. Implementation snapshot: `28cc7d9`, pushed.
See [progress.md](progress.md) for all agent/worktree ownership and subsequent commits.
Do not check out or reset Claude's original checkout, modify old experiment data,
overwrite existing results, or launch another copy of a still-running experiment.

The source input root is the existing six-month pilot's `data` directory under
`/home/wellington/workspace/mba-agents/mba-main/algo-suite/data/training/`.
The new output root is this worktree's `build/experiments/`, outside that input tree.
All test markets are synthetic fixtures and must never be reported as performance.
Experimental results use the actual archived EURUSD/GDELT data.

## Test layers: what each proves

| Layer | Feature / implementation | Proof and limitation |
| --- | --- | --- |
| Candle detection | `candlestick_detector.feature`; `perception/candlestick.py` | Real TA-Lib outputs, polarity/conflicts, warm-up, malformed OHLC and score handling. Scores are not probabilities; no trading profitability claim. |
| Tick activity | `tick_activity.feature`; `perception/volume.py`, `tick_activity.py`, `filters/volume_strength.py` | Prior-only mean, threshold veto, missing/zero evidence, exact UTC minute lookup, canonical types and partition hashes. Quote counts are not traded volume. |
| Complete candles | `bar_clock.feature`; `perception/bar_clock.py` | UTC-aligned complete bucket emission, aggregation, gaps/partial buckets and invalid timestamps. No future candle flush. |
| Combined configuration | `market_signals.feature`, `signal_configuration.feature` | Shared train/serve producers, resolved defaults, compatible model detector, valid decision clocks, incompatible DSHA/sub-bar horizon rejection. |
| Trainer family contract | `training_family_contract.feature` | Both real CLI entry points reject incompatible families/news filters before reading price/news data; all eight candidate configs accepted. |
| Activity provenance | `activity_run_provenance.feature` | Real Parquet/config/artifact I/O with only engine invocation mocked. Manifest exists before engine start; missing or mutated input fails closed. |
| RSI boundary | `rsi_native_rounding.feature` | Offline average-loss threshold follows LEAN's decimal rounding boundary, including the half-even tie. |
| Native combined parity | `closed_signal_parity.feature` | Five-day quote fixture through pinned LEAN at M1/H1/H4 versus offline rows: timing, readiness, indicators, candle labels and quote-activity ratios. One missing minute exercises fill-forward/zero activity. |
| Native legacy parity | `feature_parity.feature` | Existing EMA/news/DSHA parity, gaps and ties, preserving old contracts. Two probe initializers were repaired to supply Story 12 economics. |
| Native risk calendar | `minute_pnl_anchors.feature` | Actual `ChainAlgorithm.on_data` imported inside LEAN; unrelated collaborators stubbed. Every quote updates real `PnlWindows` before candle checks. Daily/week/year rollover, idempotence and no-quote behavior. Not a fills/PnL-economic reconciliation. |
| Real chain/orders | `run_baseline_chain.feature`, `run_hybrid_chain.feature` | Complete production wiring, fills, audit joins, stop, partial target, trailing and spread with pinned LEAN. Slower than pure/probe tests. |
| Experiment runner | `spockfx_experiments.feature` | Fresh disjoint roots, full parameter/source archives, isolated fingerprints, exact child exits, timeout/failure channels, bounded workers, before/after immutable-input checks. Child execution mocked; actual runs are separate. |
| Figures/evidence | `evidence/tests/features/intermediate_figures.feature` | Real completed source artifacts; rejects unfinished/tampered sources, preserves equity/drawdown samples and parameter links. |

All behavior tests are Gherkin plus pytest-bdd steps. Native tests carry `integration`
and are excluded by default. No native import stub is represented as an engine test.

## Reproducible verification commands

```sh
uv sync --all-packages
uv run pytest algo-backtest/tests -m 'not integration' -q
uv run ruff check algo-backtest experiments/spockfx-signals tools/perception_quality.py
uv run mypy algo-backtest/src algo-backtest/scripts experiments/spockfx-signals/runner.py tools/perception_quality.py
uv run python tools/perception_quality.py --architecture-only
uv run python tools/inference_quality.py --architecture-only
make audit
```

Native commands use the explicitly authorized host budget. Keep the shared slot
limiter; do not bypass it. Old jobs may occupy slots 0/1, so leaving the default two
slots can queue indefinitely. Each actual invocation below has its own output root.

```sh
LEAN_MAX_CONCURRENT=6 LEAN_CONTAINER_MEM_LIMIT=8g LEAN_CONTAINER_CPUS=4 OMP_THREAD_LIMIT=4 OPENBLAS_NUM_THREADS=4 \
  uv run pytest algo-backtest/tests/steps/test_closed_signal_parity.py -m integration -q
LEAN_MAX_CONCURRENT=6 LEAN_CONTAINER_MEM_LIMIT=8g LEAN_CONTAINER_CPUS=4 OMP_THREAD_LIMIT=4 OPENBLAS_NUM_THREADS=4 \
  uv run pytest algo-backtest/tests/steps/test_feature_parity.py -m integration -q
LEAN_MAX_CONCURRENT=6 LEAN_CONTAINER_MEM_LIMIT=8g LEAN_CONTAINER_CPUS=4 OMP_THREAD_LIMIT=4 OPENBLAS_NUM_THREADS=4 \
  uv run pytest algo-backtest/tests/steps/test_minute_pnl_anchors.py -m integration -q
LEAN_MAX_CONCURRENT=6 LEAN_CONTAINER_MEM_LIMIT=8g LEAN_CONTAINER_CPUS=4 OMP_THREAD_LIMIT=4 OPENBLAS_NUM_THREADS=4 \
  uv run pytest algo-backtest/tests/steps/test_run_baseline_chain.py algo-backtest/tests/steps/test_run_hybrid_chain.py -m integration -q
```

The actual first native combined run used `--basetemp=build/signal-native-final`:
three new scenarios passed, eight legacy scenarios failed because their probe
initializers lacked `_economics`. Preserve those failure logs. After repair,
`--basetemp=build/legacy-parity-fixed` passed all eight legacy scenarios. New signal
parity also previously passed in `build/closed-signal-native-v2`.
The order-chain batch used `build/chain-native-final`: **9 passed, 16 deselected**
in 1,162.82 seconds. Never reuse these basetemp directories: pytest may clear them. Let pytest
choose a fresh default or choose a new uniquely named directory.

Final offline backtest rerun: **1,364 passed, 53 deselected**. Native combined 3;
legacy 8; risk calendar 4; targeted runner/activity/trainer batch 54. These overlap:
**do not sum them into a unique test total**. Final full rerun adds the trainer scenarios.
Scoped lint/type/architecture/audit pass. Whole-workspace lint/type still report
pre-existing BigQuery/tooling failures; they are not silently excluded from a claim
of global success. The disk-backed non-backtest retry passed **504 scenarios**,
with four deselected; its failed inode-exhausted predecessor remains archived.

## Current real experiments

Two fresh matrices were prepared and launched from the frozen implementation:

| Matrix | Output directory | Current session |
| --- | --- | --- |
| Baseline, four cells | `build/experiments/20260928-baseline-h4-v1` | parent execution session `71760` |
| GDELT hybrid, four cells | `build/experiments/20260928-hybrid-h4-v1` | parent execution session `44780` |

Hybrid v1 subsequently failed with `ENOSPC` before its last two result directories
could be created and before final checkpoint persistence. Its first two completed
cells are not a completed matrix; stale `backtest_running` statuses are not liveness.
A fresh `20260928-hybrid-h4-v2` used the same code/settings after infrastructure repair.
It finished successfully (session 29828, exit 0), with all four cells `succeeded`
and `final-input-check.json` reporting `ok: true`. Baseline v1 also finished with
parent exit 0 and all four cell/integrity checks passing. **Do not relaunch either.**

Session IDs are assistant-session handles, not operating-system PIDs. On takeover,
read each `execution-started.json` for its PID and check that process's exact command
before deciding it is alive. The existence of the file alone does not prove liveness.
Do not kill another session's or predecessor job's processes.

Every matrix has two workers, six shared LEAN slots, 4 CPU/8 GiB containers and four
training numeric threads. Each cell trains a separate CPU model. Training:
2015-02-02–06-30; combiner calibration: July; evaluation: September 2015. Cash 10,000,
EURUSD/OANDA, H4, Dragon08 risk/exit proxy, spread 1 pip, commission 0. Thresholds and
parameters are fixed before observation; no result-driven retries/tuning.

Each cell's `parameters.md` explains every filter setting and embeds the full plan.
`strategy-config.json`, `strategy-provenance.json`, `source-mapping.md`, XML copies,
`commands.json`, `hashes.json` and `provenance.json` provide the machine-readable join.
Inspect `training.log`, `backtest.log`, `status.json`, then the successful
`results/run.json`, `metrics.json`, statement/equity files and the engine result.

The runner is silent on the terminal while children write their own logs. Check
these files instead of launching a second copy:

```sh
rg --files build/experiments | rg 'status.json|exit-status.json|final-input-check.json|training.log|backtest.log|run.json|metrics.json'
ps -eo pid,ppid,etime,pcpu,args | rg 'spockfx-signals/runner.py|train_.*meta_learner|QuantConnect.Lean.Launcher'
docker stats --no-stream
```

Completion requires the parent `exit-status.json` with exit 0, cell states `succeeded`,
successful final run manifests, and passing `final-input-check.json`. A zero return,
flat curve, zero trades, or failed cell is retained, never omitted. Stop and diagnose
input/contract failures; do not patch archived plans or models. `execute` deliberately
refuses reuse once claimed. If genuinely interrupted, first establish all children
and containers are stopped, preserve the failed archive, and prepare a new versioned
output directory with the same registered settings or an explicitly justified amendment.

Do not edit fingerprinted source/config/test files while these matrices run: batch
checks reject drift. Story documentation and monograph changes are outside the runner's
code fingerprint. Changing a source file requires a new prepared execution snapshot.

## Documentation, commit and consolidation procedure

### Infrastructure failure and recovery

The broad non-backtest workspace command ended with **462 passed, 42 failed, four
deselected** after exhausting `/tmp` inodes. `/tmp` had 44 GiB free but only nine
available inodes out of 1,048,576. This is a failed run, not a global test pass.
The completed run's `/tmp/pytest-of-wellington/pytest-5972` contained 277,963 entries.
It was moved without deletion to
`/home/wellington/workspace/mba-agents/experiment-test-archives/story13-workspace-pytest-5972-inode-failure`.
This preserves failed-test fixtures and freed approximately 278,000 `/tmp` inodes.
No user dataset, old experiment or worktree was removed. Future whole-workspace
tests must use a **fresh disk-backed `--basetemp`**, not `/tmp`, and check `df -i`
as well as `df -h`. Do not reuse the archived failure directory as basetemp.

Hybrid v1 failed for this infrastructure reason, not a parameter-selection result.
Keep it unchanged and report the retry separately. Baseline v1 already had successful
parent/cell manifests and a passing final immutable-input check before exhaustion.

### Perception gate wiring and final coverage

After the experimental snapshots had completed, the `check-perception` target was
extended to include the new bar-clock, candle and activity tests in host coverage,
plus native closed-signal/calendar tests. Otherwise the old DSHA-only host command
would report the newly introduced modules as untested. No model or research setting
changed. The old DSHA `source_wiring.py` receiver also lacked Story 12 ATR/Minimum/
Maximum, pip/account fields and Story 13 minute hooks; supplying those unrelated
collaborators repaired its isolated wiring probe without adding production fallbacks.

Preserved first failure: `build/story13-perception-native` (all nine scenarios used
one failed initializer). Fixed retry: `build/story13-perception-native-fixed`,
**9 passed, 29 deselected in 17.63 seconds**. Host coverage command in the Makefile:
**283 passed, nine deselected**. Merge/check command:

```sh
uv run python tools/perception_quality.py \
  --coverage build/perception-host-coverage.json \
  --native-lines-dir build/story13-perception-native-fixed \
  --merged-coverage build/story13-perception-coverage.json
```

Result: architecture/CRAP **PASS**; all scored perception functions have **100% line
coverage**, maximum CC/CRAP **7**. Host and traced-native coverage are merged exactly
as specified by the pre-existing gate. This is not a claim of complete branch or
mutation coverage. **The full mutation campaign was not rerun in this takeover.**

### Publishing results

All three raw matrix directories (accepted baseline v1, failed hybrid v1, accepted
hybrid v2) are preserved in
[`h4-run-artifacts-20260928T011114Z.tar.gz`](evidence/h4-run-artifacts-20260928T011114Z.tar.gz).
SHA-256: `7bdc1ef9a4ee56706cb74a9c0e8ca0ee27ce24eea79c8afebe76780a78c1cf2c`.
It contains the actual model bytes, effective settings, engine/decision/ledger/equity
outputs, execution logs and integrity manifests—not just screenshots or summaries.
No market/news source dataset is duplicated. `tar -dzf` against the original three
directories verifies archive contents. This archive survives `/tmp` cleanup when
the pushed repository is restored. Extract only into a **fresh directory**, inspect
its relative member names first, and do not execute archived absolute-path commands
blindly; they describe the original run locations, not the extraction destination.

Evidence scripts use workspace source resolution for their isolated strict typing:

```sh
MYPYPATH=algo-analyze/src:algo-backtest/src:algo-core/src \
  .venv/bin/mypy --strict --follow-imports=silent \
  docs/stories/in-progress/13-pattern-volume-experiments/evidence/snapshot_h4_results.py \
  docs/stories/in-progress/13-pattern-volume-experiments/evidence/render_h4_figures.py
```

This passes for both files. Without these paths, mypy reports editable-package stub
discovery errors, not missing runtime libraries. TA-Lib is declared and locked in
the project; no ad hoc Torch/Transformers installation or unsupported NLP input was
introduced. The combined evidence BDD suite currently has **seven passing scenarios**.

Append new result snapshots; do not replace the predecessor evidence. Include full
parameter joins, model/code/input hashes and failures. Report reused-window results
as exploratory, not confirmatory. GDELT events are not article text; no FinBERT or
ModernBERT dependency/fabricated text is part of this experiment.

Use `make verify` from `/tmp/mba-pattern-volume/monografia` after chapter updates.
Record outcome, page count and known warnings; 94-page predecessor update is verified.
Update [progress.md](progress.md) with what/why, agent status, exact new commit and
push status. Stage only reviewed work in this isolated branch, use descriptive
commits and ordinary `git push`; do not merge main or force-push during takeover.
