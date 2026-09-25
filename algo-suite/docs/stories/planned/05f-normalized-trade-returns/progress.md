# Progress — Spec 05f (normalized trade returns)

- [ ] Define the normalized trade-return artifact contract
- [ ] Implement producer-side normalized fractional `return` values
- [ ] Preserve raw LEAN trade payloads for audit/debugging
- [ ] Add BDD coverage for representative LEAN closed-trade payloads
- [ ] Add BDD coverage proving figures render from `write_run_artifacts()` output
- [ ] Reject or explicitly mark unsupported absolute-PnL-only payloads
- [ ] `make -C algo-backtest check` green
- [ ] `make -C algo-analyze check` green
