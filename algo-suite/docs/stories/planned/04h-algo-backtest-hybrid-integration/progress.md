# Progress — Spec 04h (hybrid strategy integration, final)

## Update (2026-09-26, later same session): the "baseline" chain now runs for real

`algos/baseline/main.py` now exists and runs the full F1+F2+F3+F5+F6+F7 chain (no F4)
against the real pinned LEAN container, verified two ways:

1. **New integration test** (`tests/features/run_baseline_chain.feature` +
   `tests/steps/test_run_baseline_chain.py`, `@integration`): the chain runs to
   completion against a synthetic price swing, exits successfully, produces a metrics
   summary and full run artifacts. Passing, alongside 2 new fast CLI-validation
   scenarios. All existing `run_baseline.feature`/`order_execution.feature` integration
   tests (11 scenarios) still pass unchanged.
2. **Real run**: `algo-backtest run --strategy baseline --symbol EURUSD --from
   2015-02-02 --to 2015-02-06 --param size=0.5` against the real materialized 2015-02
   Dukascopy data — `success=True`, `closed_trades=0` (F7's threshold rule never
   triggered BUY/SELL in this window; a legitimate outcome, not a bug — see below), PDF
   equity/drawdown reports generated via `algo-analyze figures`.

**This is still a wiring smoke test, not a methodology result** (per this file's own
established framing — see `main.py`'s own module docstring for the full list): F3's
candlestick pattern is never populated, F5/F6's account-risk features use fixed
placeholder economics, and F7's meta-learner is trained by the new
`scripts/train_baseline_meta_learner.py` on whatever short window it's pointed at (this
run: `2015-02` split train/validation/test across trading days only, since weekends
have no FX data) — not a statistically meaningful model. Zero closed trades over 5 days
is consistent with a conservative/undertrained threshold rule, not evidence of a crash.

**New real gap found and fixed along the way**: `run_lean()` only ever copied
`algo_backtest/engine/` into the container -- a chain-based algorithm additionally needs
`algo_backtest.chain.*`/`rules.*`/`strategies.py` and `algo_core` itself, none of which
the pinned image ships. `lean_runner.py` now also copies those two packages in,
alongside `engine/`, using the exact same pattern. `algos/baseline/main.py` also could
not call F5/F6/F7's own `load_*_config()` (would fail fast inside the container --
nothing mounts `conf/` there, and TD-43's per-caller schema isolation means adding those
keys to `conf/backtest.yaml` would have broken every other `algo-backtest` command on
the host); it builds their config from explicit in-code placeholder constants instead.

**Still not done** (the real remaining gap, narrower than before): F4/news wiring (the
`hybrid` strategy, not `baseline`), a statistically meaningful F7 model trained on the
full materialized window once it finishes, and moving this story to `done/` (its real
Definition of Done — a `hybrid` run — still isn't met by a `baseline`-only smoke test).

## Session handoff (2026-09-26)

**Verified today, no longer a blocker:** the pinned `quantconnect/lean:17748` image's
Python package set (cited below as "unverified" and the reason this pass deferred the
LEAN-container work) is confirmed present: `pyarrow==19.0.1`, `lightgbm==4.6.0`,
`scikit-learn==1.6.1`, `joblib==1.5.3` (checked via
`docker run --rm --entrypoint python3 quantconnect/lean:17748 -c "import ..."`). No
package install needed — F4's Parquet read and F7's model load/serialize can proceed
directly inside the container as designed.

**Also changed this session** (context for whoever picks this up next):
- GDELT Events real data materialization is in progress (`bigquery_ctas_export_gdelt_events.py`,
  rewritten to per-date queries + per-day Parquet writes this session — see PR #31).
  Running on a second machine with local NVMe now, several months already `.done`
  (`2020-01`, `2015-02`, `2015-03` confirmed; more in progress).
- GDELT GKG ingestion + events⋈gkg join is **on hold for V2** (not needed for this
  delivery) — see `docs/technical-debt.md` TD-53 and PR #32. Don't wait on GKG data to
  start the LEAN-container work below; F4 only needs the Events-derived features.
- `algo-score events --kind gdelt` (raw Events → the feature Parquet F4 actually reads)
  has only ever been run for `2020-01`. Needs re-running per month as the raw
  materialization above finishes each one, before F4 has real signal for those months.
- GPR lane (`algo-download run --source gpr` → `algo-transform run --source gpr` →
  `algo-score events --kind gpr`) has never been run at all — needed for the coverage
  rule's "≥2 corpora active" requirement, independent of the GDELT lane.

## Concrete next-session TODO (in dependency order)

**Operator decision (2026-09-26): scope the first test small — one week of `2015-02`, not
the whole window — to see how it goes before committing to more.** `2015-02`'s raw Events
Parquet is already `.done`, so this is runnable immediately, no waiting on the background
materialization. The exact command to start with (queued but not yet run this session —
picking this up is literally the first action for the next session):

```
cd algo-suite && uv run algo-score events --kind gdelt --from 2015-02-01 --to 2015-02-07
```

This only tests the event-feature extraction stage (raw Events -> the feature Parquet F4
reads) — it is NOT a backtest and won't be until item 5 below (`algos/baseline`/`hybrid`
main.py) exists. Confirm this step produces real, sane feature output for the one-week
window before deciding whether to widen it to the rest of `2015-02` or the full window.

1. Backfill event features: `algo-score events --kind gdelt --from 2015-02 --to <window-end>`
   once each month's raw Events Parquet lands (`.done` marker present).
2. Run the GPR lane end-to-end (download → transform → event features) — currently
   entirely unrun.
3. Run `algo-transform coverage` against real data; confirm the reported training window
   actually starts at/near 2015-02 as expected.
4. Serialize `train_meta_learner()`'s fitted models (`joblib.dump`) and decide the mount
   path into the LEAN container (volume mount, same pattern as `lean-data/`).
5. Write `algos/baseline/main.py` / `algos/hybrid/main.py` (the actual remaining item
   below) — LEAN-native indicator wiring for F1-F3, `self.portfolio` for F5/F6, the news
   feature Parquet for F4, the persisted meta-learner for F7, `decision_to_order_action`
   from `chain/terminal.py` driving `OrderExecutor`.
6. Run `algos/experiment_zero/*` and the two chain algos against the real container
   (`tests/features/order_execution.feature`'s pattern), thread a real `trade_id` from
   `OrderExecutor` into `decisions.parquet`.
7. Then, and only then, move `04-algo-backtest-filter-chain-hybrid/` to `done/` with a
   `lessons-learned.md`, per the last item below.

- [x] Wire F7 terminal step to `OrderExecutor` (04a) — `chain/terminal.py`'s
      `F7TerminalDecision` (reads F7's own `FilterResult` as the chain's `Decision`) +
      `decision_to_order_action` (classifies a `Decision` into execute/manage/stand_aside
      for a LEAN algorithm's `on_data()` to switch on). Pure Python, proven against the
      real F1-F7 chain end-to-end (`tests/features/filter_chain_mechanics.feature`'s new
      Rule). **Not done:** actually calling `OrderExecutor` from inside a running LEAN
      algorithm — that needs `algos/{baseline,hybrid}/main.py`, which don't exist yet
      (see the last item below and `docs/technical-debt.md` TD-51).
- [x] `baseline`/`hybrid` strategy YAML via `extends:` composition —
      `src/algo_backtest/strategies/{baseline,hybrid}/config.yaml` +
      `algo_backtest/strategies.py`'s single-level `extends:` loader (TD-8's explicitly
      scoped exception: a base may not itself declare `extends:`).
- [x] Experiment 0 — buyhold/random/perfect_foresight known-answer strategies —
      `algos/experiment_zero/{buyhold,random,perfect_foresight}/main.py` written to the
      exact proven `baseline_ma`/`baseline_meanrev` pattern, registered in `run.py`'s
      `STRATEGIES` with real Gherkin-covered param validators. **Not run against the real
      LEAN container this pass** (see below).
- [ ] End-to-end integration test: `algo-backtest run --strategy hybrid --symbol EURUSD` —
      **not done.** `run.py`'s `STRATEGIES` has no `"baseline"`/`"hybrid"` entry: that
      needs `algos/baseline/main.py`/`algos/hybrid/main.py` reading a strategy's
      `config.yaml` and populating `ExecutionState.features` each bar from live
      LEAN-native indicators (F1-F3), `self.portfolio` (F5/F6), the real news Parquet
      (F4), and a persisted meta-learner artifact (F7) — the single largest remaining
      engineering surface in `algo-backtest`. Deliberately deferred this pass: the
      pinned LEAN image is ~10 GB, `pyarrow`/`lightgbm`/`scikit-learn` availability
      inside it is unverified, and pulling/running it risked NAS I/O contention with the
      concurrent, unrelated 10-year FX price backfill running in the original working
      tree during this session. See `docs/technical-debt.md` TD-51 for the itemized
      remaining scope.
- [ ] `decisions.parquet` joins `trades.parquet` by `trade_id` (end-to-end check) — **not
      done**, blocked on the item above (no strategy drives the chain end-to-end yet, so
      there is no real run to join). Also note: the real ledger today is `trades.json`
      (TD-47 already corrected `SPEC.md` §6.1's stale `trades.parquet` plan) — the actual
      join target for a future check is `trades.json`, not `trades.parquet` as originally
      worded in this checklist item.
- [x] Mermaid filter-chain diagram per strategy README —
      `src/algo_backtest/strategies/{baseline,hybrid}/README.md`.
- [x] Update `algo-backtest/SPEC.md`, `00-PLAN.md` §1, `ch04-deliverables.md` — all three
      updated to describe F4/F7/`chain/terminal.py`/`strategies.py` as built, and to
      honestly scope the remaining LEAN-container wiring as the one open item.
- [ ] Move `04-algo-backtest-filter-chain-hybrid/` (+ lanes) to `done/`, add
      `lessons-learned.md` — **deliberately not done.** The parent story's real
      Definition of Done (a LEAN-container hybrid run producing `decisions.parquet` +
      `trades.json`) is not met; moving it to `done/` would misrepresent status to future
      readers. Revisit once TD-51's remaining scope lands.
- [x] `make check` green (algo-backtest + algo-score scoped: see final report for count);
      `make audit` — see final report.
- [x] Gauntlet (differential mutmut, `uncle-bob-agent-gauntlet`): 112/122 killed (91.8%)
      after adding boundary/edge scenarios for `chain/terminal.py` and `strategies.py`
      (empty `filter_results`, `decision_to_order_action` coverage, non-mapping config,
      missing-vs-empty `filters`, a real `_deep_merge` `and`→`or` gap, missing-`families`-
      key, default-root-parameter coverage). Remaining 10 survivors: 8 message-text
      canaries (TD-34/36/40/49 class, new row TD-52) + 2 confirmed-equivalent mutants on
      an unobservable default-value substitution.
