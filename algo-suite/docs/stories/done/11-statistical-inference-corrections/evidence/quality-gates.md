# Story 11 final quality gates — September 27, 2026

All required software gates passed. This closes the statistical implementation
story; it does not close Task 10's scientific-readiness gates or establish H1.

| Gate | Command / evidence | Result |
| --- | --- | --- |
| Analyzer acceptance and cleaner | `make -C algo-suite/algo-analyze check-inference`; `final-quality-gate.txt` | 143 Gherkin scenarios; Ruff and strict mypy pass; architecture boundaries pass |
| Coverage / CRAP | Same combined gate | 100% line coverage in deflated, significance, portfolio and reports; maximum scoped CRAP 8 |
| Mutation hardening | `gauntlet_mutations.py`; final and prior campaign JSON | 149/149 generated arithmetic, comparison and Boolean mutants killed; zero survivors/errors/exclusions; baseline and negative control verified |
| Researcher-facing QA | `uv run python docs/stories/done/11-statistical-inference-corrections/evidence/qa_cli.py` from algo-suite | 14 actual subprocess CLI checks pass; `qa-results.json` |
| Independent statistical study | `uv run --with mpmath==1.3.0 python docs/stories/done/11-statistical-inference-corrections/evidence/validate_inference.py` | Five high-precision formula fixtures and all registered simulation gates pass; 7,200 coherent p/interval decisions |
| Real engine artifacts | `smoke-saved-runs.sh` from repository root via story path | Two completed September runs, 30 actual daily returns each; flat-equity inference unavailable; originals unchanged |
| Dependency audit | `make -C algo-suite audit`; `dependency-audit.txt` | No known vulnerabilities at audit time |
| Manuscript | `make -C monografia pdf` then `make -C monografia verify`; `manuscript-verify.txt` | 90-page PDF; no undefined citations/references |
| Evidence and gate tooling | Ruff and strict mypy over the four Python scripts (with `MYPYPATH=algo-analyze/src`) | Pass |

`check-inference` executes the lint, type and test checks of `make check`, adding
coverage, architecture and CRAP enforcement. The earlier coder-stage `make check`
also passed. Backtest code and artifacts were not changed, so no backtest code gate
was needed. The test log retains two third-party Typer/Click deprecation warnings.

The gauntlet used distinct specifier, coder and cleaner agents; the independent
scientific-validation agent subsequently performed hardening, and the specifier
performed black-box QA after the session's agent-thread limit prevented further
fresh agents. Findings were repaired and mechanically rechecked. Mutation passes
reuse prior kills only when source hashes match; the final report records which
mutants were replayed and which verified kills were reused. No surviving mutants
were waived or classified as equivalent.

Core source hashes in the final mutation report and simulation configuration were
verified against the files submitted in this PR. The arithmetic-boundary hardening
also caught a confidence-interval mismatch at alpha=0.035, B=199: floating-point
multiplication rounded the percentile rank incorrectly. The implementation now
inverts the same floating-point p-value grid used by the rejection decision.

The nine-run migration inventory retains unavailable reasons. Metadata for the two
pilot smoke runs was reconstructed on temporary copies only; selection history was
not invented. Legacy results, raw runs and frozen models were preserved.
