# QA procedure — execution realism from the operator's shell

You are a person operating `algo-backtest` and `algo-analyze` from a shell. Prove that a
backtest run from the CLI (a) shows every parameter it will trade with and where each came
from before it starts, (b) turns F7 signals into reference-style trade plans — a stop, a
lot sized from `risk_per_trade`, a partial take-profit, a trailing step, a spread on every
fill — that LEAN actually books, (c) leaves behind a run directory a stranger can audit
without re-running anything, and (d) produces a statement, an equity series and a
self-contained report that other tools consume. Do not judge the strategy by its numbers;
this procedure proves the machinery. A failed step is a defect, not a strategy result.

Prerequisites: a data root with the 2015-09 (and, for step 7, 2015-10) EURUSD minute
lean-data materialized, the frozen F7 models (the 2026-09-26 six-month pilot job:
`data/training/2026-09-26-six-month-pilot/{baseline-f7,hybrid-f7}.json`; a run refuses a
model whose `price_features`/label horizon differ from the strategy's), Docker with the
pinned LEAN image, `ALGO_BROKER__ADAPTER=oanda`, and `ALGO_DATA_ROOT` pointing at that data
root. Every command below is run from `algo-suite/` after `uv sync --all-packages`.

## 1. Explain the strategy before running anything

    uv run algo-backtest explain-strategy baseline
    uv run algo-backtest explain-strategy hybrid

Look at: one line per resolved parameter, `key = value  # <source>`, sorted by key. For
`baseline` the `capital_mgmt.*` lines must show the reference plan — `risk_per_trade = 0.03`,
`stop_loss_shrink = 0.2`, `min_stop_pips = 5.0`, `min_stop_factor = 1.2`,
`targets = [{"at_level_ratio": 2.0, "close_fraction": 0.5}]`,
`trail_stops = [{"at_level_ratio": 0.5, "to_level_ratio": -0.66}]`, `min_reward_risk = 2.0`,
`stop_distance_source = "swing"` — and the `execution.*` lines `spread_pips = 1.0`,
`commission_per_lot = 0.0`, `min_hold_bars = 0`, `broker_stop_level_pips = 0.0`,
`close_on_veto = false`. For `hybrid` the same F5/F6/F7 and `execution` lines end in
`# baseline/config.yaml` (inherited through `extends:`) while `news_context.*` ends in
`# hybrid/config.yaml`.

Pass: every line ends in `# <name>/config.yaml` or `# default`; no `# unknown`; the values
above are printed verbatim; `hybrid` and `baseline` differ only in `filters`,
`meta_learner.families` and the `news_context` section.

## 2. Run a strategy from a $10,000 account

    uv run algo-backtest run --strategy baseline --symbol EURUSD \
      --from 2015-09-01 --to 2015-09-30 --param cash=10000 \
      --model data/training/2026-09-26-six-month-pilot/baseline-f7.json

Look at, in order:

1. The bootstrap parameter print — the `explain-strategy` lines again, prefixed
   `strategy[baseline] `, printed before any data check or container start. This is the
   auditable record of what the run will trade with.
2. `run[baseline]: success=True closed_trades=<n> results=<dir>/main.json`.
3. `metrics: total_return=… sharpe=… max_drawdown=… hit_rate=…`.
4. `statement: Previous Ledger Balance: 10,000.00` … `statement: Equity: …` (the A/C
   Summary lines), then the four paths `statement: …/statement.md`,
   `equity chart: …/equity.png`, `equity csv: …/equity.csv`, `report: …/report.html`.

Pass: the bootstrap print appears before `run[...]`; `success=True`; `closed_trades`
greater than zero; `Previous Ledger Balance` is exactly `10,000.00`; the four statement
paths are inside the printed run directory. A `--param size=…` must be rejected with exit
code 2 (`baseline params must be exactly ['cash']`): position size is not a run parameter
any more.

## 3. Inspect the run directory

    ls data/runs/baseline/<stamp>/
    uv run python -m json.tool data/runs/baseline/<stamp>/trade-plans.json | head -60
    grep -E "BASELINE_(STARTING_CASH|FILL_COSTS|PLAN\||TRAIL|OCO_CANCEL|STOP_RESIZE)" \
      data/runs/baseline/<stamp>/log.txt | head -20

Look at:

- Files: `run.json`, `main.json`, `main-order-events.json`, `trades.json`, `metrics.json`,
  `inference-inputs.json`, `decisions.parquet`, `strategy-config.json`,
  `strategy-config.yaml`, `strategy-provenance.json`, `trade-plans.json`, `statement.md`,
  `equity.png`, `equity.csv`, `report.html`, `log.txt`.
- `strategy-config.yaml` is the fully resolved config (no `extends:`), the same document as
  `strategy-config.json`; `strategy-provenance.json` maps every dotted parameter path to
  `baseline/config.yaml` or `default`.
- `trade-plans.json`: one record per planned entry with `entry_order_id`, `entry_time`,
  `direction`, `lots`, `quantity`, `entry_price`, `stop_loss`, `take_profits`
  (`price`, `close_fraction`, `quantity`), `trail_stops` (`at_level_ratio`,
  `to_level_ratio`, `at_price`, `to_price`) and `spread_pips`. For a `buy`, `stop_loss` is
  below `entry_price` by at least 5 pips (`min_stop_pips`), the single take-profit is above
  it with `close_fraction` 0.5 and a `quantity` of half the position with the opposite sign,
  the trail's `to_price` is between the stop and the entry, `spread_pips` is 1.0, and
  `lots × 100000` equals `|quantity|` to within one unit.
- `log.txt`: one `BASELINE_STARTING_CASH=10000.0` line; a
  `BASELINE_FILL_COSTS|model=slippage|…` line (plus a `model=fee` line only when
  `commission_per_lot` > 0); one
  `BASELINE_PLAN|entry=…|lots=…|quantity=…|stop=…|targets=[…]` line per record of
  `trade-plans.json`; `BASELINE_TRAIL|…` when a trailing step armed, `BASELINE_OCO_CANCEL|…`
  when a stop or target filled and the rest was cancelled, `BASELINE_STOP_RESIZE|…` after a
  partial take-profit.

Pass: every file listed is present; the plan records satisfy the geometry above; the
number of `_PLAN|` lines equals the number of records; `trades.json` is non-empty and each
trade's `orderIds[0]` is an `entry_order_id` of a record.

## 4. Read the statement

    sed -n 1,40p data/runs/baseline/<stamp>/statement.md

Look at: the header `A/C No: <stamp>   Name: baseline / EURUSD   <period end>`; the
Closed Transactions table — `Lots` filled (not `—`), `S / L` and `T / P` filled from the
plan (a run without plans would say so explicitly), `Commission` `0.00` because
`commission_per_lot` is 0, a totals row; the A/C Summary block with
`Previous Ledger Balance 10,000.00`, `Balance = 10,000.00 + Closed Trade P/L`, `Equity`
and, beneath, the engine-reported equity for reconciliation; the Parameters section with
a `Source` column reading `baseline/config.yaml` or `default`, and `cash` from `--param`.

Pass: the header names the run; every closed row has a ticket, lots, S / L and T / P;
balance arithmetic holds to the cent; no parameter's source is `unknown`.

## 5. Open the performance dashboard

    xdg-open data/runs/baseline/<stamp>/report.html   # or open it in any browser via file://

Do it with the network off (or the browser's developer tools showing no request).

Look at: six account cards (Balance, Equity with the net % since start, Floating P/L,
Margin Used, Free Margin, Leverage `1:30` — `capital_mgmt.assumed_leverage`), the equity
curve with a dashed starting-deposit line at 10,000, six performance cards, and the five
tabs — Equity, Drawdown, Monthly Returns, Trade History (the same rows as the statement's
Closed Transactions), Parameters (the provenance table).

Pass: the page renders and every tab switches with the network off; `grep -ci "<script"
report.html` prints 0 and `grep -cE "https?://" report.html` prints 0; the Trade History
row count equals `closed_trades`; the Leverage card reads `1:30`.

## 6. Regenerate the statement artifacts from the run directory

    uv run algo-backtest statement --run data/runs/baseline/<stamp> --out /tmp/regen
    diff <(grep -v '^Period:' data/runs/baseline/<stamp>/statement.md) \
         <(grep -v '^Period:' /tmp/regen/statement.md) && echo "statement identical"
    cmp data/runs/baseline/<stamp>/equity.csv /tmp/regen/equity.csv && echo "equity.csv identical"
    head -3 /tmp/regen/equity.csv

Look at: the same A/C summary lines as step 2; `/tmp/regen/` holding `statement.md`,
`equity.png`, `equity.csv`, `report.html`; `equity.csv` starting
`time,equity,drawdown_pct` with a first row at equity `10000.0` and drawdown `0.0`.

Pass: `statement identical` (only the `Generated:` timestamp on the `Period:` line may
differ) and `equity.csv identical`; the regeneration touched no LEAN container. Pointing
`--run` at a directory without `run.json` must exit 2 naming the missing file.

## 7. Consolidate two runs

Run a second window (or the `hybrid` strategy over the same window with
`hybrid-f7.json`), then:

    uv run algo-backtest run --strategy baseline --symbol EURUSD \
      --from 2015-10-01 --to 2015-10-31 --param cash=10000 \
      --model data/training/2026-09-26-six-month-pilot/baseline-f7.json
    uv run algo-analyze equity-curves --run data/runs/baseline/<sep-stamp> \
      --run data/runs/baseline/<oct-stamp> --out /tmp/curves
    head -3 /tmp/curves/equity-consolidated.csv

Look at: one `equity-curves: <strategy> …` summary line per strategy (first equity, last
equity, chained net %, max drawdown %), then the three paths. The CSV columns are
`strategy, run_id, time, equity_raw, equity_chained, drawdown_pct`; for the October rows
`equity_raw` restarts at 10,000 while `equity_chained` continues from September's last
value. Open `equity-consolidated.html` with the network off: one line per strategy, a KPI
card per strategy, a dotted marker where October was chained on.

Pass: exit code 0; `equity-consolidated.{csv,png,html}` exist; September and October form
one continuous chained line; a directory without `equity.csv` makes the command exit 2
naming the `algo-backtest statement --run` command that creates it.

## 8. Run the deterministic gate

    uv run python docs/stories/done/12-execution-realism/evidence/qa_check.py \
      data/runs/baseline/<sep-stamp> data/runs/baseline/<oct-stamp>

Look at: one `[PASS]`/`[FAIL]` line per check under each run directory, a
`== consolidated` block with the `equity-curves` check, and the final `QA:` line. The checks
per run: `strategy-config.json present`, `strategy-config.yaml matches strategy-config.json`,
`provenance sources are config.yaml or default`, `trade-plans.json present`, `plan stop
distance within capital_mgmt bounds` (the floor `max(min_stop_pips, min_stop_factor ×
broker_stop_level_pips)`; exact for a `fixed` source — the bundled `swing` source's base is
a bar feature, so only the floor is checked), `plan targets match capital_mgmt.targets`,
`plan trail steps match capital_mgmt.trail_stops`, `plan spread equals
execution.spread_pips`, `plan entry orders join the LEAN result`, `plan lots match
quantity`, `position risk within risk_per_trade` (lots × stop pips × pip value against
`risk_per_trade` × the balance at entry, 5 % slack by default: `--risk-tolerance`),
`concurrent positions within risk_guard cap`, the three `… present` checks, `equity.csv
starts at cash` and `report.html self-contained`.

Options: `--pip-size 0.0001` when the fill prices do not fix the quote precision,
`--lot-step` for a broker with a coarser order step than OANDA's one unit,
`--analyze-out DIR` to keep the consolidated files.

Pass: exit code 0 and `QA: PASS`. Record both run IDs, the model SHA-256 lines from
`log.txt` (`BASELINE_MODEL_SHA256=…`) and the printed check table in the story's
`progress.md`.
