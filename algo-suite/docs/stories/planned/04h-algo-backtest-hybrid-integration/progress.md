# Progress — Spec 04h (hybrid strategy integration, final)

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
