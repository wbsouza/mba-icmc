# Spec 04 tasks — algo-backtest: order-execution engine + filter chain + hybrid

**Tool:** `algo-suite/algo-backtest/` · **Status:** Wave 1 in progress — Track B (filter-chain
mechanics, Spec 04b) landed on `feat/04b-filter-chain-mechanics`; Track A (order-execution engine,
Spec 04a) still in flight in another session.
**Governing docs:** this folder's [`spec.md`](spec.md) (§3–§7), [`algo-backtest/SPEC.md`](../../../../algo-backtest/SPEC.md)
(§3 dir layout: `engine/`, `chain/`, `rules/`, `config/`), `specs.md` §11.3.1 (dataclasses,
verbatim), §14.5–§14.8 (risk/capital-management formulas).

This breaks Spec 04 into parallel, dependency-ordered waves so two sub-agents can work Wave 1
concurrently today; Waves 2–4 are sequencing notes for the sessions that follow, not yet task cards.

## Wave 1 — no dependencies, start now, 2 parallel tracks

Both tracks touch disjoint files. Spec 01/02/03 are already landed; the existing
`baseline_ma`/`baseline_meanrev`/LEAN integration is already on disk
([`first-baseline-results.md`](../../../first-baseline-results.md)).

### Track A — order-execution engine (spec.md §3; build/test first per user directive)

1. Audit `algos/baseline_ma/main.py` / `algos/baseline_meanrev/main.py` for the order-placement
   code already there (read-only).
2. Extract it into `engine/order_executor.py` — `OrderExecutor`: `Decision` + sizing context in,
   places the `MarketOrder`, handles `OnOrderEvent`, returns a normalized fill record (spec.md §3.2).
3. `engine/algorithm.py` — the `QCAlgorithm` subclass (`Initialize`/`OnData`/`OnOrderEvent`),
   listed as "planned" in `algo-backtest/SPEC.md` §3's tree today, wired to `OrderExecutor`.
   **Brokerage simulation is a config-selected adapter, not a hardcoded call** — mirror the
   `algo_download` `NewsDataSource`/`REGISTRY`/`build_data_source` pattern (`CLAUDE.md` "Patterns in
   use": Strategy + Adapter, Registry + Factory Method) so the app stays neutral to which fill/fee/
   spread model runs and a new one is a config value + one new file, never a rewrite of
   `OrderExecutor`/`algorithm.py`:
   - `engine/brokerage/base.py` — `BrokerageAdapter` ABC: `name: str` + `apply(algorithm: QCAlgorithm) -> None`.
   - `engine/brokerage/__init__.py` — `REGISTRY` + `build_brokerage_adapter(name, cfg)`, `@register`
     class decorator, same shape as `algo_download/adapters/__init__.py`.
   - `engine/brokerage/oanda.py` — first (and for now only) concrete adapter: `apply()` calls LEAN's
     real `self.set_brokerage_model(BrokerageName.OANDA, AccountType.MARGIN)` — LEAN's backtest-mode
     OANDA brokerage *model* (fee/spread/margin/leverage realism), no live connection, still reading
     price data purely from the materialized `lean-data/` store (`leandata.py`, already `IMPLEMENTED`).
   - Config: `broker.adapter: oanda` under the existing `config_schema` pattern (`specs.md` §14.9,
     `conf/algo-backtest.yaml` override, `algo_core.config.resolve()` precedence) — missing key is a
     hard stop (fail-fast per `CLAUDE.md`), never a silent default, since it changes fill economics.
   - `algorithm.py`'s `Initialize` calls `build_brokerage_adapter(cfg.broker.adapter, cfg).apply(self)`
     — the algorithm and `OrderExecutor` never reference `BrokerageName.OANDA` directly.
   **Gap found while planning**: neither `baseline_ma` nor `baseline_meanrev` sets any brokerage
   model today — they run against LEAN's generic default, not OANDA's actual fee/spread rules.
   Backport the adapter call to both in step 4 below so existing baseline numbers and the new hybrid
   numbers are comparable on the same fill assumptions.
4. Migrate both `baseline_ma` and `baseline_meanrev` onto `OrderExecutor` — no duplicated
   order-placement code left (DoD §7). Existing `run_baseline.feature`/`packaged_algos.feature`
   must stay green (behavior unchanged, only the code path).
5. `tests/features/order_execution.feature` — the 6 scenarios from spec.md §3.3 (BUY, SELL, HOLD,
   NO_TRADE, order-rejection handled, stop-loss/take-profit outline) against the real pinned LEAN
   container (`quantconnect/lean:17748`, TD-19's proven testcontainers pattern). Validate wording
   against LEAN's actual `OnOrderEvent` payload before finalizing assertions — these are a draft.

Depends on: step 1→2→3, 2→4, (3,4)→5 within the track.

### Track B — filter-chain mechanics (spec.md §4 step 1; `specs.md` §11.3.1)

1. `chain/model.py` — `FilterResult`, `ExecutionState`, `Decision`, `ChainOutcome`, `FilterChain`
   (copy the dataclass shapes verbatim from `specs.md` §11.3.1; implement the
   accumulate / veto-short-circuits / abstain-does-not-veto loop).
2. Extend `algo-backtest/SPEC.md`'s existing "Feature: Deterministic filter chain" Gherkin outline
   (do not start a new feature file) with 2–3 trivial stub filters (constant VETO/ABSTAIN/PASS)
   that prove step 1's chain mechanics before any real F1–F7 filter exists.

Depends on: step 1→2 within the track.

**Gate (both tracks, every step):** `cd algo-backtest && uv run pytest tests` (add `-m integration`
for LEAN-container steps, i.e. Track A step 4–5); `make check` per `CLAUDE.md`'s code-quality gate
before calling a track done. Every test is Gherkin/pytest-bdd — no plain `def test_…()` — per
`CLAUDE.md`.

---

## Wave 2 — parallel, depends only on Track B step 1 (`chain/model.py`)

Not started until Wave 1 lands. Four independent tracks, dispatchable in parallel once `chain/model.py`
exists:

- **F1–F3 (price-derived filters)** — trend, indicator, pattern; `chain/filters/f1_trend.py`,
  `f2_indicator.py`, `f3_pattern.py`. No new external data dependency.
- **F5/F6 (risk & capital-management)** — port `risk_math.py` / `trail_stop.py` / `close_portion.py`
  / `risk_guard.py` from the EJB version (`specs.md` §14.5–§14.8, formulas given verbatim) into
  `rules/`, then `chain/filters/f5_risk_guard.py` / `f6_capital_mgmt.py`. Regression test: the
  Python port must reproduce the legacy decisions on identical synthetic input (`specs.md` §14.3).
- **F4 (news-context filter)** — `chain/filters/f4_news_context.py`, vetoes on active high-risk
  events from Spec 03's sentiment/event Parquet (`specs.md` §11.3.2). **Blocker to verify first**:
  confirm Spec 03's Parquet is actually present on the NAS data root — not visible from this
  sandbox (`/media/nas/wellington/mba/algo-suite/data`, unmounted here).
- **Audit trail** — `chain/audit.py`, the `decisions.parquet` writer (§11.3.4 columns); the
  cross-tool contract Spec 05 (`algo-analyze`) joins on `trade_id`. Depends only on `chain/model.py`,
  not on any filter — safe to build alongside the three tracks above.

## Wave 3 — depends on Wave 2 (F1–F6 landed; trains over their combined feature output)

- Add the `lightgbm` dependency to `algo-backtest/pyproject.toml` (currently absent, despite the
  package description already naming it).
- F7 meta-learner — LightGBM sub-models per feature family + logistic meta-learner combining them
  into `p̂ₜ` (`PRD.md` §1), trained on the walk-forward split (`PRD.md` §4).
  `chain/filters/f7_meta_learner.py`.

## Wave 4 — depends on Wave 1 Track A (`OrderExecutor`) + Wave 3 (F7)

- Wire F7's terminal step to `OrderExecutor` — the join point between the two halves of this spec
  (spec.md §4 step 6).
- `baseline` (chain without F4) / `hybrid` (full chain) strategy YAML via `extends:` composition
  (`experiments.md` §1).
- Experiment 0 — `buyhold`/`random`/`perfect_foresight` known-answer strategies through the same
  chain + executor; build early, they validate every later Sharpe number.
- End-to-end: `algo-backtest run --strategy hybrid --symbol EURUSD` runs through the full chain;
  `decisions.parquet` joins `trades.parquet` by `trade_id`.
- Mermaid filter-chain diagram per strategy README (`specs.md` §11.3.3 convention). Update
  `algo-backtest/SPEC.md`, `00-PLAN.md` §1, `ch04-deliverables.md` status column — per DoD §7 and
  this project's "keep docs in sync" rule.

```
Wave 1 (now):    Track A (order executor) ‖ Track B (chain mechanics)
Wave 2 (next):   F1–F3 ‖ F5/F6 ‖ F4 ‖ audit-trail      — all gated on Wave 1 Track B
Wave 3 (next+1): lightgbm dep → F7 meta-learner         — gated on Wave 2 (F1–F6)
Wave 4 (next+2): terminal wiring → configs → Experiment 0 → integration → docs — gated on Wave 1
                 Track A + Wave 3
```

## On completion

Per the swarmforge constitution (`swarmforge/constitution/articles/project.prompt`): move this
story folder to `algo-suite/docs/stories/done/<YYYY-MM-DD>-algo-backtest-filter-chain-hybrid/` and
add a `lessons-learned.md` alongside `spec.md`, matching existing `done/` folders. Update
`00-PLAN.md` §1, `algo-backtest/SPEC.md`'s status line, and `technical-debt.md` in the same pass.
