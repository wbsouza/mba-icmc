# Progress — Spec 04k

Completed 2026-09-26; implementation and evidence are ready for commit.

- [x] Native Wilder → HA → LWMA `PythonIndicator`, with readiness, events and reset
- [x] Primary and completed higher-timeframe TradeBar consolidation
- [x] Two F1 direction keys populated; existing EMA-gap strength retained
- [x] Validated source selector and inherited `baseline-dsha` config
- [x] Real paired EURUSD runs and existing analyzer ablation table persisted
- [x] Tie-as-down, period2=2, explicit HA seed, and `perception/` module documented
- [x] Package `make check`: 389 passed; strict mypy and Ruff green
- [x] Gauntlet: 8 native scenarios, 23/23 mutations killed, maximum CRAP 6
- [x] Retrospective and move to done

Root workspace `make check` remains blocked by the existing 52 BigQuery-script
lint errors (TD-55); it is **not** reported green. Workspace regression tests and
all six packages' source type checks pass (see `validation.md`). Dependency audit:
no known vulnerabilities. Ready debt TD-60 is resolved.

The ablation deliberately freezes the baseline's EMA-trained F7 model. Offline
training remains EMA-only. Both runs use 2015-08-03 through 2015-08-07 EURUSD;
small genuine artifacts and provenance live in `ablation/`.
