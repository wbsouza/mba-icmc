Feature: Persist raw artifacts from a backtest run
  E1/E2 make a run self-describing: alongside LEAN's result JSON it writes a run manifest
  (strategy, symbol, window, params), the closed-trade ledger, and the four headline
  metrics, so a result can be re-analyzed later without re-running the engine.

  Rule: A finished run records its manifest, closed-trade ledger and metrics

    Scenario: writing artifacts produces a manifest, a trade ledger and the metrics
      Given a finished baseline run reporting 2 closed trades
      When I write its run artifacts
      Then run.json records strategy "baseline-ma", symbol "EURUSD" and the window
      And trades.json lists 2 closed trades
      And metrics.json records the four headline metrics

  Rule: The trade ledger normalizes a fractional return per Spec 05f

    Scenario: a closed trade with entry pricing and quantity gains a normalized return
      Given a finished run with a closed trade priced at entry 1.1000, quantity 10000 and profit 55.0
      When I write its run artifacts
      Then trades.json trade 0 has a normalized return of 0.005
      And trades.json trade 0 still reports its raw profitLoss of 55.0

    Scenario: a closed trade without enough pricing data is left unsupported
      Given a finished run with a closed trade reporting only profitLoss 40.0
      When I write its run artifacts
      Then trades.json trade 0 has no normalized return field
      And trades.json trade 0 still reports its raw profitLoss of 40.0

    Scenario: a bogus raw return field is stripped when normalization cannot be computed
      Given a finished run with a closed trade reporting only profitLoss 40.0 and a bogus raw return of 999.0
      When I write its run artifacts
      Then trades.json trade 0 has no normalized return field
      And trades.json trade 0 still reports its raw profitLoss of 40.0

    Scenario: a closed trade with zero cost basis is left unsupported
      Given a finished run with a closed trade priced at entry 1.1000, quantity 0 and profit 0.0
      When I write its run artifacts
      Then trades.json trade 0 has no normalized return field

    Scenario: a closed trade whose computed return is not finite is left unsupported
      Given a finished run with a closed trade priced at entry 1.1000, quantity 10000 and an infinite profit
      When I write its run artifacts
      Then trades.json trade 0 has no normalized return field
      And trades.json trade 0 still reports a non-finite raw profitLoss

    Scenario: a pre-existing raw return field is never trusted over the computed one
      Given a finished run with a closed trade priced at entry 1.1000, quantity 10000, profit 55.0 and a bogus raw return of 999.0
      When I write its run artifacts
      Then trades.json trade 0 has a normalized return of 0.005
