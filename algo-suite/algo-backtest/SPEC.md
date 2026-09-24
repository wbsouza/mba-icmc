# Spec — algo-backtest

## 1. Purpose & scope

`algo-backtest` runs strategies over the canonical Parquet data and produces
per-run results plus a complete decision audit trail. It contains the
**execution engine integration** (LEAN), the **deterministic filter chain**, the
**risk / money-management / order-management rule modules**, and the
**configuration system** (schema, loader, interactive generator).

It covers two demo milestones within one tool:

- **Baseline** (phase 3): price-only strategy → Sharpe + equity curve.
- **Hybrid** (phase 4): full filter chain incl. the news-context filter →
  hybrid vs baseline.

Out of scope: feature *production* (price features computed natively inside the
engine; text features come pre-computed from `algo-score`); results *analysis*
(that is `algo-analyze`); live broker execution (future work).

The risk, sizing, trailing-stop and partial-close rules implement
**standard, publicly documented FX money-management techniques** (fixed-fractional
risk, ATR-based stops, multi-target scaling-out, drawdown circuit-breakers) as
the project's own design, grounded in the cited literature
(`murphy1999technical`, `chan2013algorithmic`, `lopezdeprado2018advances`).

## 2. Inputs & outputs

| Direction | Item | Form |
|---|---|---|
| In | canonical Parquet | `parquet/{security_type}/{symbol}/…` (forex for the TCC), `parquet/sentiment/…`, `parquet/events/…` |
| In | strategy `config.yaml` | validated by `algo-core` schema/loader |
| In | LEAN execution store | **durable `lean-data/`** (materialized **once** from Parquet, reused across the sweep); optional tmpfs `/dev/shm/lean-data/` copy for hot reads |
| Out | run directory | `runs/<run-id>/` with results, equity curve, `trades.parquet`, `decisions.parquet`, `parameters.txt` |
| Out | trade ledger | `runs/<run-id>/trades.parquet` (one row per **closed trade** — the unit `algo-analyze` measures) |
| Out | audit trail | `runs/<run-id>/decisions.parquet` (one row per chain run — bar-level forensics) |

Two distinct artifacts, by design: **`trades.parquet`** is the trade ledger
(entry↔exit linked, realized PnL — what performance metrics are computed from);
**`decisions.parquet`** is the bar-level chain audit (one row per chain run incl.
`HOLD`/`NO_TRADE` — for forensics). Metrics never reconstruct trades from
`decisions.parquet`; they read `trades.parquet`.

## 3. Architecture & libraries

- **LEAN** runs in Docker on the pinned image `quantconnect/lean:17748`; Python
  `QCAlgorithm` (CPython 3.11 in the LEAN container — drives the workspace 3.11 pin).
  Automated backtests are driven via **testcontainers** (no `lean` CLI, no QC account;
  see `tests/integration/`); the `lean` CLI remains an option for manual runs.
- **TA-Lib** (C lib + wrapper) for `CDL*` candlestick recognition; LEAN-native
  indicators (`self.RSI`, `self.ATR`, …) for the rest.
- **pydantic v2** config models; **typer** config-generator CLI; **algo-core** for
  schema/loader/`Instrument`/layout/DuckDB.
- **pyarrow** to write the audit trail; the parquet→LEAN-native materializer.

```
algo_backtest/
├── cli.py                  # algo-backtest version|materialize|lean-smoke|run|metrics (IMPLEMENTED)
├── config.py               # IMPLEMENTED — backtest schema (markets.oanda.data_tz=UTC) + typed
│                           #   load_backtest_config() over algo_core.config.resolve()
├── materialize.py          # IMPLEMENTED — materialize_month(): canonical Parquet → lean-data/,
│                           #   config-resolved data_tz, idempotent (skips existing day-zips)
├── leandata.py             # IMPLEMENTED — canonical Parquet → durable lean-data/ day-zips
│                           #   (UTC/START-indexed, config-injected data_tz, fail-fast); see §3.1
├── lean_runner.py          # IMPLEMENTED — run_lean(): the pinned LEAN container (testcontainers),
│                           #   secret-free launcher config, 4 mounts; returns exit/logs/results dir
├── results.py              # IMPLEMENTED — parse_results(): LEAN /Results → RunResult(success,
│                           #   closed_trades, raw_results_path); minimal (metrics deferred to Slice E)
├── run.py                  # IMPLEMENTED — STRATEGIES registry + validate_run_inputs() + run_strategy():
│                           #   per-strategy param validator (closed key set), run a registered algo on
│                           #   lean-data, parse_results. Params are strategy-specific (generic dict)
├── algos/smoke_trade/      # IMPLEMENTED — bundled one-shot algo (explicit entry+exit) for lean-smoke
├── algos/baseline_ma/      # IMPLEMENTED — fast/slow SMA crossover (trend), long-only, fixed sizing
├── algos/baseline_meanrev/ # IMPLEMENTED — SMA mean-reversion (counter-trend), long-only, fixed sizing
├── artifacts.py            # IMPLEMENTED — write_run_artifacts(): pure persistence of run.json
│                           #   (manifest) + trades.json (ledger) + metrics.json; metrics.json last
│                           #   as the completeness marker (Slices E1+E2)
├── metrics.py              # IMPLEMENTED — metrics_from_results()/extract_metrics(): the four
│                           #   Chapter-4 metrics (total return, Sharpe, max drawdown, hit rate) from
│                           #   LEAN portfolioStatistics; fail-fast on incomplete results (E2)
├── experiment.py           # IMPLEMENTED — Run/Experiment value objects, load_experiment() (closed
│                           #   schema, fail-fast), run_experiment() (injected runner): deterministic
│                           #   runs/experiments/<experiment>/<run_id>/ + row-oriented experiment.json
│                           #   manifest; fail-fast → experiment-error.json (Stage F1)
├── engine/
│   └── algorithm.py        # QCAlgorithm: Initialize / OnData / OnOrderEvent (planned)
├── chain/
│   ├── model.py            # FilterResult, ExecutionState, Decision, ChainOutcome, FilterChain (run → ChainOutcome)
│   ├── filters/            # F1..Fn filter classes (one file each)
│   └── audit.py            # IMPLEMENTED — DecisionRow/FilterResultRow, decision_row_from_outcome(),
│                           #   write_decisions(): decisions.parquet audit trail (specs.md §11.3.4)
├── rules/
│   ├── risk_math.py        # fixed-fractional lot sizing
│   ├── strategy_math.py    # target ladder, trail-stop, stop-level stretch
│   ├── trail_stop.py       # trailing-stop trigger/destination
│   ├── close_portion.py    # partial-close laddering
│   └── risk_guard.py       # portfolio caps, drawdown breakers, leverage cap
├── config/
│   ├── generator.py        # interactive CLI (typer)
│   └── (schema/loader live in algo-core)
└── strategies/
    └── <name>/config.yaml  # generated, version-controlled
```

### 3.1 LEAN-native materializer (`leandata.py`) — not a black box

LEAN does not read Parquet; it reads its own on-disk format. The materializer
turns canonical Parquet into the **durable `lean-data/` execution store**,
**read-through**: built on the first cache miss, persisted, and reused across the
whole sweep — never regenerated per run (`../docs/parquet-evaluation.md`, refined
decision 2026-05-24). The optional tmpfs `/dev/shm/lean-data` copy is staged from
it for hot reads. It is explicitly specified so the temporal-alignment risk is
visible:

- **Resolution:** writes **minute** data directly (LEAN supports a `minute`
  resolution; no synthetic ticks are fabricated from minute bars).
- **Format:** one zip per pair per day under the LEAN Forex folder, containing a
  CSV with LEAN's fixed Forex **quote** schema (`millis-since-midnight,
  bidO,bidH,bidL,bidC, bidVol, askO,askH,askL,askC, askVol`; both sides retained,
  volumes 0 for FX); file/dir naming follows LEAN's convention, mapped from the
  `Instrument` asset class (`forex/<market>/minute/<symbol>/YYYYMMDD_quote.zip` for
  FX; LEAN uses `equity/<market>/minute/<symbol>.zip`, `future/...`, etc. for other
  classes — a deterministic per-asset-class mapping, forex for the TCC). Implemented
  in `leandata.py` (`write_lean_minute`).
- **Timezone (empirically nailed 2026-05-25):** canonical Parquet is UTC. LEAN stores
  forex (OANDA) minute data in **UTC**, **START-indexed** (`ms` = bar start since
  midnight in the configured data tz; file-day = start's date), so the materializer
  writes the bar start directly. The data tz is **injected from config** (UTC for
  OANDA → identity conversion), never hard-coded. With the algorithm tz set to UTC,
  `self.UtcTime` at delivery == the bar's UTC end, so each Parquet bar maps to exactly
  one LEAN bar, DST-invariant. Proven by a containerized round-trip test
  (`tests/integration/test_timezone_roundtrip.py`, summer EDT + winter EST) — not the
  spike's earlier (disproven) "NY / END-indexed" guess.
- **Gaps:** minutes with no tick have **no bar** (not forward-filled); LEAN
  tolerates missing minutes. Forward-filling here would fabricate prices.
- **Durability + idempotence:** day-zips are written atomically (temp file + rename),
  so an interrupted run never leaves a truncated zip; `materialize_month` skips days
  whose zip already exists and **fails fast on a missing or empty** canonical Parquet
  (an empty month partition is a bad upstream artifact, not "already done").
- **Volume:** tick-count volume is carried through; it is an activity proxy
  (FX has no consolidated volume), consumed only by the market-activity feature.
- **Quote side:** bid/ask are both retained in Parquet; the converter emits the
  side LEAN uses for fills, and the transaction-cost model reads the spread from
  the same Parquet so backtest costs and the quote stream are consistent.

The **week-1 spike** validated the core path (engine runs locally, lean-data format,
bar timing) before anything was built on it; see `spikes/lean/README.md` for the
de-risking breakdown. Its findings are now superseded by committed code: the
materializer (`leandata.py`, unit-tested) and a **testcontainers integration suite**
(`tests/integration/`) that runs the pinned `quantconnect/lean:17748` image with no
QC account and no `lean` CLI — a smoke backtest plus the timezone round-trip that
empirically established the UTC/START-indexed convention. Integration tests carry the
`integration` mark and are **excluded from `make check`** (the image is ~10 GB); run
them with `uv run pytest -m integration`. The `/dev/shm` acceleration remains optional
and out of scope here.

**Backtest↔live parity.** The feature and sentiment computation is one
mode-agnostic engine (vectorized over history in backtest, one bar at a time in
live) behind the `algo-core` `Cache` port in read-through + write mode. The same
code and same cache run in both modes, so the deployed model never sees inputs it
was not trained on (no train/serve skew). Each bar is computed **exactly once**
the first time it exists; every later access — the rest of a sweep, or a live
restart's warmup — is a cache hit. In live, only the just-closed bar misses
(it never existed before); the trained model is loaded, never retrained.

## 4. Diagrams

### 4.1 Sequence — one bar through the filter chain to an order

```mermaid
sequenceDiagram
    participant L as LEAN (OnData bar)
    participant A as algorithm
    participant FC as FilterChain
    participant F as Filters F1..Fn
    participant X as Order executor (terminal filter)
    participant B as Broker (LEAN sim)
    participant AU as decisions.parquet

    L->>A: OnData(bar)
    A->>FC: run(ExecutionState)
    loop per filter
        FC->>F: apply(state)
        F-->>FC: FilterResult(reco, reason, veto?, enrichment)
        FC->>FC: append result, merge enrichment into state.features
        alt veto
            FC-->>A: Decision.NO_TRADE (short-circuit)
        end
    end
    FC->>X: decide(state)
    X-->>FC: BUY | SELL | HOLD
    FC-->>A: ChainOutcome (decision + enriched state)
    alt BUY or SELL
        A->>B: MarketOrder(sized lots)
        B-->>A: OnOrderEvent(fill)
    end
    A->>AU: persist one row (filter_results, final_decision, vetoed_by)
```

### 4.2 State — position / trade lifecycle

```mermaid
stateDiagram-v2
    [*] --> Flat
    Flat --> Open: BUY/SELL emitted, order filled
    Open --> Open: HOLD (trail stop armed / advanced)
    Open --> PartiallyClosed: target level hit, partial close
    PartiallyClosed --> PartiallyClosed: next target / trail advance
    Open --> Closed: stop or final target hit
    PartiallyClosed --> Closed: stop or final target hit
    Open --> Closed: risk-guard breaker (drawdown/leverage)
    PartiallyClosed --> Closed: risk-guard breaker
    Closed --> Flat: trade finalized, PnL and audit recorded, cooldown applied
    Flat --> [*]
```

`Closed` is a transient finalization state (record PnL, write the trade's audit
rows, apply the one-trade-per-candle / cooldown dedup) distinct from `Flat`
(idle, eligible to open a new position). Every exit path — stop, final target,
or risk-guard breaker — converges on `Closed` before returning to `Flat`.

### 4.3 State — config parameter loading (delegated to algo-core)

See `algo-core` §4.2; `algo-backtest` consumes that policy: a missing
trading-impactful parameter is a hard stop before the first bar.

## 5. CLI surface

```
algo-backtest run      --strategy <name> [--symbol ...] --cv <single|cpcv|walkforward>
                       [--folds N --embargo D]        # validation protocol (see below)
algo-backtest config   <name>                                         # interactive generator
algo-backtest config   --upgrade <old.yaml>                           # migrate schema version
algo-backtest materialize --src parquet/{security_type} --dst lean-data/  # parquet → durable LEAN-native (lazy/read-through; forex for the TCC)
algo-backtest lean-smoke                                              # trivial backtest, sanity
```

### 5.1 Validation protocol (CPCV / walk-forward)

The methodology's combinatorial purged k-fold + embargo (Ch.3 §sec:evaluation)
is **driven by `algo-backtest`, not an external script**. `--cv` selects the
protocol; the split is defined in the strategy config (`validation:` block:
`scheme`, `n_folds`, `embargo_days`, the train/validation/test spans). For each
fold the engine purges feature observations whose label horizon overlaps a
validation fold and applies the embargo, runs the backtest per fold, and writes
one `runs/<run-id>/fold=<k>/` set of artifacts plus an aggregate. `--cv single`
runs the single held-out test pass (one evaluation per variant, no iteration on
the test span). `algo-analyze` reads the per-fold `trades.parquet` to compute the
deflated Sharpe across folds. This closes the methodology↔implementation gap:
CPCV is a first-class run mode, configured, not improvised.

## 6. Data contracts

### 6.1 Trade ledger — `runs/<run-id>/trades.parquet`

One row per **closed trade** (LEAN exposes filled `Trade` objects natively;
entry and exit are linked here). This is the unit `algo-analyze` measures.

| Column | Type | Notes |
|---|---|---|
| `trade_id` | string | unique per trade |
| `pair` | string | e.g. `EURUSD` |
| `direction` | string | `LONG` / `SHORT` |
| `entry_ts` / `exit_ts` | datetime (UTC) | fill timestamps |
| `entry_price` / `exit_price` | float | fill prices |
| `size` | float | lots / units |
| `realized_pnl` | float | net of modeled transaction costs |
| `return` | float | per-trade return (for Sharpe, hit rate) |
| `holding_minutes` | int | exit − entry |
| `exit_reason` | string | `stop` / `final_target` / `risk_guard` |
| `max_adverse` / `max_favorable` | float | excursions (optional, for analysis) |

Partial closes are represented as the realized PnL of the closed portion folded
into the trade's final `realized_pnl`, with intermediate closes recorded in
`decisions.parquet`; one `trades.parquet` row is the whole trade's outcome.

### 6.2 Audit trail — `runs/<run-id>/decisions.parquet`

| Column | Type | Notes |
|---|---|---|
| `timestamp` | datetime (UTC) | bar timestamp |
| `pair` | string | e.g. `EURUSD` |
| `features_hash` | string | hash of input feature dict (reproducibility) |
| `filter_results` | list<struct> | accumulated FilterResult list |
| `final_decision` | string | `BUY` / `SELL` / `HOLD` / `NO_TRADE` |
| `vetoed_by` | string \| null | name of vetoing filter, if any |
| `trade_id` | string \| null | the trade this chain run opened or managed; `null` for `NO_TRADE`. **Foreign key to `trades.parquet`** |

One row per chain run (~2 M rows / pair over 10y). This is the **bar-level
forensic** record, not a trade ledger: per-trade metrics come from
`trades.parquet`. The `trade_id` foreign key links each opening (`BUY`/`SELL`)
and each managing (`HOLD`) chain run to its trade, so "which filters preceded a
losing trade?" is an unambiguous join on `trade_id` — never a fragile
timestamp+pair match. `algo-analyze` consumes both: `trades.parquet` for metrics,
`decisions.parquet` joined by `trade_id` for forensics.

### 6.3 Decision semantics

| Decision | Meaning |
|---|---|
| BUY / SELL | open new long / short |
| HOLD | manage an open position (trail, partial close, no-op) |
| NO_TRADE | stand aside; any veto, or no entry and no open position |

### 6.4 Config

YAML, `schema_version` pinned; loaded via `algo-core` (hard-stop on missing
trading-impactful params; `null` = explicit-disable; `extends:` inheritance;
provenance log to `parameters.txt`). Sections: `universe`, `risk_math`,
`strategy_math`, `risk_guard`, `circuit_breakers`, `operational`, and the ordered
`chain` (the filter sequence).

**Filter order is a searched hyperparameter, not a fixed assumption.** The
`chain` list defines the order and presence of filters; since each filter acts on
the state the previous ones accumulated, different orderings yield different
decisions, so the best ordering is found **empirically by simulation**. To stay
honest under the validation protocol (§5.1), the ordering is selected on the
training/validation folds of the combinatorial purged $k$-fold scheme and
**frozen before the single held-out test pass** — it is never tuned on the test
span. The ordering comparison is reported in the monografia's ablation study
(Chapter 4).

**Each filter also reads a configurable timeframe (multi-timeframe analysis).**
A filter entry carries a `timeframe` (MT5 set `m1`…`d1`); the decision is taken on
the finest bar of the grid, but a filter may analyze a coarser one (e.g. a trend
filter on `h4` for an `m1` decision). The bar series for each timeframe is
pre-materialized by `algo-transform` and read through the `algo-core` cache, so a
filter observing a different timeframe is a lookup, not a recomputation. Like the
order, the per-filter timeframe is a hyperparameter: selected on the
training/validation folds and frozen before the test pass, part of the same
ablation.

**Lot units are broker-specific and come from LEAN, not hard-coded.** Risk math
(`risk_math.py`) sizes the position in notional/standard lots using
`Instrument.lot_size` (the universal 100,000-unit standard FX lot). The
**broker-dependent minimum order size and lot step** (OANDA = 1 unit; MT4/MT5 =
0.01-lot steps) are LEAN's `SymbolProperties` for the configured market
(`Instrument.market`), applied when the computed size is rounded into an
executable order. We do not duplicate per-broker lot tables; switching the
brokerage changes only the market, and LEAN supplies the tradable increment.

## 7. Error handling

- Missing trading-impactful config param → hard stop before first bar
  (named param + section + hint).
- `schema_version` mismatch → hard stop with `--upgrade` hint.
- Insufficient margin for computed lot size → capital filter vetoes (NO_TRADE),
  logged; not a crash.
- Risk-guard breach (portfolio cap, drawdown, leverage) → veto / flatten per
  config; logged in audit trail.
- Filter veto → chain short-circuits to NO_TRADE; `vetoed_by` recorded.
- `lean-data/` absent or stale (version mismatch) → `run` materializes it on the
  first miss (read-through), persists, and reuses it for the rest of the sweep;
  the optional tmpfs copy is re-staged from it if cleared.

## 8. Test scenarios (Gherkin)

The scenarios below describe the target-state chain with the real F1-F7 filters
(§11.3.2 of `specs.md`), which do not exist yet. `tests/features/filter_chain_mechanics.feature`
is the executable proof of the same accumulate / veto-short-circuit / abstain-does-not-veto
mechanics today, using trivial stub filters ahead of F1-F7 (Spec 04b).

```gherkin
Feature: Deterministic filter chain
  Background:
    Given a strategy config with filters F1..F7
    And a synthetic ExecutionState for one bar

  Scenario: A veto short-circuits the chain to NO_TRADE
    Given filter F5 (risk guard) vetoes
    When the chain runs
    Then no downstream filter is consulted
    And the final decision is NO_TRADE
    And vetoed_by is "risk_guard"
    And one audit row is written for the bar

  Scenario: Enrichment accumulates downstream
    Given F1 enriches state with trend_score
    When F7 (threshold rule) runs
    Then F7 can read trend_score from state.features
    And the audit row lists every filter's contribution

  Scenario: ABSTAIN does not veto
    Given F3 (pattern) ABSTAINs (no pattern this bar)
    When the chain runs
    Then the chain continues past F3
    And F3 carries no vote weight in the terminal rule

Feature: Fixed-fractional position sizing
  Scenario Outline: lot size from risk, unit value and stop distance
    Given account balance <balance> and risk fraction <risk>
    And stop distance <units> units with unit value <uv>
    When sizing is computed
    Then lot size equals (<balance> * <risk>) / (<uv> * <units>) within tolerance
    # for FX the instrument's unit is the pip; the formula is unit-generic
    Examples:
      | balance | risk | units | uv  |
      | 10000   | 0.02 | 20    | 1.0 |
      | 10000   | 0.02 | 50    | 1.0 |

  Scenario: USDJPY unit_size is honored in sizing
    Given a USDJPY trade (FX, unit "pip")
    Then the stop distance uses unit_size 0.01, not the EURUSD 0.0001

Feature: Trailing stop and partial close
  Scenario: Trail arms at the configured level
    Given a long position and trail-arm factor 0.5
    When price advances halfway to the target distance
    Then the trailing stop is armed at the configured destination

  Scenario: Partial close at a target level
    Given a long position with a target ladder
    When the first target level is hit
    Then the configured fraction is closed
    And the remainder stays open with the trail advanced

Feature: Risk guard
  Scenario: Drawdown breaker flattens and blocks new trades
    Given the daily drawdown limit is breached
    When a new BUY would be emitted
    Then the risk guard vetoes
    And open positions are flattened per config
    And the breaker is recorded in the audit trail

  Scenario: Explicitly disabled leverage cap is logged, not enforced
    Given max_leverage is null in the config
    When the strategy starts
    Then startup logs "EXPLICITLY DISABLED: max_leverage"
    And no leverage cap is enforced

Feature: Reproducibility
  Scenario: Same config + same data ⇒ identical decisions
    Given a fixed config and a fixed cached feature stream
    When the backtest runs twice
    Then both runs produce byte-identical decisions.parquet
    And parameters.txt is identical

  Scenario: Missing required parameter is a hard stop
    Given a config missing risk_math.risk_per_trade
    When the backtest starts
    Then it refuses to start before the first bar
    And the error names the parameter
```

Edge cases (this tool's §8 themes): veto short-circuit; ABSTAIN vs VETO;
sizing unit_size per instrument; margin-insufficient veto; drawdown/leverage breaker;
audit completeness (one row per chain run incl. NO_TRADE); determinism
(byte-identical reruns, fixed seeds); tmpfs rebuild; schema-version mismatch;
`extends:` variants (a base strategy + a looser-risk variant as a short diff).

## 9. Acceptance criteria

- Baseline (phase 3): price-only strategy runs end-to-end on LEAN over the
  target window; emits Sharpe, max drawdown, equity curve, full audit trail.
- Hybrid (phase 4): news-context filter active; produces a comparable run for
  hybrid-vs-baseline.
- Config policy enforced exactly (hard-stop / default-log / explicit-null /
  provenance log).
- Reruns are byte-identical (determinism).
- Rule modules covered by unit + property tests; chain covered by BDD.
- No identifying third-party expression in code or docs; rules implemented fresh
  from the cited public techniques.

## 10. Open items

- Number of filters in the first chain and their order (config-driven; the
  reference chain is F1 trend → F2 indicator → F3 pattern → F4 news → F5 risk →
  F6 capital → F7 threshold). A **volume/strength context filter** is planned as
  an additional evidence filter (top layer, alongside trend/indicator): it reads
  the daily per-currency `currency_strength` feature from `algo-transform`
  (tick-volume activity proxy) and biases direction toward the day's dominant
  currency. It is added via `config.yaml` like any other filter; its signal
  strengthens as the pair universe expands toward the major pairs (the universe
  is config-driven, so scaling is configuration, not code).
- **Extended filter set F8–F14** (the quality gates of methodology
  §subsec:extended-filters — candlestick confirmation, tradability/ADF, news
  confidence/magnitude gates, sub-model consensus, etc.) are added as further
  filter modules under `chain/filters/`, config-enabled per variant. They are
  exercised by Experiments 6–9 (the filter-ablation study) and the volume filter
  above joins this extended set. Added incrementally; not part of the F1–F7
  baseline chain.
- Ablation variants (single base strategy vs additional variants) — default: one
  base strategy for the TCC; variants via `extends:` if time permits.
- Recommended-range values shown by the config generator for each risk-guard
  parameter.
- Whether TA-Lib `CDL*` runs inside the LEAN algorithm or as a pre-pass (default:
  inside, native indicators preferred; TA-Lib only for candlestick patterns).
