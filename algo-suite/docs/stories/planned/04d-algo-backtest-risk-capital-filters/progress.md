# Progress — Spec 04d (risk & capital-management filters F5/F6)

- [ ] Port `rules/risk_math.py` (fixed-fractional lot sizing) from `fx-manager`
- [ ] Port `rules/trail_stop.py` from `fx-manager`
- [ ] Port `rules/close_portion.py` from `fx-manager`
- [ ] Port `rules/risk_guard.py` from `fx-manager`
- [ ] Regression test: Python port reproduces legacy decisions on identical synthetic input
- [ ] F5 risk-guard filter (`chain/filters/f5_risk_guard.py`) + VETO/ABSTAIN scenarios
- [ ] F6 capital-management filter (`chain/filters/f6_capital_mgmt.py`) + VETO/ABSTAIN scenarios
- [ ] `make check` green
