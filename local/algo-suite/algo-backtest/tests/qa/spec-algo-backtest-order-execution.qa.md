# QA procedure — algo-backtest: order-execution engine

End-to-end verification through the `algo-backtest` CLI only (the tool's user
interface — no direct calls into `algo_backtest.engine.*` Python modules).
Convert each numbered step below into an executable script per
`swarmforge/roles/QA.prompt`; keep the script in lockstep with this file when
either changes.

Executable script: `run_order_execution_qa.py`.

Scope note: this QA procedure covers `engine/order_executor.py`,
`engine/algorithm.py`, and `engine/brokerage/` (Spec 04a, Track A) as migrated
into `baseline-ma`/`baseline-meanrev`. The filter chain (F1–F7) and the hybrid
strategy are a separate, not-yet-landed lane — out of scope here.

Setup common to every section: fresh, empty `ALGO_DATA_ROOT` temp dir;
materialize EUR/USD minute data via `algo-backtest materialize` for the
existing price-swing fixture window used by `run_baseline.feature`
(2014-05-07..09) before running any scenario below.

## 1. Happy path — a BUY order is placed and its fill lands in trades.json

1. Run: `algo-backtest run --strategy baseline-ma --symbol EURUSD --from 2014-05-07 --to 2014-05-09 --param fast=3 --param slow=8 --param size=0.5`.
2. Expect: exit code 0.
3. Expect: `runs/<run-id>/trades.json` exists with at least one closed trade.
4. Expect: that entry's direction is `LONG`, entry/exit prices are both set,
   and the entry timestamp is before the exit timestamp.

## 2. Flat market — no order is placed, no trade record is created

1. Run the same command as §1 over the existing flat-price fixture window
   from `run_baseline.feature`.
2. Expect: exit code 0.
3. Expect: `trades.json` is an empty list and the CLI's reported closed-trade
   count is zero.

## 3. The brokerage model is config-selected, not hardcoded

1. Run the happy-path command from §1 with the default config.
2. Expect: the run's output/log states which brokerage adapter was applied
   (e.g. names "oanda").
3. Re-run with the config's brokerage-adapter key set to an unknown value.
4. Expect: exit code 1 (the adapter is validated during algorithm
   initialization inside the LEAN run, not by CLI pre-flight validation — a
   bad `--strategy`/`--param` is exit 2, this is exit 1) and stderr names the
   invalid adapter — never a silent fallback to a default model.

## 4. baseline-meanrev runs end-to-end through the shared OrderExecutor

`run_baseline.feature` only ever exercised `baseline-ma`, so there is no recorded
pre-migration `baseline-meanrev` ledger to diff against — the OrderExecutor
migration and `baseline-meanrev`'s first automated coverage landed in the same
Spec 04a change. This section instead proves the migration didn't duplicate or
break order-placement logic when both baseline algos were moved onto the shared
engine.

1. Run `baseline-meanrev` over the price-swing fixture window from §1
   (`--param window=5 --param band=0.001 --param size=0.5`).
2. Expect: exit code 0.
3. Expect: `trades.json`'s row count matches the CLI's reported `closed_trades`
   count exactly (the ledger and the report agree — no order silently dropped
   or double-counted).
