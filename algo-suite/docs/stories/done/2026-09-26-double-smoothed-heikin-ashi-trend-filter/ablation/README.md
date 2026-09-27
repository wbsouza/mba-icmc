# Perception-source ablation with frozen EMA-trained F7 model

EURUSD historical minute quotes; identical window and account parameters. This short smoke comparison is not evidence of profitability.

| strategy | total_return | sharpe | max_drawdown | hit_rate |
| --- | --- | --- | --- | --- |
| baseline | 0.0 | 0.0 | 0.0 | 0.0 |
| baseline-dsha | 0.0001 | 0.0456 | 0.0 | 1.0 |

The CSV and CLI JSON contain the actual completed-run metrics. qa-evidence.json records artifact, frozen model and input ZIP hashes, decision comparisons, and configuration provenance.

Pass 1 is LEAN Wilder(6); pass 2 is LEAN LWMA(2), matching MT4's default second period of 2 (the historical Java implementation used 1). Ties classify down. LEAN warmup and bar boundaries may differ from MT4.

Some runs may predate the engine configuration sidecar: qa-resolved-config.json is an explicitly labeled QA snapshot when that sidecar is absent. Actual model parity is checked from each engine log.

Decision artifacts expose consumed directions and feature hashes, but not per-bar readiness or underlying candle times. Native integration acceptance tests are the timing/readiness gate. Workspace, coverage, complexity and mutation gates are recorded separately.
