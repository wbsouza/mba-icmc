# Runbook: running the `baseline` F1-F7 chain (2026-09-26)

Covers `algos/baseline/main.py` (PR #33) — the F1+F2+F3+F5+F6+F7 chain (no F4/news)
wired into a real LEAN algorithm. **This is a wiring smoke test, not a methodology
result** — see `progress.md`'s 2026-09-26 sections and `docs/technical-debt.md`'s TD-51
for the full list of known simplifications before citing any number this produces.

## 1. Train and persist the F7 meta-learner (once, or whenever the window changes)

```bash
cd algo-suite/algo-backtest
uv run python scripts/train_baseline_meta_learner.py \
    --symbol EURUSD --year 2015 --month 2 \
    --train-end 2015-02-03 --validation-end 2015-02-05 --test-end 2015-02-06
```

Writes `src/algo_backtest/algos/baseline/f7_meta_learner.joblib`, loaded by `main.py` at
`initialize()`. Boundaries must fall on real trading days — FX markets are closed
weekends, so a span landing entirely on a Saturday/Sunday raises `ValueError` (empty
walk-forward span).

## 2. Run the backtest

```bash
cd algo-suite
uv run algo-backtest run --strategy baseline --symbol EURUSD \
    --from 2015-02-02 --to 2015-02-06 --param size=0.5
```

Prints `run[baseline]: success=... closed_trades=... results=<path>/main.json` plus a
`metrics:` line. `closed_trades=0` is a valid outcome (F7's threshold rule is
conservative), not a failure — check `<results_dir>/log.txt` for `BASELINE_DECISION|...`
lines to confirm the chain actually evaluated every bar (this is exactly what
`run_baseline_chain.feature`'s `@integration` scenario asserts automatically).

## 3. Generate the PDF report

```bash
uv run algo-analyze figures --run baseline/<run-id>
```

Writes `equity.pdf` and `drawdown.pdf` under `<results_dir>/figures/`.

## Sequence diagram: one `run` invocation, end to end

```mermaid
sequenceDiagram
    actor Op as Operator
    participant CLI as algo-backtest CLI
    participant Run as run.py
    participant Lean as lean_runner.run_lean()
    participant Docker as LEAN container
    participant Algo as algos/baseline/main.py
    participant Chain as FilterChain (F1-F7)
    participant Exec as OrderExecutor

    Op->>CLI: algo-backtest run --strategy baseline ...
    CLI->>Run: validate_run_inputs() + run_strategy()
    Run->>Run: check lean-data covers the window
    Run->>Lean: run_lean(algo_dir, results_dir, data_mounts, parameters)
    Lean->>Lean: copy engine/, algo_backtest/, algo_core/ into work dir
    Lean->>Docker: mount work dir at /LeanCLI, start container
    Docker->>Algo: Initialize()
    Algo->>Algo: load f7_meta_learner.joblib, build FilterChain
    loop every minute bar
        Docker->>Algo: OnData(slice)
        Algo->>Algo: build ExecutionState.features (live indicators + portfolio)
        Algo->>Chain: chain.run(state)
        Chain-->>Algo: ChainOutcome(decision)
        Algo->>Algo: debug("BASELINE_DECISION|...")
        alt decision is BUY or SELL
            Algo->>Exec: execute(symbol, decision, sizing)
            Exec->>Docker: market_order() / liquidate()
            Docker-->>Exec: OnOrderEvent
        end
    end
    Docker->>Algo: OnEndOfAlgorithm()
    Algo->>Algo: debug("BASELINE_CLOSED_TRADES=n")
    Docker-->>Lean: exit code + logs, /Results/main.json
    Lean-->>Run: LeanRun(exit_code, logs, results_dir)
    Run-->>CLI: RunResult (parsed main.json)
    CLI-->>Op: run[baseline]: success=... closed_trades=...\nmetrics: ...
    Op->>CLI: algo-analyze figures --run baseline/<run-id>
    CLI-->>Op: equity.pdf, drawdown.pdf
```

## State diagram: per-bar decision flow

```mermaid
stateDiagram-v2
    [*] --> WaitingForWarmup
    WaitingForWarmup --> Evaluating: all indicators ready\n(EMA fast/slow/htf, RSI, MACD)
    WaitingForWarmup --> WaitingForWarmup: bar arrives, not ready yet

    state Evaluating {
        [*] --> F1
        F1 --> F2: no veto
        F1 --> Vetoed: direction conflict
        F2 --> F3: (never vetoes)
        F3 --> F5: (never vetoes)
        F5 --> F6: no veto
        F5 --> Vetoed: risk cap breached
        F6 --> F7: no veto
        F6 --> Vetoed: insufficient margin
        F7 --> Terminal: threshold rule (p_hat vs theta_high/theta_low, regime)
    }

    Evaluating --> Deciding: chain.run() returns ChainOutcome

    state Deciding {
        [*] --> CheckDecision
        CheckDecision --> Execute: BUY or SELL
        CheckDecision --> Manage: HOLD
        CheckDecision --> StandAside: NO_TRADE (vetoed)
    }

    Execute --> PositionOpen: OrderExecutor.execute() fills
    Manage --> PositionOpen: leave open position alone
    Manage --> Flat: no open position
    StandAside --> PositionOpen: leave open position alone
    StandAside --> Flat: liquidate if invested

    PositionOpen --> WaitingForWarmup: next bar
    Flat --> WaitingForWarmup: next bar
    WaitingForWarmup --> [*]: OnEndOfAlgorithm (BASELINE_CLOSED_TRADES emitted)
```

## Known limitations (repeat of `progress.md`/TD-51, kept here for a runbook reader)

- F3's `candlestick_pattern` is always `None` — no real detector wired; F3 ABSTAINs every bar.
- F5/F6's account-risk features (`account_portfolio_at_risk`, `pip_value`,
  `stop_loss_pips`, `margin_per_lot`, ...) use fixed placeholder constants in
  `algos/baseline/main.py`, not a real ATR/margin model.
- F7's meta-learner is fit on whatever short window `train_baseline_meta_learner.py` is
  pointed at — mechanically valid, not statistically meaningful.
- `hybrid` (F1-F7 + F4/news) has no `algos/hybrid/main.py` yet — this runbook covers
  `baseline` only.
