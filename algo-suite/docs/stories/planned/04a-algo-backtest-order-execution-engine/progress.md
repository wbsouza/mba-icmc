# Progress — Spec 04a (order-execution engine)

- [ ] Audit `baseline_ma`/`baseline_meanrev` for existing order-placement code (T1)
- [ ] Implement `OrderExecutor` (`engine/order_executor.py`) (T2)
- [ ] Implement `engine/algorithm.py` (`QCAlgorithm` skeleton) wired to `OrderExecutor` (T3)
- [ ] `engine/brokerage/` port: `BrokerageAdapter` ABC + registry + `oanda.py` adapter, config-selected
- [ ] Migrate `baseline_ma` onto `OrderExecutor` + brokerage adapter (T4)
- [ ] Migrate `baseline_meanrev` onto `OrderExecutor` + brokerage adapter (T4)
- [ ] `tests/features/order_execution.feature` — 6 scenarios green against real pinned LEAN container (T5)
- [ ] `make check` green
