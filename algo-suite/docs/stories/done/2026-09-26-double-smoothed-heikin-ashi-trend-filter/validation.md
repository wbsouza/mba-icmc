# Validation — 04k

The requested Uncle Bob agent gauntlet ran as separate Specifier, Coder,
Cleaner, Hardener and QA agent sessions. Acceptance tests are Gherkin-only.

- Host acceptance: 28 scenarios passed.
- Native acceptance: 8 scenarios passed against `quantconnect/lean:17748`.
- Mutation gate: **23/23 killed**, zero survivors/errors (`mutations.json`).
  Scope: new config and HA formula, native smoothing/consolidation wrappers, and
  source selection/readiness in the shared chain engine. This is the scoped
  operator campaign, not an assertion that every conceivable mutation was tested.
- Dependency-boundary checker: passed. Pure formula/config modules do not depend
  on LEAN or chain/engine policy; native adapters have an explicit import allowlist.
- CRAP threshold 8: passed, maximum **6**. All perception functions have 100%
  measured line coverage after combining host coverage.py with native stdlib
  tracing (`quality-report.txt`). Branch coverage is not claimed by this measure.
- Strict mypy: all six packages' source plus the new quality tools passed (137 files).
- Workspace regression suite: 751 passed, 35 deselected, before the later
  additional hardening scenarios; those were then run in the package gate.
- Dependency audit: no known vulnerabilities.

The `algo-backtest` package's `make check` passes: 389 scenarios passed, 35
integration scenarios deselected by the default gate. Root workspace `make check`
still stops on **52 pre-existing BigQuery-script Ruff errors**, recorded in TD-55;
this story does not mark that workspace gate green. The ready TD-60 cleanup was
completed: removed obsolete direct joblib dependency and mypy override, preserving
scikit-learn's transitive dependency.

## Reproduce

From `algo-suite`, `make check-perception` runs host coverage, native observations
and assertions, automatic coverage merging, the architecture/CRAP checker, and
native mutation tests in order. Docker is required; `make check` stays offline and
includes the dependency-boundary check. `make -C algo-backtest check` runs the
package regression suite; `make audit` checks dependency vulnerabilities.

Gauntlet-driven stories retain the measured quality and mutation reports alongside
their spec, progress and lessons learned so gate claims can be independently audited.
Native line coverage uses stdlib tracing because the pinned container lacks coverage.py.
Mutation tests use isolated package copies and bounded subprocesses; production is
never mutated. Standard mutmut covers the host-importable config and HA modules;
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
