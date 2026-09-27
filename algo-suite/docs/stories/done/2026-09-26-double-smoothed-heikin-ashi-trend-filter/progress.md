# Progress — Spec 04k

Completed 2026-09-26, including PR #43 offline training/parity in PR #45.

- [x] Native Wilder → HA → LWMA `PythonIndicator`, with readiness, events and reset
- [x] Primary and completed higher-timeframe TradeBar consolidation
- [x] Two F1 direction keys populated; existing EMA-gap strength retained
- [x] Validated source selector and inherited `baseline-dsha` config
- [x] Real paired EURUSD runs and existing analyzer ablation table persisted
- [x] Tie-as-down, period2=2, explicit HA seed, and `perception/` module documented
- [x] Package `make check`: 418 passed; strict mypy and Ruff green
- [x] Gauntlet: 9 indicator + 8 parity native scenarios, 49/49 mutations killed, maximum CRAP 6
- [x] Atomic config artifact, measured native observations, automated perception gate
- [x] Paired ablation provenance requires engine-written sidecars from one code revision
- [x] Retrospective and move to done

Root workspace `make check` remains blocked by the existing 52 BigQuery-script
lint errors (TD-55); it is **not** reported green. Workspace regression tests and
all six packages' source type checks pass (see `validation.md`). Dependency audit:
no known vulnerabilities. Ready debt TD-60 is removed from the active ledger.
PR #43 ancestry, tie decision and offline training/parity are integrated. TD-61
retains the deferred ABSTAIN experiment; resolved TD-62 is removed.

The ablation deliberately freezes the baseline's EMA-trained F7 model. Offline
training additionally supports config-selected DSHA with real native parity. Both runs use 2015-08-03 through 2015-08-07 EURUSD;
small genuine artifacts and provenance live in `ablation/`.

- [x] Config-selected offline DSHA pipeline and training entry points
- [x] Real native parity across readiness, gaps, flat ties, and custom parameters
- [x] Refresh gauntlet evidence, documentation and lessons; remove resolved TD-62
