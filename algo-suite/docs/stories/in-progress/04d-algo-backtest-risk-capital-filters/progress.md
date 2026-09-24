# Progress — Spec 04d (risk & capital-management filters F5/F6)

Own worktree/branch (`feat/04d-risk-capital-filters`), disjoint files from 04c/04f — safe to
run fully in parallel with them.

**Correction vs. the original checklist below:** the `fx-manager` legacy Java repo is NOT
present in this checkout (only referenced by URL in specs.md §14.5,
`https://git.disposalqueen.com/algo-trading/fx-manager`) — there is no local source to
"port" or diff against. Implement strictly from specs.md §14.5-§14.8's formulas/constants
(given verbatim there), and prove the arithmetic by unit-level Gherkin scenarios with
hand-computed expected values from the stated formula — not a regression against legacy
code that isn't accessible from this sandbox. Document this deviation in `lessons-learned.md`.

- [ ] T1 — `rules/risk_math.py`: fixed-fractional lot sizing,
      `lot_size = (account_balance * risk) / (pip_value * stop_loss_pips)` (specs.md §14.5,
      `risk = 0.03` default) + `tests/features/risk_math.feature`
- [ ] T2 — `rules/trail_stop.py`: trail-stop trigger/destination (specs.md §14.5 target/trail
      formulas + §14.7 Strategy A05 params: arm at 50% of way to SL, destination
      entry-66%*SL-distance) + `tests/features/trail_stop.feature`
- [ ] T3 — `rules/close_portion.py`: partial-close laddering (§14.7: intermediate partial
      close 50%, final target 2.0x SL close 50%) + `tests/features/close_portion.feature`
- [ ] T4 — `rules/risk_guard.py`: portfolio caps/drawdown breakers/leverage cap, all
      config-driven per §14.8 (`portfolio_at_risk_cap`, `daily_drawdown_limit`,
      `weekly_drawdown_limit`, `max_concurrent_trades_per_account`, `max_leverage`) — no
      numeric defaults, missing config is a hard stop (fail-fast, CLAUDE.md)
- [ ] T5 — `chain/filters/f5_risk_guard.py`: Filter wired to `rules/risk_guard.py`,
      VETO/ABSTAIN scenarios (`tests/features/f5_risk_guard.feature`)
- [ ] T6 — `chain/filters/f6_capital_mgmt.py`: Filter wired to `rules/risk_math.py`,
      enriches state with computed lot size, vetoes on insufficient margin
      (`tests/features/f6_capital_mgmt.feature`)
- [ ] T7 — gate: `make check` green; mutation pass on all `rules/*.py` + both filter files
- [ ] `lessons-learned.md` written, story moved to `docs/stories/done/`
