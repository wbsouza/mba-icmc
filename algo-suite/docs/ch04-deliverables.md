# Chapter 4 deliverables and evidence gates

Updated September 26, 2026. Tool completion, pilot execution, and reportable
scientific evidence are separate states. Follow the twelve stages in
[the workflow](experimental-workflow.md) and the [global plan](stories/00-PLAN.md).

| Section | Required evidence | Current state |
|---|---|---|
| Experimental setup | Exact features, splits, training/calibration, model hashes, replay assumptions, artifact provenance | Updated to the six-month EUR/USD pilot; both models trained; final archive/environment review remains |
| Data coverage | Completed source months, missing-day/quarantine review, source overlap and supported window | Local completion markers through September; full coverage rule not established |
| Baseline | Audited held-out run, trade/decision evidence, descriptive metrics and properly labeled figures | September replay completed with zero trades; diagnose before interpretation |
| Hybrid | Matched held-out replay and real event-feature availability | September replay completed with zero trades; saved equity supports an integration check, not inference |
| Ablations | Registered variants and paired evidence separating news-family and F4-gate effects | Not established by baseline/hybrid alone; DSHA frozen-model smoke evidence is a different comparison |
| Prior-art comparison | Compatible return frequency, costs, window, protocol, and limitations | No validated paired result yet; avoid inferring expected performance from another asset class |
| Threats to validity | Coverage, leakage, feature omissions, cost/risk assumptions, dependence, and selection | Pilot limitations drafted; expand with audited outcomes |

## Required transitions

1. **Task 08:** complete and reconcile source/feature readiness for each run.
2. **Task 09:** fit and calibrate, freeze models, execute paired simulations,
   and inspect actual dates, zero-trade outcomes, and decision/trade joins.
3. **Task 10:** review coverage, known-answer controls, cost/risk economics,
   dependence, feature scope, and the final validation protocol.
4. **Story 11:** schema-v2 DSR probability and paired stationary-bootstrap
   mean-return inference require independent formula/simulation validation.
   Each empirical use additionally requires audited daily equity, cost metadata,
   selection history, and predeclared block settings; unavailable diagnostics
   do not establish a null result.
5. **Task 06:** publish only evidence supported by these stages, with run IDs,
   commands, figures, uncertainty where justified, and explicit omissions.
6. **Task 07:** complete manuscript QA, advisor review, and final build.

CPCV, rolling refits, and embargo remain target validation stages. Missing
sentiment and F3 pattern detection, fixed risk/economic proxies, and GDELT's
late-reporting leakage remain limitations; extending the window alone does
not remove them. The pilot can proceed while these issues are tracked, but
its completion must not be equated with establishing H1.
