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

From `algo-suite`:

```sh
make -C algo-backtest check
uv run pytest algo-backtest/tests/steps/test_double_smoothed_heikin_ashi.py \
  algo-backtest/tests/steps/test_perception_hardening.py -m integration \
  --basetemp=/tmp/04k-native-final
uv run pytest algo-backtest/tests/steps/test_double_smoothed_heikin_ashi.py \
  algo-backtest/tests/steps/test_perception_hardening.py \
  --cov=algo_backtest.perception --cov-report=json:build/perception-host-coverage.json
uv run python tools/perception_mutations.py --native
make audit
```

The native probe emits `perception-native-lines.json` below the fixed pytest
base directory. The LEAN image lacks coverage.py, so it uses Python's stdlib trace.
To reproduce `build/perception-coverage.json`, match native/host file names by their
`algo_backtest/perception/<filename>` suffix. For each host file, retain the executable
line universe (`executed_lines ∪ missing_lines`), union native traced lines with host
executed lines, and intersect with that universe; remaining executable lines are
missing. Then run:

```sh
uv run python tools/perception_quality.py --coverage build/perception-coverage.json
```

Mutation tests copy the package to a private temporary tree and verify its imported
location; the native runner mounts that mutated copy. They never modify the shared
production files. Resource/time limits apply to subprocesses and LEAN containers.

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
