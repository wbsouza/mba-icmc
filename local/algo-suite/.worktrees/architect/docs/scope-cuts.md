# Scope cuts — what is explicitly OUT for the TCC

Stated up front to prevent gold-plating. These are deliberate exclusions, not
omissions; the thesis lists deferred items as documented future work
(`monografia` §reproducibility), and the engineering deferrals live in
`technical-debt.md`. This file is the single human-readable cut list.

| Feature | Status | Rationale |
|---|---|---|
| Multi-asset (equities, crypto, futures) | **CUT** | Forex only for the thesis. The `Instrument`/`SecurityType` model keeps the door open, but only FX majors are built (EUR/USD, USD/JPY the targets). |
| Strategy config inheritance (`extends:`) | **CUT** | Post-TCC; two strategies don't need it (TD-8). |
| Layered config file/env loading | **DEFERRED** | Loader *policy* is built; file merge is TD-3. First backtest uses convention defaults / hardcoded params. |
| Live trading / OANDA brokerage (Phase 6) | **CUT** | Out of scope; no broker connectivity from this repo. Credentials never on the critical path. |
| Tick-resolution backtests | **CUT** | `algo-transform` produces any MT5 timeframe (`m1`…`d1`) and filters are multi-timeframe (each reads its own, chosen empirically), but tick-level *backtesting* is out (ticks are kept only for slippage). |
| NoSQL / containerized cache backend | **CUT (road kept)** | `LruCache` default; the `Cache` port allows a Redis/Aerospike backend later without caller changes. |
| Repository analytical/query interface | **DEFERRED** | `put`/`read_all`/`exists` only; filtered/joined reads are TD-14, added when a consumer needs them. |
| Extra news sources (FNSPID, CC-News, Reddit, central-bank scrapers) | **CUT** | GDELT + GPR only; others are future-work adapters behind the same registry. |
| yfinance daily fallback | **DEFERRED** | Resilience branch only; built after the primary Dukascopy → backtest chain is proven (TD-17). |
| A01–A04 ablations (§4.5) | **MAYBE** | Run only if time permits after baseline + hybrid; the baseline (§4.3) is the priority. |
| 7-layer filter chain (veto/enrichment) | **TRIMMED for MVP** | First backtest uses 3 layers (trend / signal / risk). Audit trail kept (thesis value); veto/enrichment expanded later. |
