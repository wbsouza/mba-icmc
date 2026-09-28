# QA procedure — September-2015 replay on the amended chain

You are a person operating `algo-backtest` from a shell. Prove that the amended chain
(filter parameters in `config.yaml`, F7 regime gate off, $10,000 account) produces
buy and sell decisions that become real trades in the LEAN simulation, and that every
parameter the run used is auditable from its artifacts. Do not look at the numbers to
judge the strategy; this procedure only proves the machinery.

Prerequisites: the 2026-09-26 pilot job data root (`data/training/2026-09-26-six-month-pilot/data`,
with 2015-02..09 canonical GDELT months linked and 2015-02..10 event features built), the
frozen models `baseline-f7.json` / `hybrid-f7.json` in that job directory, Docker with the
pinned LEAN image, `ALGO_BROKER__ADAPTER=oanda`.

1. Run, from `algo-suite/`, with `ALGO_DATA_ROOT` pointing at that data root:

       .venv/bin/algo-backtest run --strategy baseline --symbol EURUSD --from 2015-09-01 --to 2015-09-30 \
         --param cash=10000 --model data/training/2026-09-26-six-month-pilot/baseline-f7.json
       .venv/bin/algo-backtest run --strategy hybrid   --symbol EURUSD --from 2015-09-01 --to 2015-09-30 \
         --param cash=10000 --model data/training/2026-09-26-six-month-pilot/hybrid-f7.json

   Each prints `run[<strategy>]: success=True closed_trades=<n>` and the results path.
   Expected: `success=True` and `closed_trades` greater than zero for both.

2. Open the run folder printed (`data/runs/<strategy>/<stamp>/`). Check by eye:
   - `strategy-config.json` shows `meta_learner.regime_gate: false`, `theta_high: 0.55`,
     `theta_low: 0.45`, and the `risk_guard` / `capital_mgmt` (and, for hybrid,
     `news_context`) sections with the values from the bundled `config.yaml`.
   - `log.txt` contains one `<TAG>_STARTING_CASH=10000.0` line and both
     `decision=BUY` and `decision=SELL` lines.
   - `trades.json` is a non-empty list.
   - `main.json` → `statistics` → `Start Equity` is `10000.00` and `End Equity` differs
     from it; `charts` → `Strategy Equity` → `series` → `Equity` → `values` is not flat.
   - `decisions.parquet` has rows with `final_decision` BUY and SELL, and at least one row
     whose `trade_id` is not null.

3. Run the deterministic check over both run folders (exit code 0 = PASS):

       .venv/bin/python docs/stories/done/09-six-month-training-september-pilot/evidence/qa_check.py \
         --cash 10000 data/runs/baseline/<stamp> data/runs/hybrid/<stamp>

4. Record both run IDs, the printed check table and the two model SHA-256 hashes in the
   story's `progress.md`. A failed step is a defect in the machinery, not a strategy result.
