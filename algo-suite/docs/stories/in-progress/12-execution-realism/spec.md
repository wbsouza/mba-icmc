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
| A | wave 1 | `capital_mgmt` grows `stop_loss_shrink`, `min_stop_factor`, `targets[]` (`at_level_ratio`, `close_fraction`), `trail_stops[]` (`at_level_ratio`, `to_level_ratio`), `min_reward_risk` (null = off), `stop_distance_source` (`fixed`\|`atr`), `atr_multiplier`; new `execution` section (`spread_pips`, `commission_per_lot`, `min_hold_bars`) always resolved with defaults; `strategy-config.yaml` written next to the JSON artifact; YAML, README tables, SPEC |
| B | wave 2 (after A) | F6 builds the full plan from its section — stop pips (fixed or ATR × multiplier, shrunk, floored), lot size, target and trail offsets in pips via `rules/strategy_math`, reward:risk — enriches `trade_plan`, vetoes below `min_reward_risk` |
| C | wave 1 | Fill costs: pip-spread slippage model and per-lot commission fee model applied to the security from the `execution` section; pure math in a typed module with BDD, LEAN adapters call it |
| D | wave 2 (after A, C) | Executor: market order sized from the plan, stop-market and take-profit orders with partial close, trail updates per bar, `min_hold_bars`; opposite signal closes only after plan logic; `size` param dropped for chain strategies |
| E | wave 1 | ATR: `price_features.atr_period`, LEAN ATR subscription, `atr_pips` feature, offline `atr_series` for train/serve parity |
| F | wave 1 | Engine controls and legacy baselines take `--param cash` (closes TD-65); experiment specs updated |
| G | wave 3 | Integration scenarios (stop fill, target partial close, trail move, spread cost), Sept-2015 rerun with A05 values from $10,000, Oct–Nov confirmation, QA script, docs, debt ledger, thesis §3 wording |

## A05 reference values (specs.md §14.7)

risk 3% (pilot uses 0.5%), max concurrent trades 2, stop shrink 20%, min stop 1.2 × broker
stop level, final target 2.0 × SL closing 50%, trail armed at 50% of the way to target
moving the stop to entry − 66% × SL distance, intermediate partial close 50%.

## Out of scope

Structural (swing/breakout) stop levels — the stop distance is fixed pips or ATR here;
F9–F14 extended filters; live trading.
