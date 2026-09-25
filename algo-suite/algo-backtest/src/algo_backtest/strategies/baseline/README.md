# Strategy: `baseline`

Price-only. Docs/experiments.md Experiment 1: calibrate the price-only baseline on
EUR/USD. Feature families scored by the meta-learner: trend (F1), indicator (F2),
pattern (F3) — no news family. Config: [`config.yaml`](config.yaml).

```mermaid
flowchart TB
    Start([Bar tick])
    F1["F1 — Trend-regime filter<br/>reads trend_direction, trend_strength,<br/>higher_tf_trend_direction"]
    F2["F2 — Indicator filter<br/>reads rsi, macd_hist"]
    F3["F3 — Pattern filter<br/>reads candlestick_pattern"]
    F5["F5 — Risk-guard filter<br/>reads account state, positions"]
    F6["F6 — Capital-management filter<br/>reads ATR, balance, stop distance"]
    F7["F7 — Meta-learner threshold rule<br/>p_hat from trend+indicator+pattern"]
    Decision([Decision: BUY / SELL / HOLD<br/>+ full audit trail])
    Veto([NO_TRADE])

    Start --> F1 --> F2 --> F3 --> F5 --> F6 --> F7 --> Decision

    F1 -. veto: direction conflict .-> Veto
    F5 -. veto: risk cap breached .-> Veto
    F6 -. veto: insufficient margin .-> Veto

    classDef filter fill:#dff,stroke:#066
    classDef terminus fill:#efe,stroke:#3c3
    classDef vetoed fill:#fee,stroke:#c33
    class F1,F2,F3,F5,F6,F7 filter
    class Decision terminus
    class Veto vetoed
```

## Run

```bash
algo-backtest run --strategy baseline --symbol EURUSD --from 2024-06-01 --to 2024-06-30
```

**Status (2026-09-25):** `config.yaml` and the pure-Python filter chain (F1-F7,
`chain/terminal.py`'s `F7TerminalDecision`) are real and tested. The `algo_backtest run
--strategy baseline` CLI path is **not yet wired** — `run.py`'s `STRATEGIES` registry has
no `"baseline"` entry, because that needs an `algos/baseline/main.py` LEAN algorithm
reading this chain config and driving it from live LEAN-native indicators + a persisted
meta-learner artifact, which has not been built or verified against the real LEAN
container. See `docs/technical-debt.md`'s Spec 04h entry.
