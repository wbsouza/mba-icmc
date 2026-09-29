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
