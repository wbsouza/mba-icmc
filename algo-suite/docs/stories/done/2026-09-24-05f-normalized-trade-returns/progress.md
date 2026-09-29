# Progress — Spec 05f (normalized trade returns)

- [x] Define the normalized trade-return artifact contract
- [x] Implement producer-side normalized fractional `return` values
- [x] Preserve raw LEAN trade payloads for audit/debugging
- [x] Add BDD coverage for representative LEAN closed-trade payloads
- [x] Add BDD coverage proving figures render from `write_run_artifacts()` output
- [x] Reject or explicitly mark unsupported absolute-PnL-only payloads
- [x] `make -C algo-backtest check` green
- [x] `make -C algo-analyze check` green
