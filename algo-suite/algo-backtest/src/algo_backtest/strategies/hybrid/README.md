# Strategy: `hybrid`

`extends: baseline`, adding F4 (news-context) and the "news" feature family. Docs/
experiments.md Experiment 2: evaluate full hybrid vs. baseline on EUR/USD — this is the
strategy Hypothesis H1 is tested against. Config: [`config.yaml`](config.yaml).

```mermaid
flowchart TB
    Start([Bar tick])
    F1["F1 — Trend-regime filter<br/>reads trend_direction, trend_strength,<br/>higher_tf_trend_direction"]
    F2["F2 — Indicator filter<br/>reads rsi, macd_hist"]
    F3["F3 — Pattern filter<br/>reads candlestick_pattern"]
    F4["F4 — News-context filter<br/>reads real GDELT event_intensity<br/>(mandatory) + per-symbol sentiment<br/>(best-effort, TD-48)"]
    F5["F5 — Risk-guard filter<br/>reads account state, positions"]
    F6["F6 — Capital-management filter<br/>reads ATR, balance, stop distance"]
    F7["F7 — Meta-learner threshold rule<br/>p_hat from trend+indicator+pattern+news"]
    Decision([Decision: BUY / SELL / HOLD<br/>+ full audit trail])
    Veto([NO_TRADE])

    Start --> F1 --> F2 --> F3 --> F4 --> F5 --> F6 --> F7 --> Decision

    F1 -. veto: direction conflict .-> Veto
    F4 -. veto: active high-risk event .-> Veto
    F5 -. veto: risk cap breached .-> Veto
    F6 -. veto: insufficient margin .-> Veto

    classDef filter fill:#dff,stroke:#066
    classDef terminus fill:#efe,stroke:#3c3
    classDef vetoed fill:#fee,stroke:#c33
    class F1,F2,F3,F4,F5,F6,F7 filter
    class Decision terminus
    class Veto vetoed
```

## Run

```bash
algo-backtest run --strategy hybrid --symbol EURUSD --from 2024-06-01 --to 2024-06-30
```

**Status (2026-09-26):** `config.yaml`, the pure-Python chain, and `algos/hybrid/main.py`
are all real and run against the real pinned LEAN container (Spec 04h) — same wiring
smoke-test caveats as [`baseline`](../baseline/README.md), plus F4's own sentiment half
remaining best-effort pending TD-48 (full-month real article-text ingestion, ~500 GB /
~90 hours at the current adapter's throughput) — the event-veto half is real today. See
`docs/technical-debt.md`'s TD-51 and
`docs/stories/done/2026-09-26-04h-algo-backtest-hybrid-integration/RUNBOOK.md` for the
exact commands to reproduce.
