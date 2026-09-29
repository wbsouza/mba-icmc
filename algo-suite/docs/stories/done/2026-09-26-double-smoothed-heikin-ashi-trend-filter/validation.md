# Validation — 04k

The requested Uncle Bob agent gauntlet ran as separate Specifier, Coder,
Cleaner, Hardener and QA agent sessions. Acceptance tests are Gherkin-only.

- Focused host perception acceptance: 42 scenarios passed (including 13 offline DSHA scenarios).
- Native acceptance: 9 indicator scenarios plus 8 training/parity scenarios passed
  against `quantconnect/lean:17748` (5 DSHA parity cases, 3 existing EMA/news cases).
- Mutation gate: **49/49 killed**, zero survivors/errors (`mutations.json`).
  Scope: config, HA formula, offline smoothing/consolidation, native adapters, and
  source selection/readiness in the shared chain engine. This is the scoped
  operator campaign, not an assertion that every conceivable mutation was tested.
- Dependency-boundary checker: passed. Pure formula/config modules do not depend
  on LEAN or chain/engine policy; native adapters have an explicit import allowlist.
- CRAP threshold 8: passed, maximum **6**. All perception functions have 100%
  measured line coverage after combining host coverage.py with native stdlib
  tracing (`quality-report.txt`). Branch coverage is not claimed by this measure.
- Strict mypy: all six packages' source plus the new quality tools passed (138 files).
- Original implementation workspace regression: 751 passed, 35 deselected.
  Review follow-up validation reran the affected package (418 passed) and all
  workspace tooling scenarios (22 passed).
- Dependency audit: no known vulnerabilities.

The `algo-backtest` package's `make check` passes: 418 scenarios passed, 41
integration scenarios deselected by the default gate. Root workspace `make check`
still stops on **52 pre-existing BigQuery-script Ruff errors**, recorded in TD-55;
this story does not mark that workspace gate green. The ready TD-60 cleanup was
completed: removed obsolete direct joblib dependency and mypy override, preserving
scikit-learn's transitive dependency. Its row was deleted from the active debt
ledger. PR #43's branch was merged into this branch, preserving its ancestry and
tie decision in the done story. TD-61 tracks ABSTAIN-on-tie research. PR #43's
offline training/parity requirement is implemented in the same story; resolved
TD-62 is removed from the ledger.

Both ablation arms were rerun from clean code revision
`9eced901ec93d04bf3f7f41b03b47f20edaa7d38`. `ablation/qa-evidence.json` records
engine-written sidecar hashes for both runs and matching frozen model hashes.
The comparison has 6,940 baseline decisions and 6,639 candidate decisions; the
candidate first evaluates at 2015-08-03 06:00 UTC. These are smoke observations,
not evidence for profitability or DSHA-retrained-model performance. The later
training/parity addition does not replace that model or change the runtime
perception path; this earlier code revision remains the experiment's provenance.

## Reproduce

From `algo-suite`, `make check-perception` runs host coverage, native observations
and assertions, all training/parity scenarios, automatic coverage merging, the architecture/CRAP checker, and
native mutation tests in order. Docker is required; `make check` stays offline and
includes the dependency-boundary check. `make -C algo-backtest check` runs the
package regression suite; `make audit` checks dependency vulnerabilities.

Gauntlet-driven stories retain the measured quality and mutation reports alongside
their spec, progress and lessons learned so gate claims can be independently audited.
Native line coverage uses stdlib tracing because the pinned container lacks coverage.py.
Mutation tests use isolated package copies and bounded subprocesses; production is
never mutated. Standard mutmut covers the host-importable config, HA and offline replay modules;
`make check-perception` additionally covers real native adapters and engine wiring.

## QuantConnect references checked

- [Custom indicators](https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/custom-indicators):
  PythonIndicator subclass, manual current value/event publication and readiness.
- [Wilder moving average](https://github.com/QuantConnect/Lean/blob/master/Indicators/WilderMovingAverage.cs)
  and [linear-weighted moving average](https://github.com/QuantConnect/Lean/blob/master/Indicators/LinearWeightedMovingAverage.cs):
  native smoothing and readiness, not local reimplementations.
- [Heikin-Ashi](https://github.com/QuantConnect/Lean/blob/master/Indicators/HeikinAshi.cs):
  transform and first-candle seeding reference.
- [TradeBar consolidation](https://github.com/QuantConnect/Lean/blob/master/Common/Data/Consolidators/TradeBarConsolidator.cs)
  and [period/count base](https://github.com/QuantConnect/Lean/blob/master/Common/Data/Consolidators/PeriodCountConsolidatorBase.cs):
  forward-only aggregation and end-time scan semantics.

The running behavior was verified against the pinned image, not inferred solely
from the moving upstream documentation or source branch.
