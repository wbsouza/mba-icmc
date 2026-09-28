# Story 12 — Execution realism: fx-manager money management wired to orders

**Decision (2026-09-27, with the user):** make the `capital_mgmt` parameters real. Today F6
computes a lot size the executor ignores, no stop or target order is ever placed
(TD-46), fills carry Dukascopy's ~0.3-pip ECN spread with $0 fees, and `size=0.5` bets
50% of equity as notional. The September-2015 replay (story 09) therefore proves the
machinery, not the economics.

## Goal

Each F7 signal becomes an fx-manager-style trade plan (specs.md §14.5–14.7, strategy
A05): stop first, lot from `risk_per_trade` and the stop distance, targets as multiples
of the stop distance with the spread added, partial close at the intermediate target,
trailing stop armed and moved by factors of the stop distance, a minimum reward:risk
before entry, realistic spread and commission on every fill. Every number is a YAML
parameter with provenance; nothing is a code constant.

## Scope (one PR, parallel waves)

| Item | Owner | Deliverable |
|---|---|---|
| A | wave 1 | `capital_mgmt` grows `stop_loss_shrink`, `min_stop_pips`, `min_stop_factor`, `targets[]` (`at_level_ratio`, `close_fraction`), `trail_stops[]` (`at_level_ratio`, `to_level_ratio`), `min_reward_risk` (null = off), `stop_distance_source` (`fixed`\|`atr`\|`swing` — `swing` added in wave 2, see below), `atr_multiplier`; new `execution` section (`spread_pips`, `commission_per_lot`, `min_hold_bars`, `broker_stop_level_pips`, `close_on_veto`) always resolved with defaults; `strategy-config.yaml` written next to the JSON artifact; YAML, README tables, SPEC |
| B | wave 2 (after A) | F6 builds the full plan from its section — stop pips per side (fixed, ATR × multiplier, or the structural swing low/high distance over `price_features.swing_lookback_bars`; shrunk, then floored by `max(min_stop_pips, min_stop_factor × execution.broker_stop_level_pips)`), lot size from the wider stop, target and trail offsets in pips via `rules/trail_stop`, reward:risk — enriches `trade_plan`, vetoes below `min_reward_risk` |
| C | wave 1 | Fill costs: pip-spread slippage model and per-lot commission fee model applied to the security from the `execution` section; pure math in a typed module with BDD, LEAN adapters call it |
| D | wave 2 (after A, C) | Executor: market order sized from the plan, stop-market and take-profit orders with partial close (one-cancels-the-others), trail updates per bar, `min_hold_bars` before an opposite signal may reverse, `close_on_veto` (default false); `trade-plans.json` per run; `size` param dropped for chain strategies |
| E | wave 1 | ATR: `price_features.atr_period`, LEAN ATR subscription, `atr_pips` feature, offline `atr_series` for train/serve parity |
| F | wave 1 | Engine controls and legacy baselines take `--param cash` (closes TD-65); experiment specs updated |
| G | wave 3 | Integration scenarios (stop fill, target partial close, trail move, spread cost), Sept-2015 rerun with A05 values from $10,000, Oct–Nov confirmation, QA script, docs, debt ledger, thesis §3 wording |
| H | wave 1 | End-of-run broker-style `statement.md` + `equity.png`; `algo-backtest statement --run` regenerates them for any finished run |
| H2 | wave 1 | `report.html`: self-contained "Account Performance" dashboard beside the statement |
| H3 | wave 1 | `equity.csv` per run; `algo-analyze equity-curves` chains several runs per strategy into `equity-consolidated.{csv,png,html}` |

## A05 reference values (specs.md §14.7)

risk 3% (pilot uses 0.5%), max concurrent trades 2, stop shrink 20%, min stop 1.2 × broker
stop level, final target 2.0 × SL closing 50%, trail armed at 50% of the way to target
moving the stop to entry − 66% × SL distance, intermediate partial close 50%.

## Out of scope

F9–F14 extended filters; live trading. Structural (swing) stop levels were listed here
originally; they shipped in wave 2 as `stop_distance_source: swing` (the distance to the
rolling swing low/high over `price_features.swing_lookback_bars`, A05's structural
template stop) and are `baseline`'s default. Breakout-level stops remain out of scope.

## Registered protocol (2026-09-27, with the user) — decided before any 2016 bar is simulated

GDELT 2.0 collection starts 2015-02-18, so February 2015 is thin; the first fully
collected month is March 2015. The main experiment uses one complete collected year:

| Span | Use |
|---|---|
| 2015-03-02 → 2015-12-31 | family models (LightGBM) |
| 2016-01-01 → 2016-01-31 | combiner calibration; threshold grid recorded |
| 2016-02-01 → 2016-02-29 | trainer's held-out partition, no replay |
| 2016-03-01 → 2016-10-31 | one continuous simulation per strategy, $10,000, A05 plan; both strategies run in parallel |

Amendment (2026-09-27, evening): October 2016 finished ingesting before the job's first
stage completed, so the simulation window was extended from 2016-09-30 to 2016-10-31 —
still before any 2016 bar was simulated. GDELT event features are built through
2016-11-01 so the last October bar's decision minute is covered. The training,
calibration and held-out spans are unchanged.

Pre-registered threshold rule: keep θ = 0.55/0.45 with the regime gate off unless the
January-2016 validation hit rate at 0.55/0.45 is below 0.5; the full grid is recorded
either way (`threshold-calibration.json`). The Sept–Nov 2015 rerun with the frozen
2026-09-26 six-month models is the pilot check of the execution machinery, not the
experiment. Job scripts: `data/training/2026-09-27-execution-realism/run.sh` and
`data/training/2026-09-28-one-year-protocol/run.sh` (local, gitignored).

## Execution decisions taken during integration

- `execution.close_on_veto` defaults to **false**: with true, every planned trade in the
  sine-cycle fixture was closed one minute after entry by F1's direction-conflict veto,
  cancelling its stop and targets. A05 did not close on a signal change (only its
  USD/JPY variant did); the stop, targets, trail and `min_hold_bars` govern exits.
- Stop and limit orders carry no tag: the pinned LEAN image cannot bind
  `StopMarketOrder(Symbol, float, float, str)` from Python; the plan log lines identify
  the orders instead (TD-66).
- The planned-stop integration scenario (`run_baseline_chain.feature`, "planned stop
  fills at the configured distance") uses a **1-pip fixed stop**, not the A05 distance:
  the sine fixture's ask peaks only 1.5 pips above the short entry the model takes at the
  sine top (the entry slips half the 1-pip spread), so a 2-pip stop would never be
  touched within the two-day span. Shrink and floors are zeroed in that variant and the
  exit is asserted within 2 pips of the planned stop (the exit slips the other half
  spread). The A05 values themselves are exercised by the target, trail and spread
  scenarios with 4- and 10-pip stops.
- Every planned entry is recorded in the run's `trade-plans.json`, which the statement
  joins to `trades.json` by `orderIds[0]` for the S/L and T/P columns.
