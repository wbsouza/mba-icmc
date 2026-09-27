# Story 11 final quality gates — September 27, 2026

All required software gates passed. This closes the statistical implementation
story; it does not close Task 10's scientific-readiness gates or establish H1.

| Gate | Command / evidence | Result |
| --- | --- | --- |
| Analyzer acceptance and cleaner | `make -C algo-suite/algo-analyze check-inference` | 159 Gherkin scenarios (review follow-up, September 27); Ruff and strict mypy pass; architecture boundaries pass; `check-inference-architecture` is part of workspace `make check` |
| Coverage / CRAP | Same combined gate | 100% line coverage in deflated, significance, portfolio and reports; CLI file coverage above 95%; maximum scoped CRAP 8 |
| Mutation hardening | `gauntlet_mutations.py`; `gauntlet-mutations-final.json` (prior final: `-pass4.json`) | 161/161 generated arithmetic, comparison and Boolean mutants killed (114 fresh after the follow-up, 47 hash-matched reuses); zero survivors/errors/exclusions; baseline and negative control verified |
| Backtest producer | `make -C algo-suite/algo-backtest check` | 418 scenarios pass with `inference-inputs.json` emitted per run and `broker_adapter` required |
| Researcher-facing QA | `uv run python docs/stories/done/11-statistical-inference-corrections/evidence/qa_cli.py` from algo-suite | 14 actual subprocess CLI checks pass; `qa-results.json` |
| Independent statistical study | `uv run --with mpmath==1.3.0 python docs/stories/done/11-statistical-inference-corrections/evidence/validate_inference.py` | Six formula fixtures pass; the original n=1200 gates pass and reproduce exactly; **both registered thesis-window extensions fail the null gate** (recorded, not waived; see `README.md`); 21,600 coherent p/interval decisions; script exits nonzero by design |
| Real engine artifacts | `smoke-saved-runs.sh` from repository root via story path | Two completed September runs, 30 actual daily returns each; flat-equity inference unavailable at L=3 and L=1; originals unchanged |
| Dependency audit | `make -C algo-suite audit`; `dependency-audit.txt` | No known vulnerabilities at audit time |
| Manuscript | `make -C monografia pdf` then `make -C monografia verify`; `manuscript-verify.txt` | 90-page PDF; no undefined citations/references |
| Evidence and gate tooling | Ruff and strict mypy over the four Python scripts (with `MYPYPATH=algo-analyze/src`) | Pass |

`check-inference` executes the lint, type and test checks of `make check`, adding
coverage, architecture and CRAP enforcement. The review follow-up changed the
backtest producer (`artifacts.py`), so its tool gate was rerun. Workspace-wide
`make check` is red on `main` for reasons unrelated to this story (TD-64). The
test log retains two third-party Typer/Click deprecation warnings.

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
