# Progress — Spec 04a (order-execution engine)

- [x] Audit `baseline_ma`/`baseline_meanrev` for existing order-placement code (T1) —
      no explicit MarketOrder/OnOrderEvent code existed; both use LEAN's
      `set_holdings`/`liquidate` helpers only, so this is a fresh build, not an extraction.
- [x] Implement `OrderExecutor` (`engine/order_executor.py`) (T2) — unit-tested
      (8 scenarios, `tests/features/order_executor.feature`) against a fake algorithm
      double; real LEAN types (`OrderStatus`) imported lazily so it stays testable
      outside the container.
- [x] Implement `engine/algorithm.py` (`QCAlgorithm` skeleton) wired to `OrderExecutor` (T3) —
      container-only file (imports `AlgorithmImports`), excluded from ruff/mypy like `algos/`;
      proven only via the real-container feature, not plain unit tests.
- [x] `engine/brokerage/` port: `BrokerageAdapter` ABC + registry + `oanda.py` adapter,
      config-selected — unit-tested (4 scenarios, `tests/features/brokerage_adapter.feature`).
      `broker.adapter` added to `config.py`'s `SCHEMA` as `Impact.TRADING` (no default,
      hard stop on missing — matches spec.md's fail-fast requirement); threaded through
      `run_strategy`/`run_experiment`/`cli.py` as a `broker_adapter` LEAN parameter.
      `lean_runner.py` now copies `engine/` alongside every algo's `main.py` so it's
      importable as a top-level `engine` package inside the container.
- [x] Migrate `baseline_ma` onto `OrderExecutor` + brokerage adapter (T4) — replaced
      `set_holdings`/`liquidate` with `order_executor.execute(Decision.BUY, ...)` /
      `order_executor.close(...)`; `broker_adapter` param required, `init_execution`
      called from `initialize()`.
- [x] Migrate `baseline_meanrev` onto `OrderExecutor` + brokerage adapter (T4) — same pattern.
- [x] `tests/features/order_execution.feature` — 9 scenario examples (7 scenarios, 2 are
      Scenario Outlines) green against the real pinned LEAN container (T5). Pruned the
      draft's `trades.parquet` assertions to the recorded-fill log instead — no
      `trades.parquet` writer exists anywhere in the codebase yet (only `trades.json`
      via `artifacts.py`); building one is a separate, larger cross-cutting task, out of
      Track A's stated scope. New `tests/algos/order_exec` test algorithm gives
      per-scenario control over Decision/size/stop-loss/adapter that the price-driven
      baselines can't. Real-container debugging found and fixed 3 bugs: internal
      `engine/brokerage/*` modules used absolute `algo_backtest.engine...` imports that
      don't resolve once `engine/` is copied as a top-level package inside the container
      (fixed → relative imports); `BrokerageName.OANDA` doesn't exist, the real LEAN
      enum member is `OANDA_BROKERAGE`; `OrderExecutor.execute` passed `SizingContext.size`
      straight to `market_order` as raw quantity instead of a portfolio fraction via
      `calculate_order_quantity` (matching `set_holdings`'s prior semantics), which
      rejected any size below one lot.
- [x] `make check` green (ruff, mypy, pytest — 74/74 non-integration + 11/11 integration).
      No `make audit`/`pip-audit` tooling exists in this repo (pre-existing gap); no new
      third-party dependency was added, so nothing new to audit here.

**Self-audit finding (disclosed, not silently papered over):** `OrderExecutor.execute`
threads `SizingContext.stop_loss`/`take_profit` through into the `FillRecord` as data,
but never submits a real LEAN protective order (`StopMarketOrder`/bracket) for them —
scenario 05's "carries a stop-loss" is proven at the `FillRecord` level, not by an
enforced LEAN order. Logged as `technical-debt.md` TD-46 (deferred until Wave 2's F6
capital-management filter is the first real caller needing an enforced stop).

- [x] QA pass (2026-09-24): merged hardener's `4ca4aae`, then independently verified.
      `make check` (78/78 non-integration) and the real-container
      `order_execution.feature` (9/9) both green. Corrected
      `tests/qa/spec-algo-backtest-order-execution.qa.md`, which asserted against a
      `trades.parquet` artifact that was never built; today's real ledger is
      `trades.json`, and it should stay that way — a trades ledger is an ongoing,
      updated-over-the-run record, not the fixed/immutable data Parquet is for
      (see `technical-debt.md` TD-47, which also corrects `SPEC.md` §6.1's
      `trades.parquet` plan).
      Authored the missing `tests/qa/run_order_execution_qa.py` against `trades.json`,
      driven through the `algo-backtest` CLI only; found and fixed two real bugs along
      the way: the unknown-brokerage-adapter path failed inside the LEAN run (exit 1,
      not the CLI-preflight exit 2 the doc assumed) with no error surfaced to the CLI
      caller at all (`RunResult` had no `error` field) — added one, sourced from LEAN's
      `state.RuntimeError`, and `cli.py`'s `run` command now echoes it to stderr on
      failure. Also added memory/CPU caps and a cross-process concurrency slot limiter
      to `lean_runner.py` (`LEAN_MAX_CONCURRENT`/`LEAN_CONTAINER_MEM_LIMIT`/
      `LEAN_CONTAINER_CPUS`, see SPEC.md §3) so parallel test runs or overlapping
      `algo-backtest run` invocations can't collectively exhaust host CPU/RAM — the
      same failure class as the mutation-harness desktop-freeze incident this session,
      via containers instead of orphaned subprocesses. Also cherry-picked hardener's
      `048fbcb` (the mutation-harness process-group-kill fix) into this worktree.
